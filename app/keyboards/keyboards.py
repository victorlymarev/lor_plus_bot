from aiogram.types import InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton as IKB
from datetime import datetime, timedelta
import pandas as pd
from create_bot import admins, registrators
from collections import defaultdict
from utils.utils import (get_dates_by_month_year,
                         get_date_inds,
                         get_day_by_index,
                         to_datetime)


def get_main_admin_kb(add_admin_button: bool = False):
    '''Функция возвращает главную клавиатуру для администратора
    add_admin_button - добавляет кнопку панель администратора
    '''

    buttons = [
        [IKB(text='Записать на прием',
             callback_data='make_app choose_doctor')],
        [IKB(text='Удалить запись',
             callback_data='remove_app choose_doctor')],
        [IKB(text='Перенести запись',
             callback_data='move_app choose_doctor')],
        [IKB(text='Посмотреть записи на сегодня',
             callback_data='show_date today'
             )],
        [IKB(text='Посмотреть записи на следующий день',
             callback_data='show_date tomorrow')],
        [IKB(text='Посмотреть записи на дату',
             callback_data='show_date')]
    ]
    if add_admin_button:
        buttons.append([IKB(text='Панель администратора',
                            callback_data='admin_kb')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_kb():
    '''Функция возвращает дополнительную клавиатуру для администратора'''
    buttons = [
        [IKB(text='Записать на прием (на любую дату)',
             callback_data='make_app_force choose_doctor')],
        [IKB(text='Перенести запись (на любую дату)',
             callback_data='move_app_ext choose_doctor')],
        [IKB(text='Открыть/закрыть время для записи',
             callback_data='open_close_date')],
        [IKB(text='Действия с пользователем (по записи)',
             callback_data='user_actions_app choose_doctor')],
        [IKB(text='Действия с пользователем (по id)',
             callback_data='user_actions_id set_user_id')],
        [IKB(text='Получить данные', callback_data='get_data')],
        [IKB(text='На главную',
             callback_data='main edit')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_open_close_kb():
    '''Добавляет кнопки с открытием/закрытием времени'''
    buttons = [
        [IKB(text='Открыть запись на время',
             callback_data='add_time choose_doctor')],
        [IKB(text='Открыть запись на день',
             callback_data='add_day choose_doctor')],
        [IKB(text='Открыть запись на неделю',
             callback_data='add_week choose_week')],
        [IKB(text='Закрыть запись на время',
             callback_data='remove_time choose_doctor')],
        [IKB(text='Закрыть запись на день',
             callback_data='remove_day choose_doctor')],
        [IKB(text='Закрыть запись на неделю',
             callback_data='remove_week choose_week')],
        [IKB(text='Назад', callback_data='admin_kb')],
        [IKB(text='На главную', callback_data='main edit')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_data_kb():
    '''Возвращает кнопки с выбором данных'''
    buttons = [
        [IKB(text='Записи',
             callback_data='get_data apps')],
        [IKB(text='Действия',
             callback_data='get_data logs')],
        [IKB(text='Пользователи',
             callback_data='get_data users')],
        [IKB(text='Назад', callback_data='admin_kb')],
        [IKB(text='На главную', callback_data='main edit')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_doctors_kb(q_type: str,
                   q_back: str = None,
                   text_back: str = 'Назад',
                   show_doctors=True,
                   show_treatment: bool = False,
                   show_any_lor: bool = False,
                   show_all_actions=False,
                   q_main='main edit'):
    '''Функция возвращает клавиатуру с выбором врача
    '''

    buttons = []
    if show_doctors:
        if show_any_lor:
            buttons.append([IKB(text='ЛОР (любой)',
                                callback_data=f'{q_type}|0')])
        buttons += [
            [IKB(text='Александр Викторович Лымарев (ЛОР)',
                 callback_data=f'{q_type}|2')],
            [IKB(text='Виктор Евгеньевич Лымарев (ЛОР)',
                 callback_data=f'{q_type}|1')],
            [IKB(text='Евгения Викторовна Лымарева (невролог детский)',
                 callback_data=f'{q_type}|3')],
            [IKB(text='Мария Любомировна Лымарева (каридиолог)',
                 callback_data=f'{q_type}|4')]
        ]
    if show_treatment:
        buttons.append([IKB(text='Запись на лечение',
                            callback_data=f'{q_type}|5')])
    if show_all_actions:
        buttons.append([IKB(text='Все врачи и записи',
                            callback_data=f'{q_type}|6')])

    if q_back is not None:
        buttons.append([IKB(text=text_back, callback_data=q_back)])

    buttons.append([IKB(text='На главную', callback_data=q_main)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_doctors_kb_short(q_type: str,
                         q_back: str = None,
                         doctor_id: int = None,
                         include_any_lor: bool = False,
                         q_main: str = 'get_user_main_kb edit'):
    '''Функция возвращает клавиатуру с выбором врача'''

    d1 = 'Виктор Евгеньевич Л.'
    d2 = 'Александр Викторович Л.'

    if doctor_id == 1:
        d1 += ' (выбран сейчас)'
    elif doctor_id == 2:
        d2 += ' (выбран сейчас)'

    buttons = []
    if include_any_lor:
        buttons.append([IKB(text='ЛОР (любой)',
                            callback_data=f'{q_type}|0')])

    buttons += [
        [IKB(text=d1,
             callback_data=f'{q_type}|1')],
        [IKB(text=d2,
             callback_data=f'{q_type}|2')],
    ]
    if q_back is not None:
        buttons.append([IKB(text='Назад', callback_data=q_back)])

    buttons.append([IKB(text='На главную', callback_data=q_main)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dates_kb(q_type: str,
                 q_back: str,
                 month: int,
                 year: int,
                 dates: dict = None,
                 include_sunday: bool = False,
                 main_query: str = 'main edit'
                 ):

    '''Функция возвращает клавиатуру с выбором даты'''

    if dates:
        curren_month = dates[(month, year)]
        dates = curren_month['av_dates']
        next_month, next_year = curren_month['next']
        prev_month, prev_year = curren_month['prev']
        include_sunday = False
        for date in dates:
            if date.weekday() == 6:
                include_sunday = True
                break

    else:
        dates, (next_month, next_year), (prev_month, prev_year) = (
            get_dates_by_month_year(month=month,
                                    year=year,
                                    include_sunday=include_sunday)
        )

    dates, inds = get_date_inds(dates, include_sunday=include_sunday)

    RUSSIAN_MONTHS = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    month_name = RUSSIAN_MONTHS[dates[0].month]
    buttons = []
    buttons.append(
        [IKB(text='⬅' if prev_year is not None else ' ',
             callback_data=(f'{q_type} other_month|{prev_month} {prev_year}'
                            if prev_year is not None else 'placeholder')),

         IKB(text=f'{month_name} {dates[0].year}',
             callback_data='placeholder'),

         IKB(text='➡' if next_year is not None else ' ',
             callback_data=(f'{q_type} other_month|{next_month} {next_year}'
                            if next_year is not None else 'placeholder'))])

    wk_days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
    if include_sunday:
        wk_days.append('Вс')

    buttons.append([IKB(text=i, callback_data='placeholder') for i in wk_days])

    weeks = []
    for i, (date, ind) in enumerate(zip(dates, inds)):
        # добавляем в начало пустые кнопки если первое число не пн
        if (i == 0) and date.weekday():
            for i in range(date.weekday()):
                weeks.append(IKB(text=' ', callback_data='placeholder'))
        if ind:
            weeks.append(IKB(
                text=f'{date.day}',
                callback_data=f'{q_type} |{date.strftime("%d.%m.%Y")}'))
        else:
            weeks.append(IKB(
                text=' ',
                callback_data='placeholder'))

        if len(weeks) == (6 + include_sunday):
            buttons.append(weeks)
            weeks = []

    # добавляем в конец пустые кнопки если последнее число месяца не вс
    if (len(weeks) < (6 + include_sunday)) and (len(weeks) > 0):
        for _ in range(6 + include_sunday - len(weeks)):
            weeks.append(IKB(text=' ', callback_data='placeholder'))
        buttons.append(weeks)

    if q_back:
        buttons.append([IKB(text='Назад', callback_data=q_back)])

    buttons.append([IKB(text='На главную', callback_data=main_query)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_dates_kb_short(q_type, dates, q_back: str = None, add_days=0,
                       days_per_kb=6, main_query='main edit'):
    '''Функция возвращает клавиатуру с выбором дат,
    которые уже доступны для записи
    '''
    dates = (pd.Series(dates)
             .astype('datetime64[ns]')
             .dt.normalize()
             .drop_duplicates()
             .rename('date')
             .sort_values()
             .tolist())

    if add_days < 0:
        add_days = 0

    dates_for_iteration = dates[add_days: add_days + days_per_kb]
    prev_days_ln = len(dates[:add_days])
    next_days_ln = len(dates[add_days + days_per_kb:])

    buttons = []
    for date in dates_for_iteration:
        weekday = get_day_by_index(date.weekday(), short=True)
        buttons.append([IKB(
            text=f'{date.strftime("%d.%m.%Y")} ({weekday})',
            callback_data=f'{q_type}|{date.strftime("%d.%m.%Y")}')])

    if prev_days_ln or next_days_ln:
        buttons.append(
            [IKB(text='⬅' if prev_days_ln else ' ',
                 callback_data=f'{q_type} other_dates|{add_days - days_per_kb}'
                 if prev_days_ln else 'placeholder'),
             IKB(text='➡' if next_days_ln else ' ',
                 callback_data=f'{q_type} other_dates|{add_days + days_per_kb}'
                 if next_days_ln else 'placeholder')]
        )
    if q_back:
        buttons.append([IKB(text='Назад', callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data=main_query)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_weeks_kb(q_type, q_back, dates, add_weeks=0, weeks_per_kb=7):
    '''Возвращает клавиатуру с выбором недели для записи'''

    current_date = pd.Timestamp(datetime.now()).normalize()
    current_date = current_date + timedelta(days=7 - current_date.weekday())
    start_date = current_date + timedelta(weeks=add_weeks)

    dates = (pd.Series(dates)
             .astype('datetime64[ns]')
             .dt.normalize()
             .drop_duplicates()
             .rename('date')
             .sort_values()
             .to_frame()
             )

    buttons = []

    for i in range(weeks_per_kb):
        w_st = start_date + timedelta(days=7 * i)
        w_end = start_date + timedelta(days=7 * i + 7)
        w_end
        w_st_text = w_st.strftime('%d.%m.%Y')
        w_end_text = ((start_date +
                       timedelta(days=7 * i + 6))
                      .strftime('%d.%m.%Y'))
        ln = len(dates.query('date >= @w_st').query('date < @w_end'))

        # 🟤 - дата уже прошла
        # 🔴 - ни на одну дату запись не открыта
        # 🟡 - открыта запись на некоторые даты
        # 🟢 - открыта запись на все даты
        sign = ''
        if w_st < current_date:
            sign += '🟤'
        if ln == 0:
            sign += '🔴'
        elif (ln < 6) and (ln > 0):
            sign += '🟡'
        else:
            sign += '🟢'

        buttons.append([
            IKB(text=f'{w_st_text} - {w_end_text} {sign}',
                callback_data=f'{q_type} set_week|{w_st_text}')
        ])
    pr_w = f'{q_type} choose_week other_week |{add_weeks - weeks_per_kb}'
    nt_w = f'{q_type} choose_week other_week |{add_weeks + weeks_per_kb}'
    buttons.append(
        [IKB(text='⬅', callback_data=pr_w),
         IKB(text='➡', callback_data=nt_w)]
    )
    buttons.append([IKB(text='Назад', callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data='main edit')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_simple_times_kb(q_type, q_back, doctor_id, q_main='main edit'):
    '''Возвращает клавиатуру со временем без фильтрации по датам'''
    buttons = []
    for hour in range(9, 20):
        if doctor_id in [0, 1, 2]:
            buttons.append([
                IKB(text=f"{hour}:00", callback_data=f'{q_type}|{hour}:00'),
                IKB(text=f"{hour}:30", callback_data=f'{q_type}|{hour}:30')
            ])
        elif doctor_id in [5]:
            buttons.append([
                IKB(text=f"{hour}:20", callback_data=f'{q_type}|{hour}:20'),
                IKB(text=f"{hour}:50", callback_data=f'{q_type}|{hour}:50')
            ])
        elif doctor_id in [3, 4]:
            buttons.append([
                IKB(text=f"{hour}:00", callback_data=f'{q_type}|{hour}:00'),
                IKB(text=f"{hour}:20", callback_data=f'{q_type}|{hour}:20'),
                IKB(text=f"{hour}:40", callback_data=f'{q_type}|{hour}:40')
            ])
    if q_back is not None:
        buttons.append([IKB(text='Назад', callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data=q_main)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_times_kb_admin(q_type,
                       q_back,
                       date,
                       time_start,
                       time_end,
                       step,
                       apps,
                       doctor_id,
                       add_dates):
    '''Возвращает клавиатуру со временем с красивой анимацией'''
    date_range = pd.date_range(to_datetime(date, time_start),
                               to_datetime(date, time_end),
                               freq=step,
                               inclusive='left')
    current_time = datetime.now()
    n_cols = 3 if step == '20 min' else 2 if step == '30 min' else 1

    buttons = []
    row = []
    # 🟤 - время уже прошло
    # 🟢 - к врачу записан человек
    # 🟩 - к другому врачу в записан человек
    # 🟣 - время занято врачем
    # 🟪 - время занято другим врачем
    # 🟡 - время доступно для записи
    # 🟨 - время доступно для записи к другому врачу и недоступно для текущего
    # 🔴 - время заблокировано администратором
    # 🔵 - время не было добавлено администратором
    # 🅰 - пользователя записал администратор
    # 🅱 - пользователя записал владелец

    if doctor_id == 0:
        taken_dates = [app.time for app in apps if app.user_id]
        available_dates = [app.time for app in apps
                           if (app.available_from_user
                               and app.available_from_admin)]
        blocked_dates = defaultdict(list)
        for app in apps:
            blocked_dates[app.time].append(not app.available_from_admin)
        blocked_dates = [
            time for time, blocked_list in blocked_dates.items()
            if all(blocked_list)]
        all_dates = [app.time for app in apps]

    else:
        taken_dates = [
            app.time for app in apps if app.user_id
            and (app.doctor_id == doctor_id)]
        taken_dates_other = [
            app.time for app in apps
            if app.user_id and (app.doctor_id != doctor_id)]

        dates_user_blocked = [
            app.time for app in apps if ((app.user_id is None)
                                         and (app.doctor_id == doctor_id)
                                         and (not app.available_from_user))]
        available_dates = [
            app.time for app in apps if (app.available_from_user
                                         and app.available_from_admin
                                         and (app.doctor_id == doctor_id))]
        available_dates_other = [
            app.time for app in apps if app.available_from_user
            and app.available_from_admin and (app.doctor_id != doctor_id)]
        blocked_dates = [
            app.time for app in apps if (not app.available_from_admin)
            and (app.doctor_id == doctor_id)]

        all_dates = [
            app.time for app in apps if (app.doctor_id == doctor_id)
        ]

        all_dates_other = [
            app.time for app in apps if ((app.doctor_id != doctor_id)
                                         and (app.available_from_admin
                                              or app.user_id))
        ]

    admin_dates = [app.time for app in apps if app.user_id in admins]
    reg_dates = [app.time for app in apps if app.user_id in registrators]

    for index, time in enumerate(date_range):
        str_time = time.strftime('%H:%M').lstrip('0') + ' '
        str_time_b = time.strftime('%H:%M').lstrip('0')
        time_min_20 = time - timedelta(minutes=20)
        time_plus_20 = time + timedelta(minutes=20)
        if (index == 0) and (time.minute == 50):
            row.append(IKB(text=' ', callback_data='placeholder'))
        if doctor_id == 0:
            if time in taken_dates:
                str_time += '🟢'
            if (time in available_dates) or (time in add_dates):
                str_time += '🟡'
            if time in blocked_dates:
                str_time += '🔴'
            elif time not in all_dates:
                str_time += '🔵'
        else:
            if time in taken_dates:
                str_time += '🟢'
            if time in taken_dates_other:
                str_time += '🟩'
            if (time_min_20 in taken_dates) or (time_plus_20 in taken_dates):
                str_time += '🟣'
            if ((time_min_20 in taken_dates_other)
               or (time_plus_20 in taken_dates_other)):
                str_time += '🟪'

            elif ((not ((time_min_20 not in taken_dates)
                   or (time_plus_20 not in taken_dates)))
                  and (time in dates_user_blocked)):
                # этого по идее не должно быть
                str_time += '⚫'
            if ((time in available_dates) or (time in add_dates)):
                str_time += '🟡'
            elif ((time in available_dates_other)
                  and (not ((time_min_20 in taken_dates)
                            or (time_plus_20 in taken_dates)))
                  and (time not in taken_dates)):
                str_time += '🟨'
            if time in blocked_dates:
                str_time += '🔴'
            elif (time not in all_dates):
                if not ((doctor_id in [1, 2]) and (time in all_dates_other)):
                    str_time += '🔵'

        if time < current_time:
            str_time += '🟤'
        if time in admin_dates:
            str_time += '🅱'
        elif time in reg_dates:
            str_time += '🅰'

        if len(row) < n_cols:
            row.append(IKB(
                text=str_time,
                callback_data=f'{q_type}|{str_time_b}'))
        if len(row) == n_cols:
            buttons.append(row)
            row = []

    if (len(row) < n_cols) and (len(row) > 0):
        for _ in range(n_cols - len(row)):
            row.append(IKB(text=' ', callback_data='placeholder'))
        buttons.append(row)

    buttons.append([IKB(text='Назад', callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data='main edit')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_times_kb_user(q_type, q_back, dates, doctor_id, q_main='main edit'):
    '''Возвращает клавиатуру с доступным временем'''
    dates = pd.Series(dates).astype('datetime64[ns]').sort_values().tolist()
    buttons = []
    row = []
    prev_hour = -1

    for time in dates:
        str_time = time.strftime('%H:%M').lstrip('0')
        hour = time.hour

        if doctor_id in [3, 4]:
            buttons.append([IKB(text=str_time,
                                callback_data=f'{q_type}|{str_time}')])
        else:
            if not row:
                if time.minute >= 30:
                    row.append(IKB(text=' ', callback_data='placeholder'))
                    row.append(IKB(text=str_time,
                                   callback_data=f'{q_type}|{str_time}'))
                    buttons.append(row)
                    row = []
                else:
                    row.append(IKB(text=str_time,
                                   callback_data=f'{q_type}|{str_time}'))
                    prev_hour = hour
            else:
                if hour == prev_hour:
                    # Тот же час - добавляем во второй столбец
                    row.append(IKB(text=str_time,
                                   callback_data=f'{q_type}|{str_time}'))
                    buttons.append(row)
                    row = []
                else:
                    # Новый час - завершаем предыдущий ряд и начинаем новый
                    if len(row) == 1:
                        row.append(IKB(text=' ', callback_data='placeholder'))
                    buttons.append(row)
                    row = [IKB(text=str_time,
                               callback_data=f'{q_type}|{str_time}')]
                    prev_hour = hour

    # Добавляем последний ряд если он остался
    if row:
        if len(row) == 1 and doctor_id not in [3, 4]:
            row.append(IKB(text=' ', callback_data='placeholder'))
        buttons.append(row)

    # Добавляем кнопки навигации
    if q_back is not None:
        buttons.append([IKB(text='Назад', callback_data=q_back)])
    if q_main is not None:
        buttons.append([IKB(text='На главную', callback_data=q_main)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_kb(q_back, q_main='main edit'):
    '''Клавиатура с кнопкой назад'''
    buttons = []
    if q_back is not None:
        buttons.append([IKB(text='Назад', callback_data=q_back)])

    buttons.append([IKB(text='На главную', callback_data=q_main)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_universal_kb(texts_back=None, qs_back=None, tp='main rm_mk'):
    '''
    Штука, которая позволяет быстро конструировать простые клавиатуры
    '''
    buttons = []
    if texts_back is not None:
        for text_back, q_back in zip(texts_back, qs_back):
            buttons.append([IKB(text=text_back, callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data=tp)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_main_kb(q_main='main rm_mk'):
    '''Клавиатура возвращает на главное меню'''
    buttons = [[IKB(text='На главную', callback_data=q_main)]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_actions_with_user_kb(q_type,
                             visited=False,
                             back_text=None,
                             back_q=None,
                             banned=False):
    '''Клавиатура с действиями пользователя'''
    buttons = [
        [IKB(text='Попросить оставить отзыв',
             callback_data=f'{q_type} ask_feedback')],
        [IKB(text='Написать собщение',
             callback_data=f'{q_type} write_to_user')],
        [IKB(text='Добавить пометку',
             callback_data=f'{q_type} add_mark')],
        ]
    if visited is not None:
        cb = f'{q_type} choose_action_with_user visited|{int(visited)}'
        buttons.append(
            [IKB(text=f"Изменить статус на: {'' if visited else 'не '}пришёл",
             callback_data=cb)])
    buttons += [
        [IKB(text='Посмотреть записи пользователя',
             callback_data=f'{q_type} show_user_apps')],
        [IKB(text='Посмотреть действия пользователя',
             callback_data=f'{q_type} show_user_actions')],
        [IKB(text='Удалить все записи пользователя',
             callback_data=f'{q_type} del_user_apps')],
    ]
    if banned:
        buttons.append([IKB(text='Разблокировать пользователя',
                            callback_data=f'{q_type} unban_user')])
    else:
        buttons.append([IKB(text='Заблокировать пользователя',
                            callback_data=f'{q_type} ban_user')])

    if back_q:
        buttons.append([IKB(text=back_text, callback_data=back_q)])
    buttons.append([IKB(text='На главную', callback_data='main edit')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_add_day_kb(q_type, q_back, treatment):
    '''Клавиатура с выбором для добавления дня для записи'''
    buttons = [
        [IKB(text='Подтвердить', callback_data=f'{q_type} approve')],
        [IKB(text='Изменить время начала приема',
             callback_data=f'{q_type} change_time_start')],
        [IKB(text='Изменить время окончания приема',
             callback_data=f'{q_type} change_time_end')]
    ]
    if treatment is not None:
        x = 'да' if treatment else 'нет'
        buttons.append([IKB(
            text='Добавить запись на лечение: ' + x,
            callback_data=f'{q_type} treatment|{int(treatment)}')])
    if q_back:
        buttons.append([IKB(text='Назад', callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data='main edit')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_add_week_kb(q_type, q_back, treatment):
    '''Клавиатура с выбором для добавления недели для записи'''
    x = 'да' if treatment else 'нет'
    buttons = [
        [IKB(text='Подтвердить', callback_data=f'{q_type} approve')],
        [IKB(text='Изменить время начала приема',
             callback_data=f'{q_type} change_time_start')],
        [IKB(text='Изменить время окончания приема',
             callback_data=f'{q_type} change_time_end')],
        [IKB(text='Изменить время начала приема в выходные',
             callback_data=f'{q_type} change_weekend_time_start')],
        [IKB(text='Изменить время конца приема в выходные',
             callback_data=f'{q_type} change_weekend_time_end')],
        [IKB(text='Добавить запись на лечение: ' + x,
             callback_data=f'{q_type} treatment|{int(treatment)}')],
        [IKB(text='Выбрать дни приема Виктор Евгеньевича',
             callback_data=f'{q_type} ve_days')],
        [IKB(text='Выбрать сокращенные дни',
             callback_data=f'{q_type} weekend_days')],
        [IKB(text='Выбрать нерабочие дни',
             callback_data=f'{q_type} days_without_work')],
    ]
    if q_back:
        buttons.append([IKB(text='Назад', callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data='main edit')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_weekdays_kb(q_type, q_back, days):
    '''Клавиатура с выбором дней недели'''

    texts = ['Понедельник', "Вторник", "Среда",
             "Четверг", "Пятница", "Суббота", "Воскресенье"]

    texts = [text + ' 🟢' if i in days else text
             for i, text in enumerate(texts)]

    buttons = [
        [IKB(text=texts[0], callback_data=f'{q_type}|0'),
         IKB(text=texts[1], callback_data=f'{q_type}|1'),
         ],
        [IKB(text=texts[2], callback_data=f'{q_type}|2'),
         IKB(text=texts[3], callback_data=f'{q_type}|3'),
         ],
        [IKB(text=texts[4], callback_data=f'{q_type}|4'),
         IKB(text=texts[5], callback_data=f'{q_type}|5'),
         ],
        [IKB(text=texts[6], callback_data=f'{q_type}|6')
         ]
    ]
    if q_back:
        buttons.append([IKB(text='Назад', callback_data=q_back)])
    buttons.append([IKB(text='На главную', callback_data='main edit')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_user_kb(add_app, add_app_move, another):
    '''Главная клавиатура пользователя'''
    buttons = []
    if add_app:
        app_text = 'Записаться еще раз' if another else 'Записаться'
        buttons.append([IKB(text=app_text,
                            callback_data='make_user_app choose_user_doctor')])
    if add_app_move:
        buttons.append([IKB(text='Перенести запись',
                            callback_data='move_user_app app_user_choice')])
        buttons.append([IKB(text='Удалить запись',
                            callback_data='del_user_app app_user_choice')])
    buttons += [
        [IKB(text='Информация и контакты', callback_data='info')],
        [IKB(text='Список услуг', callback_data='prices')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
