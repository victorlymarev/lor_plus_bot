from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
import pandas as pd
from omegaconf import OmegaConf
from database.handlers import AsyncORM
from create_bot import (admins,
                        registrators,
                        chat_id,
                        logger,
                        day_config,
                        week_config,
                        m_final_short)
from filters.filters import IsAdmin
from keyboards.keyboards import (get_main_admin_kb,
                                 get_admin_kb,
                                 get_doctors_kb,
                                 get_dates_kb,
                                 get_weeks_kb,
                                 get_dates_kb_short,
                                 get_doctors_kb_short,
                                 get_data_kb,
                                 get_back_kb,
                                 get_times_kb_admin,
                                 get_open_close_kb,
                                 get_universal_kb,
                                 get_weekdays_kb,
                                 get_times_kb_user,
                                 get_add_day_kb,
                                 get_simple_times_kb,
                                 get_add_week_kb,
                                 get_actions_with_user_kb
                                 )
from aiogram.fsm.context import FSMContext
from handlers.fsm import Form
from utils.utils import (get_doctor_name_by_id,
                         to_datetime,
                         get_day_by_index,
                         reply_to_log,
                         get_success_messege,
                         generate_appointments_excel,
                         generate_logs_excel,
                         generate_users_excel,
                         get_warning_message,
                         get_curren_month_year,
                         handle_dates,
                         get_reply)
from utils.async_functions import (back_to_main,
                                   get_log,
                                   get_answer_type,
                                   get_critical_messege)
from datetime import datetime, timedelta


admin_router = Router()
admin_router.message.filter(IsAdmin(admins + registrators))


@admin_router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    '''Функция отрабатывает на команду /start и возвращает главное меню'''
    log = await get_log(message=message, state=state)
    logger.info(log)
    await state.clear()
    is_admin = message.from_user.id in admins
    await message.answer(
        text='Главное меню',
        reply_markup=get_main_admin_kb(add_admin_button=is_admin))


@admin_router.callback_query(F.data.startswith('main'))
async def return_main_kb(call: CallbackQuery, state: FSMContext):
    '''Функция возвращает главное меню'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    await state.clear()
    is_admin = call.from_user.id in admins
    if 'rm_all' in call.data:
        await call.message.answer(
            text='Главное меню',
            reply_markup=get_main_admin_kb(add_admin_button=is_admin))
        await call.message.delete()

    elif 'rm_mk' in call.data:
        await call.message.answer(
            text='Главное меню',
            reply_markup=get_main_admin_kb(add_admin_button=is_admin))
        await call.message.edit_reply_markup(reply_markup=None)

    elif 'edit' in call.data:
        await call.message.edit_text(
            text='Главное меню',
            reply_markup=get_main_admin_kb(add_admin_button=is_admin))


@admin_router.callback_query(F.data == 'admin_kb')
async def return_admin_kb(call: CallbackQuery, state: FSMContext):
    '''Функция возвращает панель администратора'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    await state.clear()
    answer = await get_answer_type(call)
    await answer(
        text='Панель администратора',
        reply_markup=get_admin_kb()
    )


@admin_router.callback_query(F.data == 'open_close_date')
async def return_open_close_kb(call: CallbackQuery, state: FSMContext):
    '''Функция возвращает панель добавления и закрытия времени'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    await state.clear()
    answer = await get_answer_type(call)
    await answer(
        text='Открытие/закрытие даты',
        reply_markup=get_open_close_kb()
    )


@admin_router.callback_query(F.data.contains('choose_doctor'))
async def choose_doctor(call: CallbackQuery, state: FSMContext):
    '''Функция возвращает клавиатуру с выбором врача

    Типы запросов, которые обрабатываются клавиатурой:
    make_app
    make_app_force
    remove_app
    move_app
    add_time
    add_day
    remove_time
    remove_day
    user_actions_app
    '''
    log = await get_log(call=call, state=state)
    logger.info(log)
    q_type = call.data.split()[0]

    await call.answer()
    await state.clear()
    await state.update_data(action_type=q_type)
    if q_type in ['move_app_ext', 'move_app']:
        await state.set_state(Form.doctor_id_from)
    else:
        await state.set_state(Form.doctor_id)
    answer = await get_answer_type(call)

    reply = get_reply(q_type=q_type)
    reply += '\n<b>Выберите врача:</b>'

    show_any_lor = q_type not in ['add_time', 'add_day', 'remove_day',
                                  'remove_time', 'make_app_force']

    if q_type == 'user_actions_app':
        q_back = 'admin_kb'
    elif q_type in ['add_time', 'add_day', 'remove_time', 'remove_day']:
        q_back = 'open_close_date'
    elif q_type in ['make_app_force', 'move_app_ext']:
        q_back = 'admin_kb'
    else:
        q_back = None

    await answer(
        text=reply,
        reply_markup=get_doctors_kb(
            q_type=q_type + ' choose_date',
            show_doctors=True,
            show_any_lor=show_any_lor,
            show_treatment=True,
            q_back=q_back,
            show_all_actions='remove_day' in call.data)
        )


@admin_router.callback_query(
    StateFilter(Form.doctor_id, Form.date, Form.time,
                Form.doctor_id_from, Form.date_from, Form.time_from),
    F.data.contains('choose_date') | F.data.contains('other_month') |
    F.data.contains('other_dates')
    )
async def choose_date(call: CallbackQuery, state: FSMContext):
    '''Возвращает клавиатуру с выбором даты
    Типы запросов, которые обрабатываются клавиатурой:
    add_time
    add_day
    remove_time
    remove_day
    make_app
    make_app_force
    remove_app
    move_app
    show_date
    user_actions_app
    '''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    # обновляем данные fsm
    st = await state.get_state()

    if st in [Form.doctor_id.state]:
        await state.update_data(doctor_id=int(call.data.split('|')[-1]))
        await state.set_state(Form.date)
    elif st in [Form.doctor_id_from.state]:
        await state.update_data(doctor_id_from=int(call.data.split('|')[-1]))
        await state.set_state(Form.date_from)
    elif st in [Form.time.state]:
        await state.update_data(time=None)
        await state.set_state(Form.date)
    elif st in [Form.time_from.state]:
        await state.update_data(time_from=None)
        await state.set_state(Form.date_from)
    elif st in [Form.date.state]:
        await state.update_data(date=None)
    elif st in [Form.date_from.state]:
        await state.update_data(date_from=None)

    answer = await get_answer_type(call)

    data = await state.get_data()
    # парсим параметры для изменения клавиатуры
    if 'other_month' in call.data:
        month, year = [int(i) for i in call.data.split('|')[-1].split()]
        add_days = 0
    elif 'other_dates' in call.data:
        add_days = int(call.data.split('|')[-1])
        month, year = None, None
    else:
        add_days, month, year = 0, None, None

    # Формируем обратный запрос
    if q_type == 'show_date':
        q_back = None

    elif ((q_type in ['move_app', 'move_app_ext'])
          and (await state.get_state() == Form.date.state)
          and (data.get('doctor_id_from') >= 3)):
        q_back = f'{q_type} choose_time'

    elif ((q_type in ['move_app', 'move_app_ext'])
          and (await state.get_state() == Form.date.state)
          and (data.get('doctor_id_from') < 3)):
        q_back = f'{q_type} handle_app'
    else:
        q_back = f'{q_type} choose_doctor'

    reply = get_reply(
        q_type=q_type,
        doctor_id_from=data.get('doctor_id_from'),
        doctor_id=data.get('doctor_id'),
        date_from=data.get('date_from'),
        date=data.get('date'),
        time_from=data.get('time_from'),
        user_id=data.get('user_id'),
        user_name=data.get('user_name'),
        doctor_true_from=data.get('doctor_true')
        )

    # Для следующих типов запросов всегда возвращаем полную клавиатуру
    if ((q_type in ['add_time', 'add_day', 'make_app_force',
                    'show_date', 'user_actions_app'])
        or ((q_type == 'move_app_ext')
            and (await state.get_state()) == Form.date.state)):

        if q_type == 'move_app_ext':
            reply += '\n<b>Выберите дату новой записи:</b>'
        else:
            reply += '\n<b>Выберите дату:</b>'

        if month is None:
            month, year = get_curren_month_year()

        if q_type in ['add_time', 'make_app_force',
                      'user_actions_app', 'move_app_ext']:
            q_type += ' choose_time'
        elif q_type in ['add_day']:
            q_type += ' set_day'

        await answer(
            text=reply,
            reply_markup=get_dates_kb(
                q_type=q_type,
                q_back=q_back,
                month=month,
                year=year,
                include_sunday=True
            ))
    # для остальных запросов выбираем клавиатуру в зависимости от врача
    # remove_time
    # remove_day
    # make_app
    # remove_app
    # move_app
    else:

        if (await state.get_state() == Form.date_from.state):
            if data['doctor_id_from'] == 0:
                doctor_q = [1, 2]
            elif data['doctor_id_from'] == 6:
                doctor_q = list(range(7))
            else:
                doctor_q = [data['doctor_id_from']]
        else:
            if data['doctor_id'] == 0:
                doctor_q = [1, 2]
            elif data['doctor_id'] == 6:
                doctor_q = list(range(7))
            else:
                doctor_q = [data['doctor_id']]

        if q_type in ['remove_time', 'remove_day', 'remove_app']:
            apps = await AsyncORM.get_visits(
                doctor_id=doctor_q,
                date_from=datetime.now() - timedelta(hours=1))

            if q_type in ['remove_app']:
                dates = [app.time for app in apps if app.user_id]
            elif q_type in ['remove_day', 'remove_time']:
                dates = [app.time for app in apps if app.available_from_admin]

        elif ((q_type in ['move_app', 'move_app_ext'])
                and ((await state.get_state()) == Form.date_from.state)):
            apps = await AsyncORM.get_visits(
                doctor_id=doctor_q, date_from=datetime.now())
            dates = [app.time for app in apps if app.user_id]

        elif q_type == 'move_app':
            apps = await AsyncORM.get_visits(
                doctor_id=doctor_q, date_from=datetime.now())
            dates = [app.time for app in apps if
                     app.available_from_user and app.available_from_admin]
            dt = to_datetime(data.get('date_from'), data.get('time_from'))
            sp_dates = await AsyncORM.get_visits_movement(
                time=dt,
                doctor_id=data['doctor_id'],
                available_from_admin=True)
            dates = sorted(dates + sp_dates)

        elif q_type in ['make_app']:
            apps = await AsyncORM.get_visits(doctor_id=doctor_q,
                                             date_from=datetime.now(),
                                             available=True)
            dates = [app.time for app in apps]

        # делаем проверку, что для клавиатуры есть даты
        if (len(dates) == 0) or (len(dates[add_days:]) == 0):
            prev_reply = '<b>Ошибка!\n'
            prev_reply += 'Не обнаружено дат, соответствующих вашему запросу'
            prev_reply += '\nПопробуйте выбрать врача заново</b>\n'
            reply = prev_reply + reply
            return await answer(
                text=reply,
                reply_markup=get_back_kb(q_back)
            )

        # Обновляем тип запроса, который будем обрабатывать далее
        if q_type == 'remove_day':
            q_type += ' set_day'
        else:
            q_type += ' choose_time'

        # ставим большую клавиатуру в зависимости от врача
        # пока оставляем маленькую клавиатуру для всех врачей
        if data.get('doctor_id') in []:
            if month is None:
                dates, (month, year) = handle_dates(dates)
            else:
                dates, (_, _) = handle_dates(dates)
                # Проверяем условие, что в месяце есть записи
                if len(dates.get((month, year), dict())
                       .get('av_dates', [])):
                    prev_reply += '<b>На данный месяц записи у врача отсутст'
                    prev_reply += 'вуют\nПопробуйте выбрать врача заново</b>'
                    return await answer(
                        text=reply,
                        reply_markup=get_back_kb(q_back)
                    )

            reply += '\n<b>Выберите дату:</b>'
            await answer(
                text=reply,
                reply_markup=get_dates_kb(
                    q_type=q_type,
                    q_back=q_back,
                    month=month,
                    year=year,
                    dates=dates,
                    get_dates_kb=True
                ))
        else:
            reply += '\n<b>Выберите дату:</b>'
            await answer(text=reply,
                         reply_markup=get_dates_kb_short(
                            q_type=q_type,
                            dates=dates,
                            q_back=q_back,
                            add_days=add_days))


@admin_router.callback_query(F.data == 'show_date')
async def show_date(call: CallbackQuery, state: FSMContext):
    '''Функция работает с методом show_date
    Она устанавливает состояние и вызывает функцию с выбором даты
    '''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await state.clear()
    await state.update_data(action_type='show_date')
    await state.set_state(Form.date)
    await choose_date(call, state)


@admin_router.callback_query(F.data.contains('choose_week')
                             | F.data.contains('other_week'))
async def choose_week(call: CallbackQuery, state: FSMContext):
    '''Функция обрабатывает два типа запросов. add_week и remove_week'''
    await call.answer()
    answer = await get_answer_type(call)
    if 'other_week' in call.data:
        q_type = call.data.split()[0]
        add_weeks = int(call.data.split('|')[-1])
    else:
        await state.clear()
        q_type = call.data.split()[0]
        add_weeks = 0
        await state.update_data(action_type=q_type)

    await state.set_state(Form.date)

    if q_type == 'add_week':
        apps = await AsyncORM.get_visits(
            doctor_id=[1, 2], date_from=datetime.now())
    elif q_type == 'remove_week':
        apps = await AsyncORM.get_visits(date_from=datetime.now())

    dates = [app.time for app in apps if app.available_from_admin]
    reply = get_reply(q_type=q_type)
    reply += '\n<b>Выберите неделю:</b>'
    reply += '''
    В зависимости от того, открывается запись или закрывается \
    индикация будет разной. При закрытии записи отображаются \
    все записи всех враче. При открытии только ЛОР врачей
    (в целом можно сделать единую индикацию как в клавиатурах с временем)
    🔴 - ни на одну дату запись не открыта
    🟡 - открыта запись на некоторые даты
    🟢 - открыта запись минимум на 6 дней в неделю
    🟤 - дата уже прошла
    '''.replace('    ', '')
    await answer(text=reply,
                 reply_markup=get_weeks_kb(
                    q_type=q_type,
                    q_back='open_close_date',
                    dates=dates,
                    add_weeks=add_weeks))


@admin_router.callback_query(
    StateFilter(Form.date, Form.time, Form.user_name, Form.user_actions,
                Form.date_from, Form.doctor_id, Form.time_from),
    F.data.contains('choose_time'))
async def choose_time(call: CallbackQuery, state: FSMContext):
    '''Функция возвращает выбор клавиатуры со временем'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]
    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    st = await state.get_state()

    if q_type in ['move_app', 'move_app_ext']:
        if st == Form.date_from.state:
            await state.update_data(date_from=call.data.split('|')[-1])
            await state.set_state(Form.time_from)
        elif st == Form.time.state:
            await state.update_data(time=None)
        elif st == Form.time_from.state:
            await state.update_data(time_from=None, doctor_id=None,
                                    date=None, time=None)
        elif st == Form.doctor_id.state:
            await state.update_data(doctor_id=None,
                                    date=None, time=None)
            await state.set_state(Form.time_from)
        if st == Form.date.state:
            if '|' in call.data:
                await state.update_data(date=call.data.split('|')[-1])
                await state.set_state(Form.time)
            else:
                await state.update_data(time_from=None, doctor_id=None,
                                        date=None, time=None)
                await state.set_state(Form.time_from)
    elif st in [Form.date.state]:
        await state.update_data(date=call.data.split('|')[-1])

    if q_type not in ['move_app', 'move_app_ext']:
        await state.set_state(Form.time)

    st = await state.get_state()
    data = await state.get_data()

    answer = await get_answer_type(call)
    if st == Form.time_from.state:
        day, month, year = [int(i) for i in data['date_from'].split('.')]
    else:
        day, month, year = [int(i) for i in data['date'].split('.')]
    dt = datetime(day=day, month=month, year=year)

    if st == Form.time.state:
        if data['doctor_id'] in [0, 1, 2]:
            doctor_q = [1, 2]
        elif data['doctor_id'] in [3, 4]:
            doctor_q = [3, 4]
        else:
            doctor_q = [5]
    elif st == Form.time_from.state:
        if data['doctor_id_from'] in [0, 1, 2]:
            doctor_q = [1, 2]
        elif data['doctor_id_from'] in [3, 4]:
            doctor_q = [3, 4]
        else:
            doctor_q = [5]

    db_data = await AsyncORM.get_visits(
        date_from=dt, date_to=dt + timedelta(days=1),
        doctor_id=doctor_q)

    if st == Form.time_from.state:
        if data['doctor_id_from'] in [0, 1, 2]:
            step = '30 min'
            time_start = '9:00'
        elif data['doctor_id_from'] in [3, 4]:
            step = '20 min'
            time_start = '9:00'
        else:
            step = '30 min'
            time_start = '9:20'
    else:
        if data['doctor_id'] in [0, 1, 2]:
            step = '30 min'
            time_start = '9:00'
        elif data['doctor_id'] in [3, 4]:
            step = '20 min'
            time_start = '9:00'
        else:
            step = '30 min'
            time_start = '9:20'

    reply = get_reply(q_type=q_type,
                      doctor_id_from=data.get('doctor_id_from'),
                      date_from=data.get('date_from'),
                      time_from=data.get('time_from'),
                      doctor_id=data.get('doctor_id'),
                      date=data.get('date'),
                      user_id=data.get('user_id'),
                      user_name=data.get('user_name'),
                      doctor_true_from=data.get('doctor_true'))

    # здесь же добавить, что это второй этап move_time
    add_dates = []
    if q_type == 'make_app':
        dates = [app.time for app in db_data
                 if app.available_from_user and app.available_from_admin]
    elif ((q_type in ['move_app', 'move_app_ext'])
          and (st == Form.time_from.state)):
        dates = [app.time for app in db_data
                 if app.user_id]
    elif q_type == 'move_app':
        dates = [app.time for app in db_data
                 if app.available_from_admin and app.available_from_user]

        add_dates = await AsyncORM.get_visits_movement(
            time=to_datetime(data['date_from'], data['time_from']),
            doctor_id=data['doctor_id'],
            available_from_admin=True)

        dates += [time for time in add_dates
                  if (time < (dt + timedelta(days=1)))
                  and (time > dt)]
    elif q_type == 'move_app_ext':

        add_dates = await AsyncORM.get_visits_movement(
            time=to_datetime(data['date_from'], data['time_from']),
            doctor_id=data['doctor_id'],
            available_from_admin=False)

        add_dates = [time for time in add_dates
                     if (time < (dt + timedelta(days=1)))
                     and (time > dt)]
    elif q_type == 'remove_app':
        dates = [app.time for app in db_data
                 if app.user_id]

    if (((q_type in ['make_app', 'remove_app', 'move_app'])
         or ((q_type == 'move_app_ext') and (st == Form.time_from.state)))
       and (len(dates) == 0)):
        prev_reply = '<b>Нет временных слотов, соответствующих вашему запросу'
        if q_type == 'make_app':
            prev_reply += ' (всё время занято)'
        elif q_type == 'remove_app':
            prev_reply += ' (на дату никто не записан)'
        prev_reply += '\nВыберите другую дату</b>\n\n'
        await answer(text=prev_reply + reply,
                     reply_markup=get_back_kb(
                         q_back=f'{q_type} choose_date'))

    reply += '\n<b>Выберите время:</b>'

    q_back = q_type + ' choose_date'

    if ((q_type in ['make_app', 'remove_app', 'move_app'])
       or ((q_type == 'move_app_ext') and (st == Form.time_from.state))):
        if ((q_type in ['move_app', 'move_app_ext'])
           and (st == Form.time_from.state)):
            q_type += ' handle_app'
        elif q_type == 'move_app':
            q_type += ' set_app_move'
        else:
            q_type += ' set_time'

        return await answer(
            text=reply,
            reply_markup=get_times_kb_user(
                q_type=q_type,
                q_back=q_back,
                dates=dates,
                doctor_id=data.get('doctor_id',
                                   data.get('doctor_id_from'))))

    if q_type == 'user_actions_app':
        q_type += ' choose_action_with_user'
    elif q_type in ['move_app_ext']:
        q_type += ' set_app_move'
    else:
        q_type += ' set_time'

    reply += '''
    🟤 - время уже прошло
    🟢 - к врачу записан человек
    🟩 - к другому врачу в записан человек
    🟣 - время занято врачем
    🟪 - время занято другим врачем
    ⚫ - время заблокировано по неизвестной причине
    🟡 - время доступно для записи
    🟨 - время доступно для записи к другому врачу и недоступно для текущего
    🔴 - время заблокировано для новой записи администратором \
    (его можно сделать доступным)
    🔵 - время не было добавлено администратором и его можно добавить
    🅰 - пользователя записал администратор
    🅱 - пользователя записал владелец

    Это очень разнообразная индикация, однако записывать человека можно только\
    если горит 🟡. 🟣 говорит о том, что кабинет на это время занят записью\
    выбранного врача (тк приём длится 40 минут), 🟪 говорит, что кабинет занят\
    записью другого врача, который сидит в том же кабинете.
    ⚫ - это то, что вообще никогда не должно появляться. Если он появился, то\
    нужно сказать мне.
    🔴 и 🔵 не могут появиться одновременно
    🟡 и 🟨 не могут появиться одновременно
    🟢 и 🟩 не могут появиться одновременно
    🟢🔴 и 🟢🔵 говорит о том, что если человек отменит свою запись на его\
    место никто не сможет записаться
    Потом могу убрать этот текст
    '''.replace('    ', '')

    await answer(
        text=reply,
        reply_markup=get_times_kb_admin(
            q_type,
            q_back=q_back,
            date=data['date'],
            time_start=time_start,
            time_end='18:00',
            step=step,
            apps=db_data,
            doctor_id=data['doctor_id'],
            add_dates=add_dates
        ))


@admin_router.callback_query(
    F.data.contains('set_time') & (
        F.data.contains('add_time') | F.data.contains('remove_time')
        | F.data.contains('remove_app')),
    Form.time)
async def add_and_remove_time_final(call: CallbackQuery, state: FSMContext):
    '''Функция позволяет добавить время для записи, удалить время для записи
    и удалить запись пользователя. Вызывается два раза. В первый раз после
    выбора даты, возвращая клавиатуру с просьбой подтвердить. Если пользователь
    подтверждает действие вызывается второй раз. Может вызываться более двух
    раз в случае ошибок.
    '''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]
    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    force_codes = []

    if '|' in call.data:
        await state.update_data(time=call.data.split('|')[-1])
    elif '@' in call.data:
        force_codes = [int(i) for i in call.data.split('@')[-1].split(', ')]

    await state.set_state(Form.time)
    answer = await get_answer_type(call)
    data = await state.get_data()
    dt = to_datetime(data['date'], data['time'])

    # этот случай есть только при удалении записи человека
    choosen_doctor = data['doctor_id']
    if data['doctor_id'] == 0:
        db_data = await AsyncORM.get_visits(date_from=dt,
                                            date_to=dt,
                                            doctor_id=[1, 2])
        db_data = [r for r in db_data if r.user_id]
        reply = get_reply(q_type=q_type,
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'),
                          time=data.get('time'))
        if db_data:
            data['doctor_id'] = db_data[0].doctor_id
        else:
            prev_reply = '<b>Ошибка!</b>\n'
            prev_reply += 'На данное время ни у одного из врачей нет записи\n'
            prev_reply += 'Выберите другого врача или другое время\n'
            reply = prev_reply + reply

            return await answer(
                text=reply, reply_markup=get_universal_kb(
                    texts_back=['Назад к выбору времени',
                                'Назад к выбору врача'],
                    qs_back=[f'{q_type} choose_time',
                             f'{q_type} choose_doctor'],
                    tp='main edit'))

    if 'approve' in call.data:

        reply = get_reply(q_type=q_type,
                          doctor_id=choosen_doctor,
                          date=data.get('date'),
                          time=data.get('time'),
                          doctor_true=data.get('doctor_id'))

        if q_type == 'add_time':
            user_id, user_name, status_code = (
                await AsyncORM.make_time_available(
                    doctor_id=data['doctor_id'],
                    time=dt,
                    force_codes=force_codes))
        elif q_type == 'remove_time':
            user_id, user_name, status_code = (
                await AsyncORM.make_time_unavailable(
                    doctor_id=data['doctor_id'],
                    time=dt,
                    force_codes=force_codes))
        elif q_type == 'remove_app':
            user_id, user_name, status_code = (
                await AsyncORM.del_appointment(
                    user_id=call.from_user.id,
                    doctor_id=data['doctor_id'],
                    time=dt,
                    force_codes=force_codes))

        if status_code < 40:
            prev_reply = get_success_messege(
                user_id, user_name, status_code)
            texts_back = ['Выбрать другое время']
            qs_back = [f'{q_type} choose_time rm_mk']
            if q_type == 'remove_app':

                await state.update_data(user_id=user_id, user_name=user_name)
                await state.set_state(Form.time)
                if call.from_user.id in admins:
                    texts_back.append('Перейти на панель пользователя')
                    q = 'user_actions_id choose_action_with_user special rm_mk'
                    reply += '\n<b>Вы можете перейти на панель работы с '
                    reply += 'пользователем и написать ему сообщение</b>'
                    qs_back.append(q)

            await answer(
                text=prev_reply + '\n' + '\n'.join(reply.split('\n')[2:]),
                reply_markup=get_universal_kb(
                    texts_back=texts_back,
                    qs_back=qs_back
                ))
            if q_type == 'remove_app':
                # на этой строчке так странно добавлюется user_id и user_name
                reply = '\n'.join(reply.split('\n')[:-1])
                reply = reply + '\n' + '\n'.join(prev_reply.split('\n')[3:])

                reply += f'\nДействие соврешил: {call.from_user.id}'
                if call.from_user.id in admins:
                    reply += ' (владелец)'
                elif call.from_user.id in registrators:
                    reply += ' (администратор)'

                await call.bot.send_message(chat_id=chat_id, text=reply)
                if data['doctor_id'] == 3:
                    pass
                    # await call.bot.send_message(chat_id=, text=reply)
                log = reply_to_log(reply)
                await AsyncORM.create_log(
                    user_id=call.from_user.id, action_type=q_type,
                    action=log, action_time=datetime.now())
            return None

        elif status_code >= 60:
            prev_reply = await get_critical_messege(
                user_id, user_name, status_code, data)
            return await answer(
                text=prev_reply + '\n' + reply,
                reply_markup=get_universal_kb(
                    texts_back=['Выбрать другое время'],
                    qs_back=[f'{q_type} choose_time rm_mk']
                ))

        else:
            prev_reply = get_warning_message(user_id, user_name, status_code)
            force_codes.append(status_code)
            force_codes = str(force_codes)[1:-1]
            return await answer(
                text=prev_reply + '\n' + reply + '\n<b>Продолжить?</b>',
                reply_markup=get_universal_kb(
                    texts_back=['Да', 'Выбрать другое время'],
                    qs_back=[f'{q_type} set_time approve@{force_codes}',
                             f'{q_type} choose_time rm_mk'],
                    tp='main edit'
                ))

    db_data = await AsyncORM.get_visits(
        date_from=dt, date_to=dt, doctor_id=[data['doctor_id']])

    user_id = db_data[0].user_id if db_data else None
    user_name = db_data[0].user_name if db_data else None

    reply = get_reply(q_type=q_type,
                      doctor_id=choosen_doctor,
                      date=data.get('date'),
                      time=data.get('time'),
                      doctor_true=data.get('doctor_id'),
                      user_id=user_id,
                      user_name=user_name)

    reply += '\n<b>Подтвердить?</b>'
    return await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Подтвердить', 'Назад'],
            qs_back=[f'{q_type} set_time approve',
                     f'{q_type} choose_time'],
            tp='main edit'))


@admin_router.callback_query(
    F.data.contains('set_time') & F.data.contains('make_app'),
    StateFilter(Form.time, Form.user_name))
async def set_user_contact(call: CallbackQuery, state: FSMContext):
    '''Функция вызывается при попытке добавить запись пользователя
    после выбора клавиатуры. Она предлагает ввести контакт клиента
    '''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()

    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)
    await state.set_state(Form.user_name)

    if '|' in call.data:
        await state.update_data(time=call.data.split('|')[-1])

    data = await state.get_data()

    dt = to_datetime(data['date'], data['time'])
    answer = await get_answer_type(call)

    choosen_doctor = data['doctor_id']
    if data['doctor_id'] == 0:
        db_data = await AsyncORM.get_visits(date_from=dt,
                                            date_to=dt,
                                            doctor_id=[1, 2])
        db_data = [r for r in db_data if r.available_from_admin]
        reply = get_reply(q_type=q_type,
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'),
                          time=data.get('time'))
        if db_data:
            data['doctor_id'] = db_data[0].doctor_id
        else:
            prev_reply = '<b>Ошибка!</b>\n'
            prev_reply += 'На данное время ни у одного из врачей нет записи\n'
            prev_reply += 'Выберите другого врача или другое время\n'
            reply = prev_reply + reply

            return await answer(
                text=reply, reply_markup=get_universal_kb(
                    texts_back=['Назад к выбору времени',
                                'Назад к выбору врача'],
                    qs_back=[f'{q_type} choose_time',
                             f'{q_type} choose_doctor'],
                    tp='main edit'))

    reply = get_reply(q_type=q_type,
                      doctor_id=choosen_doctor,
                      date=data.get('date'),
                      time=data.get('time'),
                      doctor_true=data.get('doctor_id'))

    reply += '\n<b>Введите контакт человека</b> (например, телефон и имя) '
    reply += '<u>при помощи текстовой клавиатуры</u> и отправьте сообщение'

    msg = await answer(
        text=reply,
        reply_markup=get_universal_kb(
            ['Назад к выбору времени'], [f'{q_type} choose_time'],
            tp='main edit'))
    await state.update_data(msg_id=msg.message_id)


@admin_router.message(Form.user_name)
async def read_user_contact(message: Message, state: FSMContext):
    '''Функция обрабатывает контакт при попытке записи
    и возвращает клавиатуру с предложением подтвердить действие
    '''
    log = await get_log(message=message, state=state)
    logger.info(log)
    await state.update_data(user_name=message.text)

    data = await state.get_data()
    q_type = data['action_type']

    dt = to_datetime(data['date'], data['time'])
    choosen_doctor = data['doctor_id']
    if data['doctor_id'] == 0:
        db_data = await AsyncORM.get_visits(date_from=dt,
                                            date_to=dt,
                                            doctor_id=[1, 2])
        db_data = [r for r in db_data if r.available_from_admin]
        reply = get_reply(q_type=q_type,
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'),
                          time=data.get('time'),
                          user_id=message.from_user.id,
                          user_name=data.get('user_name'))
        if db_data:
            data['doctor_id'] = db_data[0].doctor_id
        else:
            prev_reply = '<b>Ошибка!</b>\n'
            prev_reply += 'На данное время ни у одного из врачей нет записи\n'
            prev_reply += 'Выберите другого врача или другое время\n'
            reply = prev_reply + reply

            await message.answer(
                text=reply, reply_markup=get_universal_kb(
                    texts_back=['Назад к выбору времени',
                                'Назад к выбору врача'],
                    qs_back=[f'{q_type} choose_time',
                             f'{q_type} choose_doctor'],
                    tp='main edit'))
            return await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=data['msg_id'],
                reply_markup=None)

    reply = get_reply(q_type=q_type,
                      doctor_id=choosen_doctor,
                      date=data.get('date'),
                      time=data.get('time'),
                      doctor_true=data.get('doctor_id'),
                      user_id=message.from_user.id,
                      user_name=data.get('user_name'))

    reply += '\n<b>Подтвердить запись?</b>'

    q_type_approve = f'{q_type} approve_app'
    if q_type == 'make_app':
        q_type_approve += '@46'

    await state.set_state(Form.time)

    await message.answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Подтвердить запись', 'Ввести контакт заново'],
            qs_back=[q_type_approve, f'{q_type} set_time']
        ))

    await message.bot.delete_message(chat_id=message.chat.id,
                                     message_id=data['msg_id'])

    # await message.bot.edit_message_reply_markup(
    #     chat_id=message.chat.id,
    #     message_id=data['msg_id'],
    #     reply_markup=None)


@admin_router.callback_query(
    F.data.contains('approve_app') & F.data.contains('make_app'),
    Form.time)
async def approve_appointment(call: CallbackQuery, state: FSMContext):
    '''Функция записывает человека на приём'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    force_codes = []

    if '@' in call.data:
        force_codes = [int(i) for i in call.data.split('@')[-1].split(', ')]

    data = await state.get_data()
    dt = to_datetime(data['date'], data['time'])
    answer = await get_answer_type(call)

    choosen_doctor = data['doctor_id']
    if data['doctor_id'] == 0:
        db_data = await AsyncORM.get_visits(date_from=dt,
                                            date_to=dt,
                                            doctor_id=[1, 2])
        db_data = [r for r in db_data if r.available_from_admin]
        reply = get_reply(q_type=q_type,
                          doctor_id=data.get('doctor_id'),
                          date=data.get('date'),
                          time=data.get('time'),
                          user_id=call.from_user.id,
                          user_name=data.get('user_name'))
        if db_data:
            data['doctor_id'] = db_data[0].doctor_id
        else:
            prev_reply = '<b>Ошибка!</b>\n'
            prev_reply += 'На данное время ни у одного из врачей нет записи\n'
            prev_reply += 'Выберите другого врача или другое время\n'
            reply = prev_reply + reply

            return await answer(
                text=reply, reply_markup=get_universal_kb(
                    texts_back=['Назад к выбору времени',
                                'Назад к выбору врача'],
                    qs_back=[f'{q_type} choose_time',
                             f'{q_type} choose_doctor'],
                    tp='main edit'))

    reply = get_reply(q_type=q_type,
                      doctor_id=choosen_doctor,
                      date=data.get('date'),
                      time=data.get('time'),
                      doctor_true=data.get('doctor_id'),
                      user_id=call.from_user.id,
                      user_name=data.get('user_name'))

    user_id, user_name, status_code = await (
        AsyncORM.add_new_visit(
            user_id=call.from_user.id,
            doctor_id=data['doctor_id'],
            time=dt,
            user_name=data['user_name'],
            force_codes=force_codes
            )
    )

    if status_code < 40:
        prev_reply = get_success_messege(
            user_id, user_name, status_code)
        await answer(
            text=prev_reply + '\n' + '\n'.join(reply.split('\n')[2:]),
            reply_markup=get_universal_kb(
                texts_back=['Выбрать другое время'],
                qs_back=[f'{q_type} choose_time rm_mk']
            ))

        if data['doctor_id'] == 3:
            # await call.bot.send_message(chat_id=, text=reply)
            pass
        await call.bot.send_message(
            chat_id=chat_id,
            text=reply)
        log = reply_to_log(reply)
        await AsyncORM.create_log(
            user_id=call.from_user.id, action_type=q_type,
            action=log, action_time=datetime.now())

    elif status_code >= 60:
        prev_reply = await get_critical_messege(
            user_id, user_name, status_code, data)
        await answer(
            text=prev_reply + '\n' + reply,
            reply_markup=get_universal_kb(
                texts_back=['Выбрать другое время'],
                qs_back=[f'{q_type} choose_time rm_mk']
            ))

    else:
        prev_reply = get_warning_message(user_id, user_name, status_code)
        force_codes.append(status_code)
        force_codes = str(force_codes)[1:-1]
        await answer(
            text=prev_reply + '\n' + reply + '\n<b>Продолжить?</b>',
            reply_markup=get_universal_kb(
                texts_back=['Да', 'Выбрать другое время'],
                qs_back=[f'{q_type} approve_app@{force_codes}',
                         f'{q_type} choose_time rm_mk'],
                tp='main edit'
            ))


@admin_router.callback_query(
    F.data.contains('add_day') & (F.data.contains('set_day')
                                  | F.data.contains('treatment')
                                  | F.data.contains('approve')
                                  | F.data.contains('change_time_end')
                                  | F.data.contains('change_time_start')),
    Form.date)
async def add_day(call: CallbackQuery, state: FSMContext):
    '''Функция делает день доступным для записи'''
    global day_config
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]
    prev_reply = ''

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    if '|' in call.data:
        fsm_data = call.data.split('|')[-1]
        query_type = call.data.split('|')[0].split()[-1]

        if query_type == 'set_day':
            await state.update_data(date=fsm_data)

        data = await state.get_data()
        dt = to_datetime(data['date'])
        doctor_id = data['doctor_id']

        dt_start = to_datetime(
            data['date'], day_config[doctor_id][dt.weekday()]['time_start'])
        dt_end = to_datetime(
            data['date'], day_config[doctor_id][dt.weekday()]['time_end'])

        if query_type == 'change_time_start':
            if dt_end <= to_datetime(data['date'], fsm_data):
                # prev_reply += '<b>Ошибка!\nДата окончания приёма'
                # prev_reply += ' дожна быть больше даты начала</b>\n'
                prev_reply += '<b>Предупреждение!\nВыбранная дата начала '
                prev_reply += 'приёма больше даты окончания приёма.'
                prev_reply += 'Дата окончания приёма была сдвинута</b>\n'
                day_config[doctor_id][dt.weekday()]['time_start'] = fsm_data
                day_config[doctor_id][dt.weekday()]['time_end'] = fsm_data
            else:
                day_config[doctor_id][dt.weekday()]['time_start'] = fsm_data
        elif query_type == 'change_time_end':
            if to_datetime(data['date'], fsm_data) <= dt_start:
                # prev_reply += '<b>Ошибка!\nДата окончания приёма'
                # prev_reply += ' дожна быть больше даты начала</b>\n'
                prev_reply += '<b>Предупреждение!\nВыбранная дата окончания '
                prev_reply += 'приёма меньше даты начала приёма. '
                prev_reply += 'Дата начала приёма была сдвинута</b>\n'
                day_config[doctor_id][dt.weekday()]['time_start'] = fsm_data
                day_config[doctor_id][dt.weekday()]['time_end'] = fsm_data
            else:
                day_config[doctor_id][dt.weekday()]['time_end'] = fsm_data
        elif query_type == 'treatment':
            tr = not int(fsm_data)
            day_config[doctor_id][dt.weekday()]['treatment'] = tr

        day_config = OmegaConf.create(day_config)
        OmegaConf.save(day_config, "../data/yaml_configs/day_config.yaml")
    else:
        data = await state.get_data()
        dt = to_datetime(data['date'])
        doctor_id = data['doctor_id']

    answer = await get_answer_type(call)

    reply = get_reply(
        q_type=q_type,
        doctor_id=data.get('doctor_id'),
        date=data.get('date'),
        time_start=day_config[doctor_id][dt.weekday()]['time_start'],
        time_end=day_config[doctor_id][dt.weekday()]['time_end'],
        treatment=day_config[doctor_id][dt.weekday()].get('treatment'))

    if 'approve' in call.data:

        tm_start = day_config[doctor_id][dt.weekday()]['time_start']
        tm_end = day_config[doctor_id][dt.weekday()]['time_end']
        add_treatment = day_config[doctor_id][dt.weekday()].get('treatment')
        date = data['date']

        dates = pd.date_range(
            start=to_datetime(date, tm_start),
            end=to_datetime(date, tm_end),
            freq='30 min' if doctor_id in [0, 1, 2, 5] else '40 min',
            inclusive='left')

        tasks = []
        info = []
        for time in dates:
            tasks.append(
                AsyncORM.make_time_available(
                    doctor_id=doctor_id,
                    time=time,
                    force_codes=[46]))
            info.append((time, doctor_id))
            if add_treatment and (doctor_id != 5):
                tasks.append(
                    AsyncORM.make_time_available(
                        doctor_id=5,
                        time=time + timedelta(minutes=20),
                        force_codes=[46]))
                info.append((time + timedelta(minutes=20), 5))

        results = [await task for task in tasks]

        fail_doctor = []
        fail_treatment = []
        count_doctor = 0
        count_treatment = 0
        for (_, _, status_code), (time, doctor) in zip(results, info):
            if doctor != 5:
                if status_code >= 40:
                    fail_doctor.append((time, status_code))
                count_doctor += 1
            else:
                if status_code >= 40:
                    fail_treatment.append((time, status_code))
                count_treatment += 1

        if count_doctor:
            if len(fail_doctor) == 0:
                prev_reply += '<b>Все записи на приём успешно открыты</b>'
            elif len(fail_doctor) == count_doctor:
                prev_reply += '<b>Ни одна запись на приём не была открыта</b>'
            else:
                prev_reply += '<b>Некоторые записи на приём не были открыты'
                prev_reply += '</b>'
            if fail_doctor:
                prev_reply += '\n<b>Даты, которые не были открыты:</b>'
                for time, status_code in fail_doctor:
                    prev_reply += '\nДата: ' + time.strftime('%d.%m.%Y %H:%M')
                    prev_reply += f', Причина: {m_final_short[status_code]}'
            prev_reply += '\n'

        if count_treatment:
            if len(fail_treatment) == 0:
                prev_reply += '<b>Все записи на лечение успешно открыты</b>'
            elif len(fail_treatment) == count_treatment:
                prev_reply += '<b>Ни одна запись на лечение не была открыта'
                prev_reply += '</b>'
            else:
                prev_reply += '<b>Некоторые записи на лечение не были открыты'
                prev_reply += '</b>'
            if fail_treatment:
                prev_reply += '\n<b>Даты, которые не были открыты:</b>'
                for time, status_code in fail_treatment:
                    prev_reply += '\nДата: ' + time.strftime('%d.%m.%Y %H:%M')
                    prev_reply += f', Причина: {m_final_short[status_code]}'
            prev_reply += '\n'

        if (count_doctor == 0) and (count_treatment == 0):
            prev_reply += '<b>В выбраном диапозоне времени не было записей'
            prev_reply += '</b>\n'

        await state.set_state(Form.date)
        return await answer(
            text=prev_reply + '\n'.join(reply.split('\n')[1:]),
            reply_markup=get_universal_kb(['Выбрать другую дату'],
                                          [f'{q_type} choose_date rm_mk']))

    elif (("|" in call.data)
          or ('set_day' in call.data)
          or ('treatment' in call.data)):
        reply += '\n<b>Подтвердить?</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_add_day_kb(
                q_type=q_type,
                q_back=f'{q_type} choose_date',
                treatment=day_config[doctor_id][dt.weekday()].get('treatment'))
            )

    elif 'change_time_start' in call.data:
        reply += '\n<b>Выберите новое время начала приёма</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_simple_times_kb(
                q_type=f'{q_type} change_time_start',
                q_back=f'{q_type} set_day',
                doctor_id=doctor_id)
            )
    elif 'change_time_end' in call.data:
        reply += '\n<b>Выберите новое время окончания приёма</b>'
        await answer(
            text=reply,
            reply_markup=get_simple_times_kb(
                q_type=f'{q_type} change_time_start',
                q_back=f'{q_type} set_day',
                doctor_id=doctor_id)
            )


@admin_router.callback_query(
    F.data.contains('add_week') &
    (F.data.contains('set_week')
     | F.data.contains('treatment')
     | F.data.contains('approve')
     | F.data.contains('change_time_start')
     | F.data.contains('change_time_end')
     | F.data.contains('change_weekend_time_start')
     | F.data.contains('change_weekend_time_end')
     | F.data.contains('ve_days')
     | F.data.contains('weekend_days')
     | F.data.contains('days_without_work')),
    Form.date)
async def add_week(call: CallbackQuery, state: FSMContext):
    '''Функция делает неделю доступной для записи'''
    global week_config
    log = await get_log(call=call, state=state)
    logger.info(log)
    if 'approve' in call.data:
        await call.message.edit_reply_markup(reply_markup=None)

    await call.answer()
    q_type = call.data.split()[0]

    prev_reply = ''
    answer = await get_answer_type(call)

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    if '|' in call.data:
        fsm_data = call.data.split('|')[-1]
        query_type = call.data.split('|')[0].split()[-1]

        if query_type == 'set_week':
            await state.update_data(date=fsm_data)

        data = await state.get_data()

        if query_type == 'change_time_start':
            if (to_datetime(time=week_config['regular_end_time']) <=
               to_datetime(time=fsm_data)):
                # prev_reply += '<b>Ошибка!\nДата окончания приёма'
                # prev_reply += ' дожна быть больше даты начала</b>\n'
                prev_reply += '<b>Предупреждение!\nВыбранная дата начала '
                prev_reply += 'приёма в обычный день больше даты окончания '
                prev_reply += 'приёма. Дата окончания приёма была сдвинута'
                prev_reply += '</b>\n'
                week_config['regular_start_time'] = fsm_data
                week_config['regular_end_time'] = fsm_data
            else:
                week_config['regular_start_time'] = fsm_data

        elif query_type == 'change_time_end':
            if (to_datetime(time=fsm_data) <=
               to_datetime(time=week_config['regular_start_time'])):
                # prev_reply += '<b>Ошибка!\nДата окончания приёма'
                # prev_reply += ' дожна быть больше даты начала</b>\n'
                prev_reply += '<b>Предупреждение!\nВыбранная дата окончания '
                prev_reply += 'приёма в обычный день меньше даты начала приёма'
                prev_reply += '. Дата начала приёма была сдвинута</b>\n'
                week_config['regular_start_time'] = fsm_data
                week_config['regular_end_time'] = fsm_data
            else:
                week_config['regular_end_time'] = fsm_data

        elif query_type == 'change_weekend_time_start':
            if (to_datetime(time=week_config['weekend_end_time']) <=
               to_datetime(time=fsm_data)):
                # prev_reply += '<b>Ошибка!\nДата окончания приёма'
                # prev_reply += ' дожна быть больше даты начала</b>\n'
                prev_reply += '<b>Предупреждение!\nВыбранная дата начала'
                prev_reply += 'приёма в сокращенный день больше даты '
                prev_reply += 'окончания приёма. Дата окончания приёма была '
                prev_reply += 'сдвинута</b>\n'
                week_config['weekend_start_time'] = fsm_data
                week_config['weekend_end_time'] = fsm_data
            else:
                week_config['weekend_start_time'] = fsm_data

        elif query_type == 'change_weekend_time_end':
            if (to_datetime(time=fsm_data) <=
               to_datetime(time=week_config['weekend_start_time'])):
                # prev_reply += '<b>Ошибка!\nДата окончания приёма'
                # prev_reply += ' дожна быть больше даты начала</b>\n'
                prev_reply += '<b>Предупреждение!\nВыбранная дата окончания '
                prev_reply += 'приёма в сокращённый день меньше даты начала '
                prev_reply += 'приёма. Дата начала приёма была сдвинута</b>\n'
                week_config['weekend_start_time'] = fsm_data
                week_config['weekend_end_time'] = fsm_data
            else:
                week_config['weekend_end_time'] = fsm_data

        elif query_type == 'treatment':
            week_config['treatment'] = not int(fsm_data)

        elif query_type in ['ve_days', 'weekend_days', 'days_without_work']:
            if int(fsm_data) in week_config[query_type]:
                week_config[query_type].remove(int(fsm_data))
            else:
                week_config[query_type].append(int(fsm_data))

            if ((query_type != 'days_without_work')
               and (int(fsm_data) in week_config['days_without_work'])):
                week_config['days_without_work'].remove(int(fsm_data))
                prev_reply += '<b>Предупреждение!\nВыбрабнный день находился'
                prev_reply += 'в списке выходных дней. Он был удален из этого'
                prev_reply += 'списка</b>\n'

        day_config = OmegaConf.create(week_config)
        OmegaConf.save(week_config, "../data/yaml_configs/week_config.yaml")

    data = await state.get_data()
    reply = get_reply(q_type=q_type,
                      date=data.get('date'),
                      regular_start_time=week_config.get('regular_start_time'),
                      regular_end_time=week_config.get('regular_end_time'),
                      weekend_start_time=week_config.get('weekend_start_time'),
                      weekend_end_time=week_config.get('weekend_end_time'),
                      treatment=week_config.get('treatment'),
                      ve_days=week_config.get('ve_days'),
                      weekend_days=week_config.get('weekend_days'),
                      days_without_work=week_config.get('days_without_work')
                      )

    if 'approve' in call.data:
        async with ChatActionSender.typing(bot=call.bot,
                                           chat_id=call.message.chat.id):
            week_start_day = to_datetime(data['date'])

            tasks = []
            info = []
            for day_ind in range(7):
                if day_ind in week_config['days_without_work']:
                    continue

                if day_ind in week_config['weekend_days']:
                    time_st = week_config['weekend_start_time']
                    time_end = week_config['weekend_end_time']

                else:
                    time_st = week_config['regular_start_time']
                    time_end = week_config['regular_end_time']

                doctor_id = 1 if day_ind in week_config['ve_days'] else 2
                add_treatment = week_config.get('treatment')

                day = week_start_day + timedelta(days=day_ind)

                dates = pd.date_range(
                    start=to_datetime(day.strftime('%d.%m.%Y'), time_st),
                    end=to_datetime(day.strftime('%d.%m.%Y'), time_end),
                    freq='30 min',
                    inclusive='left')

                for time in dates:
                    tasks.append(
                        AsyncORM.make_time_available(
                            doctor_id=doctor_id,
                            time=time,
                            force_codes=[46]))
                    info.append((time, doctor_id))

                    if add_treatment:
                        tasks.append(
                            AsyncORM.make_time_available(
                                doctor_id=5,
                                time=time + timedelta(minutes=20),
                                force_codes=[46]))
                        info.append((time + timedelta(minutes=20), 5))

            results = [await task for task in tasks]

            fail_doctor = []
            fail_treatment = []
            count_doctor = 0
            count_treatment = 0
            for (_, _, status_code), (time, doctor) in zip(results, info):
                if doctor != 5:
                    if status_code >= 40:
                        fail_doctor.append((time, status_code, doctor))
                    count_doctor += 1
                else:
                    if status_code >= 40:
                        fail_treatment.append((time, status_code, 5))
                    count_treatment += 1

            app_gone = []
            treat_gone = []

            if count_doctor:
                if len(fail_doctor) == 0:
                    prev_reply += '<b>Все записи на приём успешно открыты</b>'
                elif len(fail_doctor) == count_doctor:
                    prev_reply += '<b>Ни одна запись на приём не была открыта'
                    prev_reply += '</b>'
                else:
                    prev_reply += '<b>Некоторые записи на приём не были '
                    prev_reply += 'открыты</b>'
                if fail_doctor:
                    not_40 = len([x for x in fail_doctor if x[1] > 40])
                    if not_40:
                        prev_reply += '\n<b>Даты, которые не были открыты:</b>'
                    for time, status_code, doctor in fail_doctor:
                        if status_code == 40:
                            app_gone.append(time)
                            continue
                        doctor_name = get_doctor_name_by_id(
                            doctor, case="short")
                        time = time.strftime('%d.%m.%Y %H:%M')
                        prev_reply += '\nДата: ' + time
                        prev_reply += f', Врач: {doctor_name}, '
                        prev_reply += f'Причина: {m_final_short[status_code]}'

                    if app_gone:
                        prev_reply += '\nЧисло записей, которые не были '
                        prev_reply += 'открыты из-за того, что время прошло: '
                        prev_reply += f'{len(app_gone)}'

                prev_reply += '\n'

            if count_treatment:
                if len(fail_treatment) == 0:
                    prev_reply += '<b>Все записи на лечение успешно открыты'
                    prev_reply += '</b>'
                elif len(fail_treatment) == count_treatment:
                    prev_reply += '<b>Ни одна запись на лечение не была '
                    prev_reply += 'открыта</b>'
                else:
                    prev_reply += '<b>Некоторые записи на лечение не были '
                    prev_reply += 'открыты</b>'
                if fail_treatment:
                    not_40 = len([x for x in fail_treatment if x[1] > 40])
                    if not_40:
                        prev_reply += '\n<b>Даты, которые не были открыты:</b>'
                    for time, status_code, doctor in fail_treatment:
                        if status_code == 40:
                            treat_gone.append(time)
                            continue
                        time = time.strftime('%d.%m.%Y %H:%M')
                        prev_reply += '\nДата: ' + time + ', '
                        prev_reply += f'Причина: {m_final_short[status_code]}'

                    if app_gone:
                        prev_reply += '\nЧисло записей, которые не были '
                        prev_reply += 'открыты из-за того, что время прошло: '
                        prev_reply += f'{len(treat_gone)}'

                prev_reply += '\n'
            if (count_doctor == 0) and (count_treatment == 0):
                prev_reply += '<b>В выбраном диапозоне времени не было записей'
                prev_reply += '</b>\n'

            prev_reply += '\n'
            await answer(
                text=prev_reply + reply,
                reply_markup=get_universal_kb(['Назад к выбору недели'],
                                              [f'{q_type} choose_week rm_mk'])
            )

    elif (('set_week' in call.data)
          or ('treatment' in call.data)
          or (('|' in call.data)
              and (not (('ve_days' in call.data)
                        or ('weekend_days' in call.data)
                        or ('days_without_work' in call.data))))):

        reply += '\n<b>Подтвердить?</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_add_week_kb(
                q_type=q_type,
                q_back=f'{q_type} choose_week',
                treatment=week_config.get('treatment'))
            )
    elif 'change_time_start' in call.data:
        reply += '\n<b>Выберите новое время начала приёма в будние дни</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_simple_times_kb(
                q_type=f'{q_type} change_time_start',
                q_back=f'{q_type} set_week',
                doctor_id=0)
            )
    elif 'change_time_end' in call.data:
        reply += '\n<b>Выберите новое время окончания приёма в будние дни</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_simple_times_kb(
                q_type=f'{q_type} change_time_end',
                q_back=f'{q_type} set_week',
                doctor_id=0)
            )
    elif 'change_weekend_time_start' in call.data:
        reply += '\n<b>Выберите новое время начала приёма в выходные дни</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_simple_times_kb(
                q_type=f'{q_type} change_weekend_time_start',
                q_back=f'{q_type} set_week',
                doctor_id=0)
            )
    elif 'change_weekend_time_end' in call.data:
        reply += '\n<b>Выберите новое время окончания приёма в выходные дни'
        reply += '</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_simple_times_kb(
                q_type=f'{q_type} change_weekend_time_end',
                q_back=f'{q_type} set_week',
                doctor_id=0)
            )

    elif 've_days' in call.data:
        reply += '\n<b>Выберите дни когда принимает '
        reply += 'Виктор Евгеньевич Лымарев</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_weekdays_kb(
                q_type=f'{q_type} ve_days',
                q_back=f'{q_type} set_week',
                days=week_config['ve_days']
            )
        )
    elif 'weekend_days' in call.data:

        reply += '\n<b>Выберите сокращённые дни</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_weekdays_kb(
                q_type=f'{q_type} weekend_days',
                q_back=f'{q_type} set_week',
                days=week_config['weekend_days']
            )
        )
    elif 'days_without_work' in call.data:
        reply += '\n<b>Выберите дни когда нет приема</b>'
        await answer(
            text=prev_reply + reply,
            reply_markup=get_weekdays_kb(
                q_type=f'{q_type} days_without_work',
                q_back=f'{q_type} set_week',
                days=week_config['days_without_work']
            )
        )


@admin_router.callback_query(F.data.contains('remove_day') &
                             (F.data.contains('set_day')
                              | F.data.contains('approve')),
                             Form.date)
async def remove_day(call: CallbackQuery, state: FSMContext):
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    if '|' in call.data:
        await state.update_data(date=call.data.split('|')[-1])

    data = await state.get_data()
    answer = await get_answer_type(call)

    reply = get_reply(q_type=q_type,
                      date=data.get('date'),
                      doctor_id=data.get('doctor_id'))

    if 'set_day' in call.data:
        if data['doctor_id'] == 5:
            reply += '\nВсе записи на лечение в этот день будут заблокированы'
        elif data['doctor_id'] == 6:
            reply += '\nВсе записи на этот день будут заблокированы'
        else:
            reply += '\nВсе записи к врачу на этот день будут заблокированы'

        reply += '\n<b>Подтвердить?</b>'

        await answer(
            text=reply,
            reply_markup=get_universal_kb(
                ['Подтвердить', 'Назад к выбору даты'],
                [f'{q_type} approve', f'{q_type} choose_date'],
                tp='main edit'))

    elif 'approve' in call.data:

        dt = to_datetime(data['date'])

        if data['doctor_id'] in [1, 2, 3, 4, 5]:
            doctor_q = [data['doctor_id']]
        elif data['doctor_id'] == 0:
            doctor_q = [1, 2]
        else:
            doctor_q = list(range(7))

        db_data = await AsyncORM.get_visits(
            date_from=dt,
            date_to=dt + timedelta(days=1),
            doctor_id=doctor_q)

        info = []
        for app in db_data:
            _, _, code = await AsyncORM.make_time_unavailable(
                doctor_id=app.doctor_id, time=app.time)
            info.append((app.doctor_id, app.time, code))

        fails = sorted([x for x in info if x[-1] > 40], key=lambda x: x[1])

        prev_reply = ''
        if info:
            if len(fails) == 0:
                prev_reply += '<b>Успешно!\n'
                prev_reply += 'Все записи успешно заблокированы</b>\n'
            elif len(fails) == len(info):
                prev_reply += '<b>Ошибка\n'
                prev_reply += 'Ни одна запись не была заблокирована</b>\n'
            else:
                prev_reply += 'Некоторые записи не были заблокированы</b>\n'

            if fails:
                prev_reply += 'Записи, которые не были заблокированы:</b>\n'
                for doctor, time, status_code in fails:
                    doctor_name = get_doctor_name_by_id(doctor, case="short")
                    time = time.strftime('%d.%m.%Y %H:%M')
                    prev_reply += '\nДата: ' + time
                    if doctor != 5:
                        prev_reply += f', Врач: {doctor_name}, '
                    else:
                        prev_reply += f', {doctor_name}, '
                    prev_reply += f'Причина: {m_final_short[status_code]}'
                prev_reply += '\n'

        else:
            prev_reply += '<b>В выбраном диапозоне времени не было записей'
            prev_reply += '</b>\n'

        await answer(
            text=prev_reply + reply,
            reply_markup=get_universal_kb(
                ['Выбрать другую дату'],
                [f'{q_type} choose_date rm_mk'],
                tp='main rm_mk'))


@admin_router.callback_query(F.data.contains('remove_week') &
                             (F.data.contains('set_week')
                              | F.data.contains('approve')),
                             Form.date)
async def remove_week(call: CallbackQuery, state: FSMContext):
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    if '|' in call.data:
        await state.update_data(date=call.data.split('|')[-1])

    data = await state.get_data()
    answer = await get_answer_type(call)
    reply = get_reply(q_type=q_type,
                      date=data.get('date'))

    if 'set_week' in call.data:
        reply += '\nБудут удалены все записи на неделе'
        reply += '\n<b>Подтвердить?</b>'
        await answer(
            text=reply,
            reply_markup=get_universal_kb(
                ['Подтвердить', 'Назад к выбору даты'],
                [f'{q_type} approve', f'{q_type} choose_week'],
                tp='main edit'))

    elif 'approve' in call.data:

        dt = to_datetime(data['date'])
        db_data = await AsyncORM.get_visits(
            date_from=dt,
            date_to=dt + timedelta(days=7),
            doctor_id=list(range(7)))

        info = []
        for app in db_data:
            _, _, code = await AsyncORM.make_time_unavailable(
                doctor_id=app.doctor_id, time=app.time)
            info.append((app.doctor_id, app.time, code))

        fails = sorted([x for x in info if x[-1] > 40], key=lambda x: x[1])

        prev_reply = ''
        if info:
            if len(fails) == 0:
                prev_reply += '<b>Успешно!\n'
                prev_reply += 'Все записи успешно заблокированы</b>\n'
            elif len(fails) == len(info):
                prev_reply += '<b>Ошибка\n'
                prev_reply += 'Ни одна запись не была заблокирована</b>\n'
            else:
                prev_reply += '<b>Некоторые записи не были заблокированы</b>\n'

            if fails:
                prev_reply += '<b>Записи, которые не были заблокированы:</b>\n'
                for doctor, time, status_code in fails:
                    doctor_name = get_doctor_name_by_id(doctor, case="short")
                    time = time.strftime('%d.%m.%Y %H:%M')
                    prev_reply += '\nДата: ' + time
                    if doctor != 5:
                        prev_reply += f', Врач: {doctor_name}, '
                    else:
                        prev_reply += f', {doctor_name}, '
                    prev_reply += f'Причина: {m_final_short[status_code]}'
                prev_reply += '\n'

        else:
            prev_reply += '<b>В выбраном диапозоне времени не было записей'
            prev_reply += '</b>\n'

        await answer(
            text=prev_reply + reply,
            reply_markup=get_universal_kb(
                ['Назад к выбору недели'],
                [f'{q_type} choose_week rm_mk'],
                tp='main rm_mk'))


@admin_router.callback_query(
    F.data.contains('show_date')
)
async def show_appointments(call: CallbackQuery, state: FSMContext):
    '''Функция показывает записи на приём'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]
    answer = await get_answer_type(call)

    if 'today' in call.data:
        reply = '<b>Просмотр записей на сегодня</b> '
        reply += '(или ближайшую дату до сегодняшнего дня, '
        reply += 'если записей на сегодня нет)\n'

        dt = datetime.now()
        dt = to_datetime(dt.strftime('%d.%m.%Y'), '23:59')
        apps = await AsyncORM.get_visits(
            date_from=dt - timedelta(days=20),
            date_to=dt)
        if apps:
            max_date = max([app.time for app in apps]).date()
            apps = [app for app in apps if ((app.time.date() == max_date)
                                            and app.user_id)]
        else:
            return answer(
                text='<b>Нет записией на сегодня</b>\n' + reply,
                reply_markup=get_universal_kb(tp='main edit'))

    elif 'tomorrow' in call.data:
        reply = '<b>Просмотр записей на ближайший день</b>\n'
        dt = datetime.now()
        dt = to_datetime(dt.strftime('%d.%m.%Y')) + timedelta(days=1)
        apps = await AsyncORM.get_visits(
            date_from=dt)
        if len(apps) == 0:
            return answer(
                text=reply + '<b>Нет записией на ближайшее время</b>',
                reply_markup=get_universal_kb(tp='main edit'))

        min_date = min([app.time for app in apps
                        if app.available_from_admin or app.user_id]).date()
        apps = [app for app in apps if (app.time.date() == min_date)]
        if len(apps) == 0:
            return answer(
                text=reply + '<b>Нет записией на достуный для записи день</b>',
                reply_markup=get_universal_kb(tp='main edit'))

    elif '|' in call.data:
        reply = get_reply(q_type=q_type)
        dt = to_datetime(call.data.split("|")[-1])
        apps = await AsyncORM.get_visits(
            date_from=dt, date_to=dt + timedelta(days=1))
        apps = [app for app in apps if app.user_id]

    day_name = get_day_by_index(dt.weekday())
    reply += f'\nДата: <b>{dt.strftime("%d.%m.%Y")} ({day_name})</b>'

    apps = [app for app in apps if app.user_id]

    if len(apps) == 0:
        reply += '\n<b>На данную дату нет записей</b>'
    else:
        dates = [app.time for app in apps]
        user_ids = [app.user_id for app in apps]
        user_names = [app.user_name for app in apps]
        doctor_ids = [app.doctor_id for app in apps]
        sk = [app.skipped for app in apps]

        skips = await AsyncORM.get_visits(user_id=user_ids,
                                          date_to=datetime.now())

        skips = pd.DataFrame({
            'user_id': [app.user_id for app in skips],
            'skipped': [app.skipped for app in skips]
            })

        all_visits = skips.groupby('user_id')['skipped'].count().to_dict()
        skipped_visits = skips.groupby('user_id')['skipped'].sum().to_dict()

        marks = await AsyncORM.get_logs(
            user_ids=user_ids, action_types=['mark'])

        marks = pd.DataFrame({
            'user_id': [note.user_id for note in marks],
            'note': [note.action for note in marks],
            'action_time': [note.action_time for note in marks]}
                             )

        df = pd.DataFrame(
            {'date': dates,
             'user_id': user_ids,
             'user_name': user_names,
             'doctor_id': doctor_ids,
             'skipped': sk
             }).sort_values(['doctor_id', 'date'])

        for doctor_id in sorted(df['doctor_id'].unique()):

            df_small = (
                df.query('doctor_id == @doctor_id').reset_index(drop=True))
            doctor_name = get_doctor_name_by_id(doctor_id)
            if doctor_id != 5:
                reply += f'\n\nВрач: <b>{doctor_name}</b>'
            else:
                reply += f'\n\n<b>{doctor_name}</b>'

            for ind, string in df_small.iterrows():
                user_id = string["user_id"]
                reply += '\n'
                ind += 1
                date = string["date"].strftime("%H:%M")
                reply += f'<b>{ind}. Время: {date}'
                reply += f', id: <code>{user_id}</code> '
                if user_id in admins:
                    reply += '(владелец)'
                elif user_id in registrators:
                    reply += '(администратор)'
                reply += '</b>'
                if pd.notna(string["user_name"]):
                    reply += f'<b>, контакт: {string["user_name"]}</b>'

                sk_v = skipped_visits.get(user_id)
                all_v = all_visits.get(user_id)

                if ((all_v
                     and (call.from_user.id in admins)
                     and (user_id not in admins + registrators))):

                    if sk_v:
                        reply += f' <b>({sk_v}/{all_v})</b>'
                    else:
                        reply += f' ({sk_v}/{all_v})'

                if string['skipped'] and (call.from_user.id in admins):
                    reply += ' <b>(не пришёл)</b>'

                if ((user_id in marks['user_id'].tolist())
                   and (call.from_user.id in admins)
                   and (user_id not in admins)
                   and (user_id not in registrators)):
                    reply += '\n    <i>Пометки:</i>'
                    sample = (marks
                              .query('user_id == @user_id')
                              [['note', 'action_time']]
                              .to_numpy())
                    for i, (m, date) in enumerate(sample, 1):
                        date = date.strftime('%d.%m.%Y')
                        m = m.replace("\n", " ").replace('  ', ' ').strip()

                        reply += f'\n    <i>{i}. {date}, {m}</i>'
    await answer(
        text=reply, reply_markup=get_universal_kb(
            ['Выбрать другую дату'],
            ['show_date'],
            'main edit'
        ))


@admin_router.callback_query(
    F.data == 'user_actions_id set_user_id'
)
async def write_user_id(call: CallbackQuery, state: FSMContext):
    '''Функция простит пользователя ввести id'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]
    await state.update_data(action_type=q_type)
    await state.set_state(Form.user_id)
    answer = await get_answer_type(call)

    reply = get_reply(q_type=q_type)
    reply += '\n<b>Введите id пользователя:</b>'

    msg = await answer(
        text=reply, reply_markup=get_back_kb('admin_kb'))
    await state.update_data(msg_id=msg.message_id)


@admin_router.message(Form.user_id)
async def return_actions_with_user_ms(message: Message,
                                      state: FSMContext):
    '''Функция обрабатывает введёный id пользователя'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    data = await state.get_data()
    user_id = message.text.strip()

    await message.bot.edit_message_reply_markup(
                        chat_id=message.chat.id,
                        message_id=data['msg_id'],
                        reply_markup=None)

    for letter in user_id:
        if letter not in '0123456789':
            reply = '<b>Ошибка!\n'
            reply += 'id пользователя введён некорректно</b>\n'
            reply += get_reply(q_type=data['action_type'], user_id=user_id)
            await state.clear()
            return await message.answer(
                text=reply,
                reply_markup=get_back_kb('user_actions_id set_user_id')
            )

    user_id = int(user_id)
    res = await AsyncORM.get_user(user_id=user_id)
    if res is None:
        reply = '<b>Ошибка!\nДанный пользователь не'
        reply += ' является пользователем бота</b>\n'
        reply += get_reply(q_type=data['action_type'], user_id=user_id)

        return await message.answer(
                text=reply,
                reply_markup=get_back_kb('user_actions_id set_user_id')
            )

    marks = await AsyncORM.get_logs(
        user_ids=[user_id], action_types=['mark'])

    reply = get_reply(q_type=data['action_type'],
                      user_id=user_id,
                      user_name=res.user_name,
                      marks=marks,
                      banned=res.banned)

    reply += '\n<b>Выберите действие:</b>'

    await state.update_data(user_id=user_id, user_name=res.user_name)
    await state.set_state(Form.user_actions)
    await message.answer(text=reply, reply_markup=get_actions_with_user_kb(
        q_type='user_actions_id', visited=None,
        back_text='Ввести другого пользователя',
        back_q='user_actions_id set_user_id',
        banned=res.banned
    ))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('choose_action_with_user'),
    StateFilter(Form.time, Form.user_actions, Form.message,
                Form.mark)
)
async def return_actions_with_user_cb(
    call: CallbackQuery, state: FSMContext
       ):
    '''Функция возвращает клавиатуру с выбором действия с пользователем'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if 'special' in call.data:
        await state.update_data(action_type=q_type)

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)
    if '|' in call.data:
        if 'visited' in call.data:
            v = not bool(int(call.data.split('|')[-1]))
        else:
            await state.update_data(time=call.data.split('|')[-1])

    answer = await get_answer_type(call)
    data = await state.get_data()

    if q_type == 'user_actions_app':
        dt = to_datetime(data['date'], data['time'])
        doctor_q = [data['doctor_id']] if data['doctor_id'] >= 1 else [1, 2]
        if 'visited' in call.data:
            await AsyncORM.change_visited_field(
                time=dt, doctor_id=doctor_q, skipped=v)

        res = await AsyncORM.get_visits(date_from=dt,
                                        date_to=dt,
                                        doctor_id=doctor_q)

        res = [r for r in res if r.user_id]

        if len(res) == 0:
            reply = '<b>Ошибка!\nНа данное время не записан'
            reply += 'ни один пользователь</b>\n'
        elif len(res) >= 2:
            reply = '<b>Ошибка!\nНа данное время записано несколько'
            reply += ' пользователей. Выберите врача точно</b>\n'
        if len(res) != 1:
            reply += get_reply(
                q_type=q_type,
                doctor_id=data.get('doctor_id'),
                date=data.get('date'),
                time=data.get('time'),
                user_id=data.get('user_id'),
                user_name=data.get('user_name'))

            return await answer(
                text=reply,
                reply_markup=get_back_kb(q_type + ' choose_time')
            )
        marks = await AsyncORM.get_logs(
            user_ids=[res[0].user_id], action_types=['mark'])
        banned = (await
                  AsyncORM.get_user(user_id=res[0].user_id)).banned

        reply = get_reply(
            q_type=q_type,
            doctor_id=data.get('doctor_id'),
            date=data.get('date'),
            time=data.get('time'),
            user_id=res[0].user_id,
            user_name=res[0].user_name,
            marks=marks,
            banned=banned,
            visited=not res[0].skipped)

        reply += '\n<b>Выберите действие:</b>'

        await state.update_data(user_id=res[0].user_id,
                                user_name=res[0].user_name)
        await state.set_state(Form.user_actions)
        await answer(
            text=reply,
            reply_markup=get_actions_with_user_kb(
                q_type=q_type, visited=res[0].skipped,
                back_text='Назад к выбору времени',
                back_q=f'{q_type} choose_time',
                banned=banned))

    elif q_type == 'user_actions_id':
        if data.get('user_id') is None:
            return await back_to_main(call, state)

        res = await AsyncORM.get_user(user_id=data['user_id'])
        if res is None:
            await state.clear()
            reply = '<b>Ошибка!\nДанный пользователь не является '
            reply += 'пользователем бота</b>'
            return await answer(
                    text=reply,
                    reply_markup=get_back_kb('user_actions_id set_user_id')
                )
        marks = await AsyncORM.get_logs(
            user_ids=[data['user_id']], action_types=['mark'])

        reply = get_reply(
            q_type=q_type,
            user_id=res.user_id,
            user_name=res.user_name,
            marks=marks)
        reply += '\n<b>Выберите действие:</b>'
        await state.set_state(Form.user_actions)
        await answer(
            text=reply,
            reply_markup=get_actions_with_user_kb(
                q_type='user_actions_id', visited=None,
                back_text='Ввести id другого пользователя',
                back_q='user_actions_id set_user_id',
                banned=res.banned))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('ban_user'),
    Form.user_actions
)
async def ban_or_unban_user(
    call: CallbackQuery, state: FSMContext
       ):
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    answer = await get_answer_type(call)

    if 'approve' in call.data:
        if 'unban_user' in call.data:
            status_code = await AsyncORM.unban_user(user_id=data['user_id'])

        elif 'ban_user' in call.data:
            status_code = await AsyncORM.ban_user(user_id=data['user_id'])

        if status_code < 40:
            reply = get_success_messege(None, None, status_code) + '\n'
        else:
            reply = get_warning_message(None, None, status_code) + '\n'

        reply += get_reply(
            q_type=q_type,
            doctor_id=data.get('doctor_id'),
            date=data.get('date'),
            time=data.get('time'),
            user_id=data.get('user_id'),
            user_name=data.get('user_name'))

        return await answer(
            text=reply,
            reply_markup=get_universal_kb(
                texts_back=['Назад к действиям с пользователем'],
                qs_back=[f'{q_type} choose_action_with_user rm_mk'],
                tp='main rm_mk'
            ))

    reply = get_reply(
        q_type=q_type,
        doctor_id=data.get('doctor_id'),
        date=data.get('date'),
        time=data.get('time'),
        user_id=data.get('user_id'),
        user_name=data.get('user_name'))

    if 'unban_user' in call.data:
        reply += '\n<b>Вы действительно хотите '
        reply += 'разблокировать пользователя?</b>'
    elif 'ban_user' in call.data:
        reply += '\n<b>Вы действительно хотите '
        reply += 'заблокировать пользователя?</b>'
    return await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Да', 'Назад'],
            qs_back=[call.data + ' approve',
                     f'{q_type} choose_action_with_user'],
            tp='main edit'
        ))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & (F.data.contains('write_to_user') | F.data.contains('add_mark')),
    StateFilter(Form.user_actions, Form.message, Form.mark)
)
async def write_to_user_or_add_mark(
    call: CallbackQuery, state: FSMContext
       ):
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    reply = get_reply(
        q_type=q_type,
        doctor_id=data.get('doctor_id'),
        date=data.get('date'),
        time=data.get('time'),
        user_id=data.get('user_id'),
        user_name=data.get('user_name'))

    answer = await get_answer_type(call)
    if 'write_to_user' in call.data:
        await state.set_state(Form.message)
        reply += '\n<b>Напишите сообщение:</b>'

    elif 'add_mark' in call.data:
        await state.set_state(Form.mark)
        reply += '\n<b>Напишите пометку:</b>'
        reply += '\nОна будет появляться при каждом действии c '
        reply += 'пользователем и при просмотре записей'

    msg = await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Назад'],
            qs_back=[f'{q_type} choose_action_with_user'],
            tp='main edit'
        ))
    await state.update_data(msg_id=msg.message_id)


@admin_router.message(StateFilter(Form.message, Form.mark))
async def read_messege_or_mark(message: Message,
                               state: FSMContext):
    log = await get_log(message=message, state=state)
    logger.info(log)
    data = await state.get_data()
    q_type = data['action_type']
    st = await state.get_state()
    reply = get_reply(
        q_type=q_type,
        doctor_id=data.get('doctor_id'),
        date=data.get('date'),
        time=data.get('time'),
        user_id=data.get('user_id'),
        user_name=data.get('user_name'))

    if st == Form.message.state:
        reply += '\n<b>Вы написали следующее сообщение:</b>\n\n'
        reply += message.text + '\n\n'
        reply += '<b>Подтвердить отправку?</b>'
        texts_back = ['Да', 'Ввести другое сообщение',
                      'Вернуться к действиям с пользователем']
        qs_back = [f'{q_type} send_message',
                   f'{q_type} write_to_user',
                   f'{q_type} choose_action_with_user']
        await state.update_data(message=message.text)

    elif st == Form.mark.state:
        reply = '<b>Вы написали следующую пометку:</b>\n\n'
        reply += message.text + '\n\n'
        reply += '<b>Подтвердить?</b>'
        texts_back = ['Да', 'Ввести другое сообщение',
                      'Вернуться к действиям с пользователем']
        qs_back = [f'{q_type} send_mark',
                   f'{q_type} add_mark',
                   f'{q_type} choose_action_with_user']
        await state.update_data(mark=message.text)
    await message.answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=texts_back,
            qs_back=qs_back,
            tp='main edit'))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('send_message'),
    Form.message
)
async def send_message_to_user(
    call: CallbackQuery, state: FSMContext
       ):
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    reply = get_reply(
        q_type=q_type,
        doctor_id=data.get('doctor_id'),
        date=data.get('date'),
        time=data.get('time'),
        user_id=data.get('user_id'),
        user_name=data.get('user_name'))
    answer = await get_answer_type(call)

    try:
        await call.bot.send_message(
            chat_id=data['user_id'],
            text=data['message']
        )
    except Exception:
        prev_reply = '<b>Не удалось отправить сообщение пользователю\n'
        prev_reply += 'Скорее всего потому, что он удалил чат</b>\n'
    else:
        prev_reply = '<b>Сообщение успешно отправлено</b>\n'
        reply += '\n<b>Отправленное сообщение:</b>\n\n'
        reply += data['message']
        await AsyncORM.create_log(user_id=data['user_id'],
                                  action_type='message',
                                  action=str(data['message']),
                                  action_time=datetime.now())

    return await answer(
        text=prev_reply + reply,
        reply_markup=get_universal_kb(
            texts_back=['Назад к действиям с пользователем'],
            qs_back=[f'{q_type} choose_action_with_user rm_mk']
        ))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('send_mark'),
    Form.mark
)
async def send_mark_to_db(
    call: CallbackQuery, state: FSMContext
       ):
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    reply = get_reply(
                q_type=q_type,
                doctor_id=data.get('doctor_id'),
                date=data.get('date'),
                time=data.get('time'),
                user_id=data.get('user_id'),
                user_name=data.get('user_name'))
    answer = await get_answer_type(call)

    try:
        await AsyncORM.create_log(user_id=data['user_id'],
                                  action_type='mark',
                                  action=data['mark'],
                                  action_time=datetime.now())
    except Exception:
        prev_reply = '<b>Не удалось добвить пометку! '
        prev_reply += 'Что-то пошло не так.</b>\n'
    else:
        prev_reply = '<b>Пометка успешно добавлена!</b>\n'

    reply += '\n<b>Пометка:</b>\n\n'
    reply += f'{data['mark']}'

    return await answer(
        text=prev_reply + reply,
        reply_markup=get_universal_kb(
            texts_back=['Назад к действиям с пользователем'],
            qs_back=[f'{q_type} choose_action_with_user rm_mk']
        ))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('ask_feedback'),
    Form.user_actions
)
async def ask_feedback(
    call: CallbackQuery, state: FSMContext
       ):
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    answer = await get_answer_type(call)
    reply = get_reply(
                q_type=q_type,
                doctor_id=data.get('doctor_id'),
                date=data.get('date'),
                time=data.get('time'),
                user_id=data.get('user_id'),
                user_name=data.get('user_name'))

    if 'approve' in call.data:
        with open('../data/text_docs/отзыв.txt', encoding='UTF-8') as f:
            feedback = f.read()
        try:
            await call.bot.send_message(
                chat_id=data['user_id'],
                text=feedback
            )
        except Exception:
            prev_reply = '<b>Не удалось отправить отзыв пользователю\n'
            prev_reply += 'Скорее всего потому, что он удалил чат</b>\n'
        else:
            prev_reply = '<b>Отзыв успешно отправлен</b>\n'
            await answer(
                text=prev_reply + reply,
                reply_markup=get_universal_kb(
                    texts_back=['Вернуться к действиям с пользователем'],
                    qs_back=[f'{q_type} choose_action_with_user rm_mk'],
                    tp='main rm_mk')
                )

            await AsyncORM.create_log(user_id=data['user_id'],
                                      action_type='feedback',
                                      action='',
                                      action_time=datetime.now())

        prev_reply = '<b>Успешно!</b>'
        prev_reply += '\n<b>Сообщение с просьбой об отызве отправлено</b>\n\n'
        return await answer(
            text=prev_reply + reply,
            reply_markup=get_universal_kb(
                texts_back=['Назад к действиям с пользователем'],
                qs_back=[f'{q_type} choose_action_with_user'],
                tp='main edit'
            ))

    reply += '\n<b>Подтвердить отправку сообщения с просьбой об отзыве?</b>'
    await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Да',
                        'Вернуться к действиям с пользователем'],
            qs_back=[f'{q_type} ask_feedback approve',
                     f'{q_type} choose_action_with_user'],
            tp='main edit'))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('show_user_apps'),
    Form.user_actions
)
async def show_user_apps(call: CallbackQuery, state: FSMContext):
    '''Функция выводит на экран все записи пользователя'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    answer = await get_answer_type(call)
    reply = get_reply(
                q_type=q_type,
                doctor_id=data.get('doctor_id'),
                date=data.get('date'),
                time=data.get('time'),
                user_id=data.get('user_id'),
                user_name=data.get('user_name'))

    db_data = await AsyncORM.get_visits(user_id=data['user_id'])
    skipped = len([app for app in db_data if app.skipped])
    active = len([app for app in db_data if app.time > datetime.now()])
    if len(db_data) == 0:
        reply += '\n<b>У челоека нет записей</b>'
    elif len(db_data) > 20:
        reply += f'\nОбщее число записей у человека: <b>{len(db_data)}</b>'
        reply += f'\nЧисло отметок не пришёл: <b>{skipped}</b>'
        reply += f'\nЧисло активных записей: <b>{active}</b>'
        reply += '\n<b>Последние 20 записей человека:</b>'
        db_data = db_data[-20:]
    else:
        reply += f'\nОбщее число записей у человека: <b>{len(db_data)}</b>'
        reply += f'\nЧисло отметок не пришёл: <b>{skipped}</b>'
        reply += f'Число активных записей: <b>{active}</b>'
        reply += '\n<b>Записи человека:</b>'

    for ind, app in enumerate(db_data, 1):
        doctor_name = get_doctor_name_by_id(app.doctor_id, case='short')
        date = app.time.strftime('%d.%m.%Y %H:%M')
        reply += f'\n{ind}. {date} {doctor_name}'
        if app.skipped:
            reply += ' <b>(не пришёл)</b>'

    await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Вернуться к действиям с пользователем'],
            qs_back=[f'{q_type} choose_action_with_user'],
            tp='main edit'))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('show_user_actions'),
    Form.user_actions
)
async def show_user_acitions(call: CallbackQuery, state: FSMContext):
    '''Функция выводит на экран все действия пользователя'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    answer = await get_answer_type(call)
    reply = get_reply(
                q_type=q_type,
                doctor_id=data.get('doctor_id'),
                date=data.get('date'),
                time=data.get('time'),
                user_id=data.get('user_id'),
                user_name=data.get('user_name'))

    db_data = await AsyncORM.get_logs(
        user_ids=[data['user_id']],
        action_types=['make_app', 'move_app', 'remove_app'])

    if len(db_data) == 0:
        reply += '\n<b>Человек не совершал никаких действий</b>'
    else:
        new_apps, moves, removes = 0, 0, 0
        for app in db_data:
            new_apps += app.action_type == 'make_app'
            moves += app.action_type == 'move_app'
            removes += app.action_type == 'remove_app'

        reply += f'\nОбщее число действий у человека: <b>{len(db_data)}</b>'
        reply += f'\nДобавление записи: <b>{new_apps}</b>'
        reply += f'\nПеремещение записи: <b>{moves}</b>'
        reply += f'\nУдаление записи: <b>{removes}</b>\n'

    to_russian = {
        'make_app': 'добавление записи',
        'move_app': 'перемещение записи',
        'remove_app': 'удаление записи'
    }
    if len(db_data) > 7:
        reply += '\n<b>Последние 7 действий человека:</b>'
        db_data = db_data[:7]
    elif (len(db_data) <= 7) and (len(db_data) > 0):
        reply += '\n<b>Действия человека:</b>'

    for ind, app in enumerate(db_data, 1):
        date = app.action_time.strftime('%d.%m.%Y %H:%M')
        reply += f'\n\n<b>{ind}. {date} {to_russian[app.action_type]}</b>'
        reply += ('\n ' + '\n'.join(
            ['    <i>' + string + '</i>'
             for string in app.action.split('\n')]))

    await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Вернуться к действиям с пользователем'],
            qs_back=[f'{q_type} choose_action_with_user'],
            tp='main edit'))


@admin_router.callback_query(
    F.data.contains('user_actions')
    & F.data.contains('del_user_apps'),
    Form.user_actions
)
async def remove_user_apps(call: CallbackQuery, state: FSMContext):
    '''Функция удаляет все записи пользователя'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    data = await state.get_data()
    answer = await get_answer_type(call)
    reply = get_reply(
                q_type=q_type,
                doctor_id=data.get('doctor_id'),
                date=data.get('date'),
                time=data.get('time'),
                user_id=data.get('user_id'),
                user_name=data.get('user_name'))

    db_data = await AsyncORM.get_visits(user_id=data['user_id'],
                                        date_from=datetime.now())
    if len(db_data) == 0:
        prev_reply = '<b>У пользователя нет актуальных записей</b>'
        return await answer(
            text=prev_reply + reply,
            reply_markup=get_universal_kb(
                texts_back=['Назад к действиям с пользователем'],
                qs_back=[f'{q_type} choose_action_with_user'],
                tp='main edit'))

    if 'approve' in call.data:

        reply += '\n<b>Были удалены следующие записи</b>'

        for ind, app in enumerate(db_data):
            await AsyncORM.del_appointment(
                doctor_id=app.doctor_id,
                user_id=app.user_id,
                time=app.time,
                force_codes=[40, 48])
            date = app.time.strftime('%d.%m.%Y %H:%M')
            doctor_name = get_doctor_name_by_id(app.doctor_id, case='short')
            reply += f'\n<b>{ind}.</b> {date}, {doctor_name}'
        return await answer(
            text=reply,
            reply_markup=get_universal_kb(
                texts_back=['Вернуться к действиям с пользователем'],
                qs_back=[f'{q_type} choose_action_with_user rm_mk'],
                tp='main rm_mk'))

    if len(db_data) > 10:
        reply += f'\n<b>Число актуальных записей у человек: {len(db_data)}'
        reply += '\nПоказаны ближайшие 10 записей</b>'

    reply += '\n<b>Записи пользователя:</b>'

    for ind, app in enumerate(db_data[:10], 1):
        date = app.time.strftime('%d.%m.%Y %H:%M')
        doctor_name = get_doctor_name_by_id(app.doctor_id, case='short')
        reply += f'\n<b>{ind}.</b> {date}, {doctor_name}'

    reply += '\n<b>Подтвердить удаление всех записей пользователя?</b>'
    await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Подтвердить удаление',
                        'Вернуться к действиям с пользователем'],
            qs_back=[f'{q_type} del_user_apps approve',
                     f'{q_type} choose_action_with_user'],
            tp='main edit'
            ))


@admin_router.callback_query(F.data.contains('handle_app'),
                             StateFilter(Form.time_from,
                                         Form.doctor_id,
                                         Form.date))
async def handle_app(call: CallbackQuery, state: FSMContext):
    '''
    Функция обрабатывает выбранную запись и в зависимости от этого
    возвращает нужную клавиатуру
    '''
    log = await get_log(call=call, state=state)
    logger.info(log)
    if (await AsyncORM.check_user(call.from_user.id))[0]:
        return None
    await call.answer()
    q_type = call.data.split()[0]

    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    answer = await get_answer_type(call)
    st = await state.get_state()

    if st == Form.time_from.state:
        await state.update_data(time_from=call.data.split('|')[-1])
    else:
        await state.update_data(doctor_id=None, date=None, time=None)

    data = await state.get_data()

    if data['doctor_id_from'] == 0:
        doctor_q = [1, 2]
    elif data['doctor_id_from'] == 6:
        doctor_q = list(range(7))
    else:
        doctor_q = [data['doctor_id_from']]
    dt = to_datetime(data['date_from'], data['time_from'])

    db_data = await AsyncORM.get_visits(
        doctor_id=doctor_q, date_from=dt, date_to=dt)

    db_data = [app for app in db_data if app.user_id]

    if len(db_data) == 0:
        reply = '<b>У на данное время никто не записан</b>\n\n'
        reply += get_reply(q_type=q_type,
                           doctor_id_from=data.get('doctor_id_from'),
                           date_from=data.get('date_from'),
                           time_from=data.get('time_from'))

        return await answer(
            text=reply,
            reply_markup=get_universal_kb(
                texts_back=['Выбрать другое время'],
                qs_back=[f'{q_type} choose_time'],
                tp='main edit'))

    await state.update_data(
        user_id=db_data[0].user_id,
        user_name=db_data[0].user_name,
        doctor_true=db_data[0].doctor_id)

    if db_data[0].doctor_id >= 3:
        await state.update_data(doctor_id=db_data[0].doctor_id)

    reply = get_reply(q_type=q_type,
                      doctor_id_from=data.get('doctor_id_from'),
                      date_from=data.get('date_from'),
                      time_from=data.get('time_from'),
                      user_id=db_data[0].user_id,
                      user_name=db_data[0].user_name,
                      doctor_true_from=db_data[0].doctor_id)

    if db_data[0].doctor_id in [0, 1, 2]:
        reply += '\n<b>Выберите врача для новой записи:</b>'
        await state.set_state(Form.doctor_id)
        return await answer(
            text=reply,
            reply_markup=get_doctors_kb_short(
                q_type=f'{q_type} choose_date',
                q_back=f'{q_type} choose_time',
                doctor_id=db_data[0].doctor_id,
                include_any_lor=(q_type == 'move_app'),
                q_main='main edit'))

    await state.set_state(Form.date)
    await choose_date(call, state)


@admin_router.callback_query(F.data.contains('set_app_move'), Form.time)
async def set_app_move(call: CallbackQuery, state: FSMContext):
    '''
    Функция обрабатывает выбранную запись и в зависимости от этого
    возвращает нужную клавиатуру
    '''
    log = await get_log(call=call, state=state)
    logger.info(log)
    await call.answer()
    q_type = call.data.split()[0]
    if (await state.get_data()).get('action_type') != q_type:
        return await back_to_main(call, state)

    force_codes = []

    if '|' in call.data:
        await state.update_data(time=call.data.split('|')[-1])
    elif '@' in call.data:
        force_codes = [int(i) for i in call.data.split('@')[-1].split(', ')]

    if q_type == 'move_app':
        force_codes.append(46)

    await state.set_state(Form.time)
    answer = await get_answer_type(call)
    data = await state.get_data()

    dt_from = to_datetime(data['date_from'], data['time_from'])
    dt_to = to_datetime(data['date'], data['time'])

    if data['doctor_id_from'] == 0:
        doctor_q_from = [1, 2]
    else:
        doctor_q_from = [data['doctor_id_from']]

    if data['doctor_id'] == 0:
        doctor_q_to = [1, 2]
    else:
        doctor_q_to = [data['doctor_id']]

    db_data_from = await AsyncORM.get_visits(
        date_from=dt_from, date_to=dt_from, doctor_id=doctor_q_from)

    db_data_from = [app for app in db_data_from if app.user_id]

    db_data_to = await AsyncORM.get_visits(
        date_from=dt_to, date_to=dt_to, doctor_id=doctor_q_to)

    doctor_true_to = data['doctor_id']
    if data['doctor_id'] == 0:
        db_data_to = [app for app in db_data_to if app.available_from_admin]
        if len(db_data_to) == 0:
            reply = '<b>Неизвестная ошибка на стороне сервера</b>'
            reply += 'Попробуйте выбрать врача, не используя кнопку "Любой '
            reply += 'ЛОР" при выборе врача\n\n'
            reply += get_reply(q_type=q_type,
                               doctor_id_from=data.get('doctor_id_from'),
                               date_from=data.get('date_from'),
                               time_from=data.get('time_from'),
                               time=data.get('time'),
                               doctor_id=data.get('doctor_id'),
                               date=data.get('date'),
                               user_id=data.get('user_id'),
                               user_name=data.get('user_name'),
                               doctor_true_from=data.get('doctor_true'))
            return await answer(
                text=reply,
                reply_markup=get_universal_kb(
                    texts_back=['Выбрать другое время'],
                    qs_back=[f'{q_type} choose_time']
                ))
        doctor_true_to = db_data_to[0].doctor_id

    if len(db_data_from) == 0:
        reply = '<b>Старая запись не найдена</b>\n'
        reply += 'Возможно они была удалена другим пользователем'
        reply += get_reply(q_type=q_type,
                           doctor_id_from=data.get('doctor_id_from'),
                           date_from=data.get('date_from'),
                           time_from=data.get('time_from'),
                           time=data.get('time'),
                           doctor_id=data.get('doctor_id'),
                           date=data.get('date'),
                           user_id=data.get('user_id'),
                           user_name=data.get('user_name'),
                           doctor_true_from=data.get('doctor_true'))
        return await answer(
                text=reply,
                reply_markup=get_universal_kb(tp='main rm_mk'))

    true_doctor_from = data['doctor_id_from']
    if data['doctor_id_from'] == 0:
        true_doctor_from = db_data_from[0].doctor_id

    reply = get_reply(q_type=q_type,
                      doctor_id_from=data.get('doctor_id_from'),
                      date_from=data.get('date_from'),
                      time_from=data.get('time_from'),
                      time=data.get('time'),
                      doctor_id=data.get('doctor_id'),
                      date=data.get('date'),
                      user_id=db_data_from[0].user_id,
                      user_name=db_data_from[0].user_name,
                      doctor_true_from=true_doctor_from,
                      doctor_true=doctor_true_to)

    if 'approve' in call.data:
        user_id, user_name, status_code = await AsyncORM.move_visit_time(
            call.from_user.id,
            doctor_id_from=true_doctor_from,
            doctor_id_to=doctor_true_to,
            time_from=dt_from,
            time_to=dt_to,
            force_codes=force_codes)

        if status_code < 40:
            prev_reply = get_success_messege(
                user_id, user_name, status_code)
            await answer(
                text=prev_reply + '\n' + '\n'.join(reply.split('\n')[2:]),
                reply_markup=get_universal_kb())

            reply = '\n'.join(reply.split('\n')[:-1])
            reply = reply + '\n' + '\n'.join(prev_reply.split('\n')[3:])
            reply += f'\nДействие соврешил: {call.from_user.id}'
            if call.from_user.id in admins:
                reply += ' (владелец)'
            elif call.from_user.id in registrators:
                reply += ' (администратор)'

            await call.bot.send_message(chat_id=chat_id, text=reply)
            if data['doctor_id'] == 3:
                pass
                # await call.bot.send_message(chat_id=, text=reply)
            log = reply_to_log(reply)
            return await AsyncORM.create_log(
                user_id=call.from_user.id, action_type=q_type,
                action=log, action_time=datetime.now())

        elif status_code >= 60:
            prev_reply = await get_critical_messege(
                user_id, user_name, status_code, data)
            return await answer(
                text=prev_reply + '\n' + reply,
                reply_markup=get_universal_kb(
                    texts_back=['Выбрать другое время'],
                    qs_back=[f'{q_type} choose_time rm_mk']
                ))
        else:
            prev_reply = get_warning_message(user_id, user_name, status_code)
            force_codes.append(status_code)
            force_codes = str(force_codes)[1:-1]
            return await answer(
                text=prev_reply + '\n' + reply + '\n<b>Продолжить?</b>',
                reply_markup=get_universal_kb(
                    texts_back=['Да', 'Выбрать другое время'],
                    qs_back=[f'{q_type} set_app_move approve@{force_codes}',
                             f'{q_type} choose_time rm_mk'],
                    tp='main rm_mk'
                ))

    reply += '\n<b>Подтвердить?</b>'
    return await answer(
        text=reply,
        reply_markup=get_universal_kb(
            texts_back=['Подтвердить', 'Назад'],
            qs_back=[f'{q_type} set_app_move approve',
                     f'{q_type} choose_time'],
            tp='main edit'))


@admin_router.callback_query(F.data.contains('get_data'))
async def get_data(call: CallbackQuery):
    log = await get_log(call=call, state=state)
    logger.info(log)
    if call.data == 'get_data':
        await call.message.edit_text(
            text='Выберите данные, которые хотите скачать',
            reply_markup=get_data_kb())

    if 'apps' in call.data:
        apps = await AsyncORM.get_visits()
        doc = generate_appointments_excel(apps)
        await call.message.answer_document(doc)
    elif 'logs' in call.data:
        logs = await AsyncORM.get_logs()
        doc = generate_logs_excel(logs)
        await call.message.answer_document(doc)
    elif 'users' in call.data:
        users = await AsyncORM.get_users()
        doc = generate_users_excel(users)
        await call.message.answer_document(doc)
