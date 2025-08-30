from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from database.handlers import AsyncORM
from keyboards.keyboards import (get_main_user_kb,
                                 get_doctors_kb,
                                 get_back_kb,
                                 get_universal_kb,
                                 get_doctors_kb_short,
                                 get_back_to_main_kb,
                                 get_times_kb_user,
                                 get_dates_kb_short)
from create_bot import (registrators,
                        admins,
                        user_appointment_limit,
                        chat_id,
                        user_treatment_limit)
from filters.filters import IsUser
from utils.utils import (get_doctor_name_by_id,
                         to_datetime,
                         get_day_by_index,
                         reply_to_log,
                         get_reply)
from utils.async_functions import (back_to_main_user,
                                   check_user_limits,
                                   get_user_info,
                                   get_answer_type)
from aiogram.fsm.context import FSMContext
from handlers.fsm import UserForm
from datetime import datetime, timedelta


user_router = Router()
user_router.message.filter(IsUser(admins, registrators))


@user_router.message(CommandStart())
async def start(message: Message,
                state: FSMContext):
    '''Обрабатывает команду /start'''
    await state.clear()
    apps, treats, _ = await AsyncORM.get_records_for_main_menu(
        message.from_user.id)
    reply = 'Добро пожаловать в бот медицинского центра ЛОР плюс'
    if apps:
        reply += '\n\n<b>Записи на приём:</b>'
        for index, app in enumerate(apps, 1):
            day_name = get_day_by_index(app.time.weekday())

            reply += f'\n<b>{index}.</b> '
            reply += f'Дата: <b>{app.time.strftime("%d.%m.%Y %H:%M")} '
            reply += f'({day_name})</b>, '
            reply += f'Врач: <b>{get_doctor_name_by_id(app.doctor_id)}</b>'

    if treats:
        reply += '\n\n<b>Записи на лечение:</b>'
        for index, treat in enumerate(treats, len(apps) + 1):
            day_name = get_day_by_index(treat.time.weekday())

            reply += f'\n<b>{index}.</b> '
            reply += f'Дата: <b>{treat.time.strftime("%d.%m.%Y %H:%M")} '
            reply += f'({day_name})</b>'

    reply += '\n\n<b>Выберите действие:</b>'

    await message.answer(
        text=reply,
        reply_markup=get_main_user_kb(
            ((len(apps) < user_appointment_limit)
             or (len(treats) < user_treatment_limit)),
            (len(apps) or len(treats)),
            another=len(apps + treats)))


@user_router.callback_query(F.data.contains('get_user_main_kb'))
async def return_main_kb(call: CallbackQuery, state: FSMContext):
    '''
    Функция возвращает главное меню
    '''
    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    await call.answer()
    await state.clear()
    apps, treats, _ = await AsyncORM.get_records_for_main_menu(
        call.from_user.id)

    reply = 'Добро пожаловать в бот медицинского центра ЛОР плюс'

    if apps:
        reply += '\n\n<b>Записи на приём:</b>'
        for index, app in enumerate(apps, 1):
            day_name = get_day_by_index(app.time.weekday())

            reply += f'\n<b>{index}.</b> '
            reply += f'Дата: <b>{app.time.strftime("%d.%m.%Y %H:%M")} '
            reply += f'({day_name})</b>, '
            reply += f'Врач: <b>{get_doctor_name_by_id(app.doctor_id)}</b>'

    if treats:
        reply += '\n\n<b>Записи на лечение:</b>'
        for index, treat in enumerate(treats, len(apps) + 1):
            day_name = get_day_by_index(treat.time.weekday())
            reply += f'\n<b>{index}.</b> '
            reply += f'Дата: <b>{treat.time.strftime("%d.%m.%Y %H:%M")} '
            reply += f'({day_name})</b>'

    reply += '\n\n<b>Выберите действие:</b>'

    answer = await get_answer_type(call)
    await answer(
        text=reply,
        reply_markup=get_main_user_kb(
            ((len(apps) < user_appointment_limit)
             or (len(treats) < user_treatment_limit)),
            (len(apps) or len(treats)),
            another=len(apps + treats)))


@user_router.callback_query(F.data.contains('app_user_choice'))
async def choose_app(call: CallbackQuery, state: FSMContext):
    '''
    Функция позволяет пользователю выбрать запись,
    которую он хочет удалить или переместить. Возвращает
    клавиатуру с текущими записями
    '''
    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    await call.answer()
    q_type = call.data.split()[0]
    await state.clear()
    await state.update_data(action_type=q_type)

    apps, treats, _ = await AsyncORM.get_records_for_main_menu(
        call.from_user.id)

    reply = get_reply(q_type=q_type)
    answer = await get_answer_type(call)

    if (len(apps) == 0) and (len(treats) == 0):
        prev_reply = '<b>Ошибка\n'
        prev_reply += 'Действующих записей на приём не обнаружено</b>\n'
        return await answer(
            text=prev_reply + reply,
            reply_markup=get_back_to_main_kb('get_user_main_kb'))

    button_texts = []
    c_data = []
    if apps:
        reply += '\n<b>Записи на приём:</b>'
        for index, app in enumerate(apps, 1):
            tm = app.time.strftime("%d.%m.%Y %H:%M")
            day_name = get_day_by_index(app.time.weekday())
            doctor_name = get_doctor_name_by_id(app.doctor_id)
            doctor_name_short = get_doctor_name_by_id(
                app.doctor_id, case="short")

            reply += f'\n<b>{index}.</b> '
            reply += f'Дата: <b>{tm} ({day_name})</b>, '
            reply += f'Врач: <b>{doctor_name}</b>'

            button_texts.append(f'{index}. {tm} {doctor_name_short}')
            c_data.append(f'{q_type} get_user_app|{app.doctor_id} {tm}')

    if treats:
        reply += '\n\n<b>Записи на лечение:</b>'
        for index, treat in enumerate(treats, len(apps) + 1):
            tm = treat.time.strftime("%d.%m.%Y %H:%M")
            day_name = get_day_by_index(treat.time.weekday())

            reply += f'\n{index}. '
            reply += f'Дата: <b>{tm} ({day_name})</b>'

            button_texts.append(f'{index}. {tm} лечение')
            c_data.append(f'{q_type} get_user_app|5 {tm}')

    if 'move_user_app' in call.data:
        reply += '\n\n<b>Выберите запись, которую хотите перенести:</b>'
    elif 'del_user_app' in call.data:
        reply += '\n\n<b>Выберите запись, которую хотите удалить:</b>'
    await state.set_state(UserForm.doctor_id_from)
    await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=button_texts,
            qs_back=c_data,
            tp='get_user_main_kb edit'
        )
    )


@user_router.callback_query(F.data.contains('get_user_app'),
                            StateFilter(UserForm.doctor_id_from,
                                        UserForm.date))
async def handle_app(call: CallbackQuery, state: FSMContext):
    '''
    Функция обрабатывает выбранную запись и в зависимости от этого
    возвращает нужную клавиатуру
    '''
    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main_user(call, state)

    if "|" in call.data:
        doctor_id, date, time = call.data.split("|")[-1].split()
        await state.update_data(doctor_id_from=int(doctor_id),
                                date_from=date,
                                time_from=time)

    data = await state.get_data()
    doctor_id = None
    if q_type == "move_user_app" and (data['doctor_id_from'] >= 3):
        doctor_id = data['doctor_id_from']

    reply = get_reply(q_type=q_type,
                      doctor_id_from=data.get('doctor_id_from'),
                      date_from=data.get('date_from'),
                      time_from=data.get('time_from'),
                      doctor_id=doctor_id)

    answer = await get_answer_type(call)

    dt = to_datetime(data['date_from'], data['time_from'])

    db_data = await AsyncORM.get_visits(
        user_id=call.from_user.id, date_from=dt,
        date_to=dt, doctor_id=[data['doctor_id_from']])

    if len(db_data) == 0:
        prev_reply = '<b>Ошибка!'
        prev_reply += '\nВыбранная вами запись больше не существует</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_back_to_main_kb('get_user_main_kb')
        )

    if q_type == 'del_user_app':
        reply += '\n<b>Подтвердить удаление записи?</b>'
        return await answer(
            text=reply,
            reply_markup=get_universal_kb(
                texts_back=['Удалить запись', 'Выбрать другую запись'],
                qs_back=[f'{q_type} del_app_approve',
                         f'{q_type} app_user_choice'],
                tp='get_user_main_kb edit'))

    elif (q_type == 'move_user_app') and (data['doctor_id_from'] in [0, 1, 2]):
        reply += '\n<b>Выберите врача, к которому вы хотите '
        reply += 'перенести запись:</b>'
        await state.set_state(UserForm.doctor_id)
        return await answer(
            text=reply,
            reply_markup=get_doctors_kb_short(
                q_type=f'{q_type} choose_user_date',
                q_back=f'{q_type} app_user_choice',
                doctor_id=data['doctor_id_from']
            ))

    elif q_type == 'move_user_app':
        await state.update_data(doctor_id=data['doctor_id_from'])
        await state.set_state(UserForm.date)
        apps = await AsyncORM.get_visits(
            doctor_id=[data['doctor_id_from']],
            date_from=datetime.now(),
            available=True)

        dates = [app.time for app in apps]
        if len(dates) == 0:
            prev_reply = '<b>Ошибка!\nУ врача нет'
            prev_reply += ' других свободных слотов для записи\n</b>'
            reply = prev_reply + reply
            return await answer(
                text=reply,
                reply_markup=get_back_kb(None, 'get_user_main_kb edit')
            )

        reply += '\n<b>Выберите дату:</b>'
        await answer(
            text=reply,
            reply_markup=get_dates_kb_short(
                q_type=q_type + ' choose_user_time',
                dates=dates,
                q_back=f'{q_type} app_user_choice',
                add_days=0,
                days_per_kb=6,
                main_query='get_user_main_kb edit'))


@user_router.callback_query(F.data.contains('choose_user_doctor'))
async def choose_doctor(call: CallbackQuery, state: FSMContext):
    '''Функция позволяет выбрать врача при записи на приём'''
    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    await call.answer()
    q_type = call.data.split()[0]

    answer = await get_answer_type(call)
    await state.update_data(action_type=q_type)

    reply = get_reply(q_type=q_type)

    app_ok, treat_ok = await check_user_limits(call.from_user.id)

    if (not app_ok) and (not treat_ok):
        prev_reply = '<b>Ошибка!\nПревышен лимит на количество записей</b>'
        prev_reply += 'Удалите одну из сущестующих записей прежде чем'
        prev_reply += 'сделать новую'
        return await answer(
            text=prev_reply + reply,
            reply_markup=get_back_to_main_kb(
                'get_user_main_kb edit'
            ))

    reply += '\n<b>Выберите врача:</b>'
    await state.set_state(UserForm.doctor_id)
    return await answer(
        text=reply,
        reply_markup=get_doctors_kb(
            q_type=q_type + ' choose_user_date',
            q_main='get_user_main_kb edit',
            show_doctors=app_ok,
            show_treatment=treat_ok,
            show_any_lor=True,
        )
    )


@user_router.callback_query(F.data.contains('choose_user_date')
                            | F.data.contains('other_dates'),
                            StateFilter(UserForm.date, UserForm.doctor_id,
                                        UserForm.time))
async def choose_date(call: CallbackQuery, state: FSMContext):
    '''Возвращает клавиатуру с выбором даты'''
    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None

    await call.answer()
    q_type = call.data.split()[0]
    answer = await get_answer_type(call)

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main_user(call, state)

    if (await state.get_state()) in [UserForm.doctor_id.state]:
        await state.update_data(doctor_id=int(call.data.split('|')[-1]))

    app_ok, treat_ok = await check_user_limits(call.from_user.id)

    data = await state.get_data()

    if q_type == 'make_user_app':
        reply = get_reply(q_type=q_type,
                          doctor_id=data.get('doctor_id'))

    elif q_type == 'move_user_app':
        reply = get_reply(q_type=q_type,
                          doctor_id_from=data.get('doctor_id_from'),
                          date_from=data.get('date_from'),
                          time_from=data.get('time_from'),
                          doctor_id=data.get('doctor_id'))
        dt = to_datetime(data['date_from'], data['time_from'])
        db_data = await AsyncORM.get_visits(
            user_id=call.from_user.id, date_from=dt,
            date_to=dt, doctor_id=[data['doctor_id_from']])

        if len(db_data) == 0:
            prev_reply = '<b>Ошибка!'
            prev_reply += '\nВыбранная вами запись больше не существует</b>'
            await answer(
                text=prev_reply + reply,
                reply_markup=get_back_to_main_kb('get_user_main_kb')
            )

    if (q_type == 'make_user_app') and (not app_ok) and (not treat_ok):
        prev_reply = '<b>Ошибка!\nПревышен лимит на количество записей</b>'
        prev_reply += 'Удалите одну из сущестующих записей прежде чем'
        prev_reply += 'сделать новую'
        return await answer(
            text=prev_reply + reply,
            reply_markup=get_back_to_main_kb(
                'get_user_main_kb edit'))

    if 'other_dates' in call.data:
        add_days = int(call.data.split('|')[-1])
    else:
        add_days = 0

    await state.set_state(UserForm.date)

    if data['doctor_id'] == 0:
        doctor_q = [1, 2]
    else:
        doctor_q = [data['doctor_id']]

    apps = await AsyncORM.get_visits(
        doctor_id=doctor_q, date_from=datetime.now(), available=True)
    dates = [app.time for app in apps]

    if q_type == 'move_user_app':
        dt = to_datetime(data['date_from'], data['time_from'])
        sp_dates = await AsyncORM.get_visits_movement(
                    time=dt,
                    doctor_id=data['doctor_id'],
                    available_from_admin=True)

        dates = sorted(dates + sp_dates)

    if q_type == 'move_user_app':
        if data['doctor_id'] in [0, 1, 2]:
            q_back = f'{q_type} get_user_app'
        else:
            q_back = f'{q_type} app_user_choice'
    elif q_type == 'make_user_app':
        q_back = f'{q_type} choose_user_doctor'

    if (len(dates) == 0) or (len(dates[add_days:]) == 0):
        prev_reply = '<b>Ошибка!\nУ врача нет'
        prev_reply += ' других' if q_type == 'move_user_app' else ''
        prev_reply += ' свободных слотов для записи\n</b>'
        reply = prev_reply + reply
        print(reply)
        return await answer(
            text=reply,
            reply_markup=get_back_kb(q_back, 'get_user_main_kb edit')
        )

    reply += '\n<b>Выберите дату:</b>'

    q_type += ' choose_user_time'
    await answer(
        text=reply,
        reply_markup=get_dates_kb_short(
            q_type=q_type,
            dates=dates,
            q_back=q_back,
            add_days=add_days,
            days_per_kb=6,
            main_query='get_user_main_kb edit'))


@user_router.callback_query(F.data.contains('choose_user_time'),
                            StateFilter(UserForm.date, UserForm.time))
async def choose_time(call: CallbackQuery, state: FSMContext):
    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    '''Позволяет пользователю выбрать время для записи. Возвращает
    клавиатуру с временем
    '''
    await call.answer()
    q_type = call.data.split()[0]
    answer = await get_answer_type(call)

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main_user(call, state)

    if (await state.get_state()) in [UserForm.date.state]:
        await state.update_data(date=call.data.split('|')[-1])

    data = await state.get_data()

    if q_type == 'move_user_app':
        reply = get_reply(q_type=q_type,
                          doctor_id_from=data.get('doctor_id_from'),
                          date_from=data.get('date_from'),
                          time_from=data.get('time_from'),
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'))

    elif q_type == 'make_user_app':
        reply = get_reply(q_type=q_type,
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'))

    app_ok, treat_ok = await check_user_limits(call.from_user.id)
    if (q_type == 'make_user_app') and (not app_ok) and (not treat_ok):
        prev_reply = '<b>Ошибка!\nПревышен лимит на количество записей</b>'
        prev_reply += 'Удалите одну из сущестующих записей прежде чем'
        prev_reply += 'сделать новую'
        return await answer(
            text=prev_reply + reply,
            reply_markup=get_back_to_main_kb(
                'get_user_main_kb edit'))

    if q_type == 'move_user_app':
        dt = to_datetime(data['date_from'], data['time_from'])
        db_data = await AsyncORM.get_visits(
            user_id=call.from_user.id, date_from=dt,
            date_to=dt, doctor_id=[data['doctor_id_from']])

        if len(db_data) == 0:
            prev_reply = '<b>Ошибка!'
            prev_reply += '\nВыбранная вами запись больше не существует</b>'
            await answer(
                text=prev_reply + reply,
                reply_markup=get_back_to_main_kb('get_user_main_kb')
            )

    await state.set_state(UserForm.time)
    dt = to_datetime(data['date'])

    if data['doctor_id'] == 0:
        doctor_q = [1, 2]
    else:
        doctor_q = [data['doctor_id']]

    apps = await AsyncORM.get_visits(
        doctor_id=doctor_q,
        date_from=dt,
        date_to=dt + timedelta(days=1),
        available=True)

    dates = [app.time for app in apps if app.time > datetime.now()]

    if q_type == 'move_user_app':
        dt_from = to_datetime(data['date_from'], data['time_from'])
        add_dates = await AsyncORM.get_visits_movement(
            time=dt_from,
            doctor_id=data['doctor_id'],
            available_from_admin=True)

        dates += [time for time in add_dates
                  if (time < (dt_from + timedelta(days=1)))
                  and (time > dt_from)]

    if (len(dates) == 0) or (max(dates) < datetime.now()):
        prev_reply = '<b>Ошибка!\n'
        prev_reply += 'На выбранную дату нет свободных записей</b>\n'
        reply = prev_reply + reply
        return await answer(
            text=reply,
            reply_markup=get_universal_kb(
                texts_back=['Выбрать другую дату'],
                qs_back=[f'{q_type} choose_user_date'],
                tp='get_user_main_kb edit'))

    reply += '\n<b>Выберите время:</b>'
    await answer(
        text=reply, reply_markup=get_times_kb_user(
            q_type=q_type + ' set_user_time',
            q_back=q_type + ' choose_user_date',
            dates=dates,
            doctor_id=data['doctor_id'],
            q_main='get_user_main_kb edit')
        )


@user_router.callback_query(F.data.contains('set_user_time'),
                            StateFilter(UserForm.time))
async def approve_time(call: CallbackQuery, state: FSMContext):
    '''
    Функция подтверждает выбор времени при добавлении и
    переносе записи
    '''

    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main_user(call, state)

    if '|' in call.data:
        await state.update_data(time=call.data.split('|')[-1])

    data = await state.get_data()
    answer = await get_answer_type(call)

    app_ok, treat_ok = await check_user_limits(call.from_user.id)
    if (q_type == 'make_user_app') and (not app_ok) and (not treat_ok):
        reply = '<b>Ошибка!\nПревышен лимит на количество записей</b>'
        reply += 'Удалите одну из сущестующих записей прежде чем'
        reply += 'сделать новую\n'
        reply += get_reply(q_type=q_type,
                           doctor_id=data.get('doctor_id'),
                           date=data.get('date'),
                           time=data.get('time'))
        return await answer(
            text=reply,
            reply_markup=get_back_to_main_kb(
                'get_user_main_kb edit'))

    dt = to_datetime(data['date'], data['time'])
    if data['doctor_id'] == 0:
        doctor_q = [1, 2]
    else:
        doctor_q = [data['doctor_id']]

    app = await AsyncORM.get_visits(
        doctor_id=doctor_q, date_from=dt, date_to=dt)
    app = [x for x in app if x.available_from_admin]

    doctor_true = None
    if (len(app) == 1) and (data['doctor_id'] == 0):
        doctor_true = app[0].doctor_id
    elif (len(app) != 1) and (data['doctor_id'] == 0):
        reply = '<b>Неизвестная ошибка на стороне сервера</b>'
        reply += 'Попробуйте выбрать врача, не используя кнопку "Любой ЛОР"'
        reply += ' при выборе врача'
        return await answer(
            text=reply,
            reply_markup=get_back_to_main_kb('get_user_main_kb edit'))

    if q_type == 'move_user_app':
        reply = get_reply(q_type=q_type,
                          doctor_id_from=data.get('doctor_id_from'),
                          date_from=data.get('date_from'),
                          time_from=data.get('time_from'),
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'),
                          time=data.get('time'),
                          doctor_true=doctor_true)

    elif q_type == 'make_user_app':
        reply = get_reply(q_type=q_type,
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'),
                          time=data.get('time'),
                          doctor_true=doctor_true)

    if ('approve' in call.data) and (dt > datetime.now()) and (len(app) == 1):

        if q_type == 'make_user_app':
            _, _, status_code = await (
                AsyncORM.add_new_visit(
                    user_id=call.from_user.id,
                    doctor_id=app[0].doctor_id,
                    time=dt,
                    user_name=('@' + call.from_user.username
                               if call.from_user.username else None),
                    force_codes=[46]))

        elif q_type == 'move_user_app':
            _, _, status_code = await (
                AsyncORM.move_visit_time(
                    user_id=call.from_user.id,
                    doctor_id_from=data['doctor_id_from'],
                    doctor_id_to=app[0].doctor_id,
                    time_from=to_datetime(data['date_from'],
                                          data['time_from']),
                    time_to=dt
                    )
            )

        if (status_code < 40) and (q_type == 'make_user_app'):
            prev_reply = '<b>Успешно!</b>\n'
            prev_reply += '<b>Вы были записаны на приём</b>\n'

            await answer(
                text=prev_reply + '\n'.join(reply.split('\n')[1:]),
                reply_markup=get_back_to_main_kb('get_user_main_kb rm_mk')
            )
            user_info = await get_user_info(
                call.from_user.id,
                ('@' + call.from_user.username
                 if call.from_user.username else None),
                make_app=True)

            await call.bot.send_message(
                chat_id=chat_id, text=reply + '\n' + user_info)
            if data['doctor_id'] == 3:
                pass
                # await call.bot.send_message(chat_id=, text=reply)

            log = reply_to_log(reply)
            await AsyncORM.create_log(user_id=call.from_user.id,
                                      action_type='make_app',
                                      action=log,
                                      action_time=datetime.now())

        elif (status_code < 40) and (q_type == 'move_user_app'):
            prev_reply = '<b>Успешно!</b>\n'
            prev_reply += '<b>Вы перенсли свою запись</b>\n'
            reply = reply.replace('Текущая', 'Старая')
            await answer(
                text=prev_reply + '\n'.join(reply.split('\n')[1:]),
                reply_markup=get_back_to_main_kb('get_user_main_kb rm_mk')
            )

            user_info = await get_user_info(
                call.from_user.id,
                ('@' + call.from_user.username
                 if call.from_user.username else None),
                move_app=True)
            await call.bot.send_message(
                chat_id=chat_id, text=reply + '\n' + user_info)

            if data['doctor_id'] == 3:
                pass
                # await call.bot.send_message(chat_id=, text=reply)

            log = reply_to_log(reply)
            await AsyncORM.create_log(user_id=call.from_user.id,
                                      action_type='move_app',
                                      action=log,
                                      action_time=datetime.now())
        else:
            prev_reply = '<b>\nОшибка!\nК сожалению, '
            prev_reply += 'на данное время невозможно записаться</b>\n'
            reply = prev_reply + reply
            return await answer(
                text=reply,
                reply_markup=get_universal_kb(
                    texts_back=['Выбрать другое время'],
                    qs_back=[f'{q_type} choose_user_time'],
                    tp='get_user_main_kb'))

    elif (dt > datetime.now()) and (len(app) == 1):
        if q_type == 'make_user_app':
            reply += '\n<b>Подтвердить запись?</b>'
            texts_back = ['Подтвердить запись', 'Выбрать другое время']
        elif q_type == 'move_user_app':
            reply += '\n<b>Перенести запись?</b>'
            texts_back = ['Перенести запись', 'Выбрать другое время']
        return await answer(
            text=reply,
            reply_markup=get_universal_kb(
                texts_back=texts_back,
                qs_back=[f'{q_type} set_user_time approve',
                         f'{q_type} choose_user_time'],
                tp='get_user_main_kb edit'))
    else:
        prev_reply = '<b>\nОшибка!\nК сожалению, '
        prev_reply += 'на данное время невозможно записаться</b>\n'
        reply = prev_reply + reply
        return await answer(
            text=reply,
            reply_markup=get_universal_kb(
                texts_back=['Выбрать другое время'],
                qs_back=[f'{q_type} choose_user_time'],
                tp='get_user_main_kb'))


@user_router.callback_query(F.data.contains('del_app_approve'),
                            StateFilter(UserForm.doctor_id_from,
                                        UserForm.date))
async def del_user_app(call: CallbackQuery, state: FSMContext):
    '''
    Функция подтвеждает удаление записи
    '''

    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    q_type = call.data.split()[0]
    answer = await get_answer_type(call)

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main_user(call, state)

    data = await state.get_data()

    dt = to_datetime(data['date_from'], data['time_from'])

    _, _, status_code = await AsyncORM.del_appointment(
        user_id=call.from_user.id,
        doctor_id=data['doctor_id_from'],
        time=dt)

    reply = get_reply(q_type=q_type,
                      doctor_id=data.get('doctor_id_from'),
                      date=data.get('date_from'),
                      time=data.get('time_from'))

    if status_code < 40:
        prev_reply = '<b>Успешно!\n'
        prev_reply += 'Запись была удалена</b>\n'

        await answer(
            text=prev_reply + '\n'.join(reply.split('\n')[1:]),
            reply_markup=get_back_to_main_kb('get_user_main_kb rm_mk'))

        user_info = await get_user_info(
            call.from_user.id,
            '@' + call.from_user.username if call.from_user.username else None,
            remove_app=True)
        await call.bot.send_message(
            chat_id=chat_id, text=reply + '\n' + user_info)
        if data['doctor_id_from'] == 3:
            pass
            # await call.bot.send_message(chat_id=, text=reply)

        log = reply_to_log(reply)
        await AsyncORM.create_log(user_id=call.from_user.id,
                                  action_type='remove_app',
                                  action=log,
                                  action_time=datetime.now())
    else:
        prev_reply = '<b>\nОшибка!\nНе удалось удалить запись</b>\n'
        return await answer(
            text=prev_reply + reply,
            reply_markup=get_back_to_main_kb('get_user_main_kb edit'))


@user_router.callback_query(F.data == 'info')
async def info(call: CallbackQuery, state: FSMContext):
    '''
    Функция возвращает информацию о больнице
    '''

    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    await call.answer()
    await state.clear()
    with open('../data/text_docs/info.txt', 'r', encoding="UTF-8") as f:
        reply = f.read()

    answer = await get_answer_type(call)

    return await answer(
            text=reply,
            reply_markup=get_back_to_main_kb('get_user_main_kb edit'))


@user_router.callback_query(F.data == 'prices')
async def prices(call: CallbackQuery, state: FSMContext):
    '''
    Функция отправляет пользователю цены на услуги
    '''

    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    await call.answer()
    await state.clear()
    reply = 'Информация об услугах находится в отправленном выше файле'
    with open('../data/text_docs/Цены.pdf', "rb") as file:
        await call.message.answer_document(
                document=BufferedInputFile(
                    file.read(),
                    filename="Услуги.pdf"
                ),
                text=reply
            )
    await call.message.delete()
    return await call.message.answer(
            text=reply,
            reply_markup=get_back_to_main_kb('get_user_main_kb edit'))
