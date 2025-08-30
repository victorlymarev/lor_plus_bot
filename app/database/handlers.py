from database.db_create import async_session
from sqlalchemy import select, text
from database.models import Appointments, Users, Logs
from datetime import datetime, timedelta
from utils.utils import get_other_doctor_id
import asyncio

lock = asyncio.Lock()


class AsyncORM:

    @staticmethod
    async def get_records_for_main_menu(user_id: int
                                        ) -> tuple[list[Appointments],
                                                   list[Appointments], bool]:

        '''Метод для главного меню

        input:
            user_id: int - id пользователя

        output:
            tuple[list[Appointments], list[Appointments], bool]
            первый список - текущие записи к врачу, отсортированные по дате
            второй список - текущие записи на лечение, отсортированные по дате
            булевое значение, содержащее информацию о том, что человек в
                ближайшие две недели был на приеме или на лечении.
        '''

        now = datetime.now()
        async with async_session() as session:
            query = (
                    select(Appointments)
                    .filter_by(user_id=user_id)
                    .filter(Appointments.time >= now - timedelta(days=14))
                    .order_by(Appointments.time)
                )
            result = await session.execute(query)
        result = result.scalars().all()

        treatments = []
        appointments = []
        visited_before = False

        for app in result:
            if app.time < now:
                visited_before = True
                continue

            if app.doctor_id == 5:
                treatments.append(app)
            else:
                appointments.append(app)

        return appointments, treatments, visited_before

    @staticmethod
    async def get_visits(user_id: int | list[int] = None,
                         date_from: datetime = None,
                         date_to: datetime = None,
                         doctor_id: list[int] = None,
                         available: bool = None,
                         ) -> list[Appointments]:

        '''Метод возвращает записи пользователя, отсортированные по дате

        input:
            user_id: int | list[int] - id пользователя
            date_from: datetime - дата от которой находить действия
            date_to: datetime - дата до которой находить действия
            doctor_id: list[int]
            available: bool - индикатор того, что запись доступна

        output:
            list[Appointments]
            список виситов за определенное время
        '''

        if isinstance(user_id, int):
            user_id = [user_id]

        async with async_session() as session:
            query = select(Appointments)
            if user_id is not None:
                query = query.filter(Appointments.user_id.in_(user_id))
            if date_from:
                query = query.filter(Appointments.time >= date_from)
            if date_to:
                query = query.filter(Appointments.time <= date_to)
            if doctor_id:
                query = query.filter(Appointments.doctor_id.in_(doctor_id))
            if available is not None:
                query = (query
                         .filter_by(available_from_user=available)
                         .filter_by(available_from_admin=available))
            query = query.order_by(Appointments.time)
            result = await session.execute(query)

            return result.scalars().all()

    @staticmethod
    async def get_visits_movement(time,
                                  doctor_id,
                                  available_from_admin: bool = True
                                  ) -> list[datetime]:

        '''Метод возвращает до двух записей на которые можно перенести
        дату. На вход подается время записи с которой мы хотим перенести
        запись. И возвращает время на 20 минут вперед или назад
        в зависимости от того, можно ли будет на них записать
        input:
            time - время записи с которой переносится запись
            doctor_id_from - id врача на которого мы переносим запись
            available_from_admin - разрешено ли время для записи
        output:
            list[datetime]
        '''

        async with async_session() as session:
            other_doctor = get_other_doctor_id(doctor_id=doctor_id)

            if doctor_id == 0:
                doctor_id = [1, 2]
            else:
                doctor_id = [doctor_id]

            q_minus_40 = (select(Appointments)
                          .filter(Appointments.doctor_id.in_(
                              other_doctor + doctor_id))
                          .filter_by(time=time - timedelta(minutes=40)))

            q_minus_20 = (select(Appointments)
                          .filter(Appointments.doctor_id.in_(
                              other_doctor + doctor_id))
                          .filter_by(time=time - timedelta(minutes=20)))

            q_plus_20 = (select(Appointments)
                         .filter(Appointments.doctor_id.in_(
                              other_doctor + doctor_id))
                         .filter_by(time=time + timedelta(minutes=20)))

            q_plus_40 = (select(Appointments)
                         .filter(Appointments.doctor_id.in_(
                              other_doctor + doctor_id))
                         .filter_by(time=time + timedelta(minutes=40)))

            res = await asyncio.gather(
                    session.execute(q_minus_40),
                    session.execute(q_minus_20),
                    session.execute(q_plus_20),
                    session.execute(q_plus_40))

            res = [r.scalars().all() for r in res]

            r_minus_40, r_minus_20, r_plus_20, r_plus_40 = res

            dates = []

            if (all([r.user_id is None for r in r_minus_40 + r_minus_20])
               or (len(r_minus_40) == 0)):
                r_minus_20 = [r.time for r in r_minus_20
                              if ((r.doctor_id in doctor_id)
                                  and (r.available_from_admin
                                       == available_from_admin))]

                if len(r_minus_20) > 0:
                    dates.append(time - timedelta(minutes=20))
                elif not available_from_admin:
                    dates.append(time - timedelta(minutes=20))

            if (all([r.user_id is None for r in r_plus_40 + r_plus_20])
               or (len(r_plus_40) == 0)):
                r_plus_20 = [r.time for r in r_plus_20
                             if ((r.doctor_id in doctor_id)
                                 and (r.available_from_admin
                                      == available_from_admin))]

                if len(r_plus_20) > 0:
                    dates.append(time + timedelta(minutes=20))
                elif not available_from_admin:
                    dates.append(time + timedelta(minutes=20))

            return dates

    @staticmethod
    async def make_time_available(doctor_id: int,
                                  time: datetime,
                                  force_codes: list[int] = None
                                  ) -> tuple[int, str, int]:
        '''
        Метод позволяет добавлять в бд новые записи, доступные для приема.
        Метод меняет поле available_from_admin на True

        input:
            doctor_id: int - id врача, для которого добавляется время
            time: datetime - дата и время, которое нужно сделать доступным для
                приема
            force_codes: list[int] - коды ошибок, которые можно преодолеть

        output:
            tuple[int, str, int]
            первое число - user_id из таблицы
            второе число - user_name из таблицы
            тетье число - статус код
        '''
        if force_codes is None:
            force_codes = []

        if (40 not in force_codes) and (time < datetime.now()):
            return (None, None, 40)

        if (((time.weekday() == 6) or
             (time.weekday() == 5 and time.hour >= 14))
           and (80 not in force_codes)):
            return None, None, 80

        async with async_session() as session, lock:
            # эти запросы нужны для того, чтобы понять что ставить в поле
            # awailable_from_user
            od = get_other_doctor_id(doctor_id=doctor_id)
            other_doctor_q = (
                select(Appointments)
                .filter(Appointments.doctor_id.in_(od))
                .filter_by(time=time))

            other_time_q = (
                select(Appointments)
                .filter(Appointments.doctor_id.in_(od + [doctor_id]))
                .filter(Appointments.time.in_(
                    [time + timedelta(minutes=20), time - timedelta(minutes=20)
                     ])))

            query = (select(Appointments)
                     .filter_by(doctor_id=doctor_id)
                     .filter_by(time=time))

            result, other_time_result, other_doctor_result = (
                await asyncio.gather(
                    session.execute(query),
                    session.execute(other_time_q),
                    session.execute(other_doctor_q)))

            result = result.scalars().one_or_none()
            other_time_result = other_time_result.scalars().all()
            other_doctor_result = other_doctor_result.scalars().one_or_none()

            if doctor_id in [1, 2] and other_doctor_result is not None:
                if (other_doctor_result.available_from_admin
                    and (other_doctor_result.user_id is None)
                        and (50 in force_codes)):
                    other_doctor_result.available_from_admin = False
                elif (other_doctor_result.available_from_admin
                      and (other_doctor_result.user_id is None)
                      and (50 not in force_codes)):
                    return None, None, 50
                elif other_doctor_result.user_id:
                    return (other_doctor_result.user_id,
                            other_doctor_result.user_name,
                            61)

            if result is not None:
                if result.available_from_admin:
                    return result.user_id, result.user_name, 23
                result.available_from_admin = True
                return result.user_id, result.user_name, 15

            av = ((not any([r.user_id for r in other_time_result])) and
                  ((other_doctor_result is None) or
                   (other_doctor_result.user_id is None)))

            new_available_appointment = Appointments(
                doctor_id=doctor_id,
                time=time,
                available_from_user=av,
                available_from_admin=True)

            session.add(new_available_appointment)
            await session.commit()
            return None, None, 11

    @staticmethod
    async def make_time_unavailable(doctor_id: int,
                                    time: datetime,
                                    force_codes: list[int] = None
                                    ) -> tuple[int, str, int]:
        '''
        Метод позволяет делать доступное для приема время недоступным.
        Метод не влияет на смежные записи.
        Фактически он изменяет поле available_from_admin и не трогает поле
        available_from_user

        input:
            doctor_id: int - id врача
            time: datetime - дата и время, которое нужно сделать недоступным
                для приема
            force_codes: list[int] - коды ошибок, которые можно преодолеть
        output:
            tuple[int, str, int]
            первое число - user_id из таблицы
            второе число - user_name из таблицы
            тетье число - статус код
        '''

        if force_codes is None:
            force_codes = []

        if (40 not in force_codes) and (time < datetime.now()):
            return (None, None, 40)

        async with async_session() as session, lock:
            query = (select(Appointments)
                     .filter_by(doctor_id=doctor_id)
                     .filter_by(time=time)
                     )
            result = await session.execute(query)
            result = result.scalars().one_or_none()
            if result:
                result.available_from_admin = False
                user_id, user_name = result.user_id, result.user_name
                await session.commit()
                return user_id, user_name, 12
            return None, None, 20

    @staticmethod
    async def add_new_visit(user_id: int,
                            doctor_id: int,
                            time: datetime,
                            user_name: str | None = None,
                            force_codes: list[int] = None
                            ) -> tuple[int, str, int]:
        '''Метод позволяет записаться на определенное время
        input:
            user_id: int - id пользователя, кто записывается
            doctor_id: int - id врача, к которому записываются
            time: datetime - дата и время записи
            user_name: str | None - имя пользователя, если есть или номер
                телефона
            force_codes: list[int] - коды ошибок, которые можно преодолеть
        output:
            первое число - user_id из таблицы
            второе число - user_name из таблицы
            тетье число - статус код
        '''
        if force_codes is None:
            force_codes = []

        if (40 not in force_codes) and (time < datetime.now()):
            return (None, None, 40)

        if (((time.weekday() == 6) or
             (time.weekday() == 5 and time.hour >= 14))
           and (80 not in force_codes)):
            return None, None, 80

        async with async_session() as session, lock:
            od = get_other_doctor_id(doctor_id=doctor_id)
            other_doctor_q = (
                select(Appointments)
                .filter(Appointments.doctor_id.in_(od))
                .filter_by(time=time))

            other_time_q = (
                select(Appointments)
                .filter(Appointments.doctor_id.in_(od + [doctor_id]))
                .filter(Appointments.time.in_(
                    [time + timedelta(minutes=20), time - timedelta(minutes=20)
                     ])))

            query = (select(Appointments)
                     .filter_by(doctor_id=doctor_id)
                     .filter_by(time=time))

            result, other_time_result, other_doctor_result = (
                await asyncio.gather(
                    session.execute(query),
                    session.execute(other_time_q),
                    session.execute(other_doctor_q)))

            result = result.scalars().one_or_none()
            other_time_result = other_time_result.scalars().all()
            other_doctor_result = other_doctor_result.scalars().one_or_none()

            # на этих строчках смотрим, что время не занято другим человеком
            if (result is not None) and result.user_id:
                return result.user_id, result.user_name, 60

            if ((other_doctor_result is not None
                 ) and (other_doctor_result.user_id)):
                return (other_doctor_result.user_id,
                        other_doctor_result.user_name, 60)

            for r in other_time_result:
                if r.user_id:
                    return r.user_id, r.user_name, 60

            if ((other_doctor_result is not None)
               and (other_doctor_result.doctor_id in [1, 2])
               and other_doctor_result.available_from_admin
               and (51 not in force_codes)):
                return None, None, 51

            # такого быть вообще не должно
            if ((result is not None)
                and (not result.available_from_user)
               and (47 not in force_codes)):
                return None, None, 47

            if ((result is not None)
               and (not result.available_from_admin)
               and (44 not in force_codes)):
                return None, None, 44

            if result is not None:
                result.user_name = user_name
                result.user_id = user_id
                result.available_from_user = False
                status_code = 13 if result.available_from_admin else 30
            elif (43 not in force_codes):
                return None, None, 43
            else:
                new_available_appointment = Appointments(
                    user_id=user_id,
                    user_name=user_name,
                    doctor_id=doctor_id,
                    time=time,
                    available_from_user=False,
                    available_from_admin=False)
                session.add(new_available_appointment)
                status_code = 30

            for r in other_time_result:
                r.available_from_user = False
            if other_doctor_result is not None:
                other_doctor_result.available_from_user = False

            await session.commit()
            return None, None, status_code

    @staticmethod
    async def del_appointment(user_id: int,
                              doctor_id: int,
                              time: datetime,
                              force_codes: list[int] = None
                              ) -> tuple[int, str, int]:
        '''
        Метод позволяет безопасно освободить запись на приём
        input:
            user_id: int - id пользователя
            doctor_id: int - id врача
            time: datetime - время записи
            force_codes: list[int] - коды ошибок, которые можно преодолеть

        output: tuple[int, str, int]
            первое число - user_id из таблицы
            второе число - user_name из таблицы
            тетье число - статус код
        '''

        if force_codes is None:
            force_codes = []

        if (40 not in force_codes) and (time < datetime.now()):
            return (None, None, 40)

        async with async_session() as session, lock:

            other_doctor = get_other_doctor_id(doctor_id)

            q_minus_40 = (select(Appointments)
                          .filter(Appointments.doctor_id.in_(
                              other_doctor + [doctor_id]))
                          .filter_by(time=time - timedelta(minutes=40)))

            q_minus_20 = (select(Appointments)
                          .filter(Appointments.doctor_id.in_(
                              other_doctor + [doctor_id]))
                          .filter_by(time=time - timedelta(minutes=20)))

            query_other_d = (select(Appointments)
                             .filter(Appointments.doctor_id.in_(other_doctor))
                             .filter_by(time=time))

            query = (select(Appointments)
                     .filter_by(doctor_id=doctor_id)
                     .filter_by(time=time))

            q_plus_20 = (select(Appointments)
                         .filter(Appointments.doctor_id.in_(
                              other_doctor + [doctor_id]))
                         .filter_by(time=time + timedelta(minutes=20)))

            q_plus_40 = (select(Appointments)
                         .filter(Appointments.doctor_id.in_(
                              other_doctor + [doctor_id]))
                         .filter_by(time=time + timedelta(minutes=40)))

            res = await asyncio.gather(
                    session.execute(q_minus_40),
                    session.execute(q_minus_20),
                    session.execute(query_other_d),
                    session.execute(query),
                    session.execute(q_plus_20),
                    session.execute(q_plus_40))

            r_minus_40, r_minus_20, r_od, result, r_plus_20, r_plus_40 = res

            result = result.scalars().one_or_none()

            if result is None:
                return None, None, 24

            if (user_id != result.user_id) and (48 not in force_codes):
                return result.user_id, result.user_name, 48

            old_user_id = result.user_id
            old_user_name = result.user_name

            result.user_id = None
            result.user_name = None
            result.available_from_user = True

            r_od = r_od.scalars().one_or_none()
            r_minus_40 = r_minus_40.scalars().all()
            r_minus_20 = r_minus_20.scalars().all()
            r_plus_20 = r_plus_20.scalars().all()
            r_plus_40 = r_plus_40.scalars().all()

            if r_od is not None:
                cond = ((r_od.user_id is None) and
                        (not any([r.user_id for r in r_minus_20 + r_plus_20])))
                if cond:
                    r_od.available_from_user = True

            if not any([r.user_id for r in r_minus_40 + r_minus_20]):
                if (r_od is None) or (r_od.user_id is None):
                    for r in r_minus_20:
                        r.available_from_user = True
            if not any([r.user_id for r in r_plus_40 + r_plus_20]):
                if (r_od is None) or (r_od.user_id is None):
                    for r in r_plus_20:
                        r.available_from_user = True
            await session.flush()
            await session.commit()
            return old_user_id, old_user_name, 18

    @staticmethod
    async def move_visit_time(user_id: int,
                              doctor_id_from: int,
                              doctor_id_to: int,
                              time_from: datetime,
                              time_to: datetime,
                              force_codes: list[int] = None
                              ) -> tuple[int, str, int]:
        '''Метод позволяет изменить время записи

        input:
            user_id: id пользователя
            doctor_id_from: int - id врача в исходной записи
            doctor_id_to: int - id врача в новой записи
            time_from: datetime - дата и время в исходной записи
            time_to: datetime - дата и время в новой записи
            force_codes: list[int] - коды ошибок, которые можно преодолеть

        output:
            первое число - user_id
            второе число - user_name
            тетье число - статус код
        '''

        if force_codes is None:
            force_codes = []

        if (41 not in force_codes) and (time_from < datetime.now()):
            return (None, None, 41)

        if (42 not in force_codes) and (time_to < datetime.now()):
            return (None, None, 42)

        if (((time_to.weekday() == 6) or
            (time_to.weekday() == 5 and time_to.hour >= 14))
           and (80 not in force_codes)):
            return None, None, 80

        async with async_session() as session, lock:

            other_doctor_f = get_other_doctor_id(doctor_id=doctor_id_from)
            other_doctor_to = get_other_doctor_id(doctor_id=doctor_id_to)

            # старая запись
            q_minus_40_f = (select(Appointments)
                            .filter(Appointments.doctor_id.in_(
                                other_doctor_f + [doctor_id_from]))
                            .filter_by(time=time_from - timedelta(minutes=40)))

            q_minus_20_f = (select(Appointments)
                            .filter(Appointments.doctor_id.in_(
                                other_doctor_f + [doctor_id_from]))
                            .filter_by(time=time_from - timedelta(minutes=20)))

            query_other_d_f = (select(Appointments)
                               .filter(Appointments.doctor_id.in_(
                                   other_doctor_f))
                               .filter_by(time=time_from))

            query_f = (select(Appointments)
                       .filter_by(doctor_id=doctor_id_from)
                       .filter_by(time=time_from))

            q_plus_20_f = (select(Appointments)
                           .filter(Appointments.doctor_id.in_(
                                other_doctor_f + [doctor_id_from]))
                           .filter_by(time=time_from + timedelta(minutes=20)))

            q_plus_40_f = (select(Appointments)
                           .filter(Appointments.doctor_id.in_(
                                other_doctor_f + [doctor_id_from]))
                           .filter_by(time=time_from + timedelta(minutes=40)))

            # новая запись
            other_doctor_q_to = (
                select(Appointments)
                .filter(Appointments.doctor_id.in_(other_doctor_to))
                .filter_by(time=time_to))

            other_time_q_to = (
                select(Appointments)
                .filter(Appointments.doctor_id.in_(
                    other_doctor_to + [doctor_id_to]))
                .filter(Appointments.time.in_(
                    [time_to + timedelta(minutes=20),
                     time_to - timedelta(minutes=20)
                     ])))

            query_to = (select(Appointments)
                        .filter_by(doctor_id=doctor_id_to)
                        .filter_by(time=time_to))

            res = await asyncio.gather(
                session.execute(q_minus_40_f),
                session.execute(q_minus_20_f),
                session.execute(query_other_d_f),
                session.execute(query_f),
                session.execute(q_plus_20_f),
                session.execute(q_plus_40_f),
                session.execute(other_doctor_q_to),
                session.execute(other_time_q_to),
                session.execute(query_to))

            r_minus_40_f, r_minus_20_f, r_od_f, result_f = res[:4]
            r_plus_20_f, r_plus_40_f, od_r_to, ot_r_to, result_to = res[4:]

            result_f = result_f.scalars().one_or_none()
            r_od_f = r_od_f.scalars().one_or_none()
            r_minus_40_f = r_minus_40_f.scalars().all()
            r_minus_20_f = r_minus_20_f.scalars().all()
            r_plus_20_f = r_plus_20_f.scalars().all()
            r_plus_40_f = r_plus_40_f.scalars().all()
            od_r_to = od_r_to.scalars().one_or_none()
            ot_r_to = ot_r_to.scalars().all()
            result_to = result_to.scalars().one_or_none()

            if (result_f is None) or (result_f.user_id is None):
                return None, None, 62

            if (user_id != result_f.user_id) and (48 not in force_codes):
                return result_f.user_id, result_f.user_name, 48

            if (result_to is not None) and result_to.user_id:
                return result_to.user_id, result_to.user_name, 63

            if (od_r_to is not None) and od_r_to.user_id:
                return od_r_to.user_id, od_r_to.user_name, 63

            for r in ot_r_to:
                # (r != result_f) - это ключевое условие
                if r.user_id and (r != result_f):
                    return r.user_id, r.user_name, 63

            if ((od_r_to is not None)
               and (od_r_to.doctor_id in [1, 2])
               and od_r_to.available_from_admin
               and (52 not in force_codes)):
                return None, None, 52

            if (user_id != result_f.user_id) and (49 not in force_codes):
                return result_f.user_id, result_f.user_name, 49

            user_id_app = result_f.user_id
            user_name = result_f.user_name

            if ((result_to is not None)
               and (not result_to.available_from_admin)
               and (44 not in force_codes)):
                return None, None, 44

            if result_to is not None:
                result_to.user_name = user_name
                result_to.user_id = user_id_app
                result_to.available_from_user = False
            elif (43 not in force_codes):
                return None, None, 43
            else:
                new_available_appointment = Appointments(
                    user_id=user_id_app,
                    user_name=user_name,
                    doctor_id=doctor_id_to,
                    time=time_to,
                    available_from_user=False,
                    available_from_admin=False)
                session.add(new_available_appointment)
                await session.flush()

            result_f.user_id = None
            result_f.user_name = None
            result_f.available_from_user = True

            if r_od_f is not None:
                cond = ((r_od_f.user_id is None) and
                        (not any([r.user_id for r in
                                  (r_minus_20_f + r_plus_20_f)])))
                if cond:
                    r_od_f.available_from_user = True

            if not any([r.user_id for r in r_minus_40_f + r_minus_20_f]):
                if (r_od_f is None) or (r_od_f.user_id is None):
                    for r in r_minus_20_f:
                        r.available_from_user = True
            if not any([r.user_id for r in r_plus_40_f + r_plus_20_f]):
                if (r_od_f is None) or (r_od_f.user_id is None):
                    for r in r_plus_20_f:
                        r.available_from_user = True

            for r in ot_r_to:
                r.available_from_user = False
            if od_r_to is not None:
                od_r_to.available_from_user = False
            await session.commit()
            return None, None, 14

    @staticmethod
    async def check_user(user_id: int,
                         user_name: str = None) -> tuple[bool, bool]:
        '''Метод проверяет, что пользователь не забанен и что он
        является новым пользователем. Если пользователь новый, то он
        добавляется в таблицу, где лежат все пользователи
        input:
            user_id: int - id пользователя
            user_name: str - имя пользователя
        ouput:
            tuple[bool, bool]
            первое значение - True, если пользователь забанен, иначе False
            второе значение - True, если пользователь новый, иначе False
        '''

        async with async_session() as session:
            query = select(Users).filter_by(user_id=user_id)
            result = await session.execute(query)
            result = result.scalars().one_or_none()
            if result:
                return result.banned, False
            new_user = Users(user_id=user_id,
                             banned=False,
                             user_name=user_name)
            session.add(new_user)
            await session.flush()
            await session.commit()
            return False, True

    @staticmethod
    async def get_user(user_id: int):
        '''Метод возвращает строку с пользователем, если он есть в базе данных
        input:
            user_id: int - id пользователя
        '''

        async with async_session() as session:
            query = select(Users).filter_by(user_id=user_id)
            result = await session.execute(query)
            result = result.scalars().one_or_none()
            return result

    @staticmethod
    async def get_users():
        '''Метод возвращает записи из таблицы users
        '''

        async with async_session() as session:
            query = select(Users)
            result = await session.execute(query)
            result = result.scalars().all()
            return result

    @staticmethod
    async def change_visited_field(time: datetime = None,
                                   doctor_id: list[int] = None,
                                   skipped: bool = False):
        '''Метод меняет поле visited в записи пользователя'''
        async with async_session() as session:
            query = (select(Appointments)
                     .filter(Appointments.doctor_id.in_(doctor_id))
                     .filter_by(time=time))
            result = (await session.execute(query)).scalars().one_or_none()
            if (result is None) or (result.user_id is None):
                return False
            result.skipped = skipped
            await session.flush()
            await session.commit()
            return True

    @staticmethod
    async def ban_user(user_id: int) -> int:
        '''Метод для блокировки пользователя
        Перед вызовом метода необходимо проверить, что мы не пытаемся забанить
        администратора!

        input:
            user_id: int - id пользователя
        output:
            статус код
        '''
        async with async_session() as session:
            query = select(Users).filter_by(user_id=user_id)
            result = await session.execute(query)
            result = result.scalars().one_or_none()
            if result:
                if result.banned:
                    return 21
                result.banned = True
                await session.flush()
                await session.commit()
                return 16
            return 45

    @staticmethod
    async def unban_user(user_id: int) -> int:
        '''Метод для разблокировки пользователя
        input:
            user_id: int - id пользователя
        output:
            статус код
        '''
        async with async_session() as session:
            query = select(Users).filter_by(user_id=user_id)
            result = await session.execute(query)
            result = result.scalars().one_or_none()
            if result:
                if not result.banned:
                    return 22
                result.banned = False
                await session.flush()
                await session.commit()
                return 17
            return 45

    @staticmethod
    async def del_user_visits(user_id: int,
                              date_from: datetime = None,
                              date_to: datetime = None,
                              doctor_id: list[int] = None
                              ) -> None:

        '''Метод удаляет записи по условию

        input:
            user_id: int - id пользователя
            date_from: datetime - дата от которой находить действия
            date_to: datetime - дата до которой находить действия
            doctor_id: list[int]
        '''

        async with async_session() as session:
            query = select(Appointments).filter_by(user_id=user_id)
            if date_from:
                query = query.filter(Appointments.time >= date_from)
            if date_to:
                query = query.filter(Appointments.time < date_to)
            if doctor_id:
                query = query.filter(Appointments.doctor_id.in_(doctor_id))
            result = await session.execute(query)

            result = result.scalars().all()
            for res in result:
                res.user_id = None
                res.user_name = None
                res.available = True
            await session.flush()
            await session.commit()

    @staticmethod
    async def create_log(user_id: int,
                         action_type: str,
                         action: str,
                         action_time: datetime,
                         ) -> None:
        async with async_session() as session:
            log = Logs(user_id=user_id,
                       action_type=action_type,
                       action=action,
                       action_time=action_time)
            session.add(log)
            await session.commit()

    @staticmethod
    async def get_logs(user_ids: list[int] = None,
                       date_from: datetime = None,
                       date_to: datetime = None,
                       action_types: list[str] = None
                       ) -> list[Logs]:

        async with async_session() as session:
            query = select(Logs)
            if user_ids is not None:
                query = query.filter(Logs.user_id.in_(user_ids))
            if date_from:
                query = query.filter(Logs.action_time >= date_from)
            if date_to:
                query = query.filter(Logs.action_time <= date_to)
            if action_types:
                query = query.filter(Logs.action_type.in_(action_types))
            query = query.order_by(Logs.action_time.desc())
            result = await session.execute(query)
            result = result.scalars().all()
            return result

    @staticmethod
    async def raw_query(query: str):
        '''Метод выполняет любой текстовый запрос к бд'''
        async with async_session() as session, lock:
            result = await session.execute(text(query))
            return result.scalars().all()
