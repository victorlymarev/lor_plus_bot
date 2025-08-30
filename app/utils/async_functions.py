from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards.keyboards import get_back_to_main_kb
from database.handlers import AsyncORM
from create_bot import (admins,
                        registrators,
                        m_final,
                        user_appointment_limit,
                        user_treatment_limit)
from utils.utils import (get_other_doctor_id,
                         to_datetime,
                         get_doctor_name_by_id,
                         get_day_by_index
                         )
from datetime import timedelta, datetime


async def back_to_main(call: CallbackQuery, state: FSMContext):
    reply = 'Данная клавиатура неактивна\n'
    reply += 'Выполните команду /start и попробуйте ещё раз'
    await call.message.edit_text(text=reply,
                                 reply_markup=get_back_to_main_kb())
    await state.clear()


async def back_to_main_user(call: CallbackQuery, state: FSMContext):
    reply = 'Данная клавиатура неактивна\n'
    reply += 'Попробуйте еще раз'
    await call.message.edit_text(text=reply,
                                 reply_markup=get_back_to_main_kb(
                                     q_main='get_user_main_kb edit'))
    await state.clear()


async def check_user_limits(user_id: int) -> tuple[bool, bool]:
    """Проверяет лимиты записей пользователя
    Возвращает кортеж из двух будевых значений
    True если предел не превыше, False иначе
    """
    apps, treats, _ = await AsyncORM.get_records_for_main_menu(user_id)
    app_limit_ok = len(apps) < user_appointment_limit
    treat_limit_ok = len(treats) < user_treatment_limit
    return app_limit_ok, treat_limit_ok


async def get_answer_type(call: CallbackQuery):
    if 'rm_mk' in call.data:
        await call.message.edit_reply_markup(reply_markup=None)
        answer = call.message.answer
    else:
        answer = call.message.edit_text
    return answer


async def get_critical_messege(user_id: int,
                               user_name: str,
                               status_code: int,
                               data: dict):
    text = '<b>Ошибка!</b>'
    text += f'\n{m_final[status_code]}'
    result = []
    if status_code in [60, 63]:
        dt = to_datetime(data['date'], data['time'])
        od = get_other_doctor_id(data['doctor_id'])
        doctors = od + [data['doctor_id']]
        result = (await AsyncORM.get_visits(
            date_from=dt - timedelta(minutes=20),
            date_to=dt + timedelta(minutes=20),
            doctor_id=doctors))
        result = [r for r in result if r.user_id]

    elif status_code == 61:
        od = get_other_doctor_id(data['doctor_id'])
        dt = to_datetime(data['date'], data['time'])
        result = (await AsyncORM.get_visits(
            date_from=dt, date_to=dt, doctor_id=od))
        result = [r for r in result if r.user_id]

    elif status_code == 62:
        return text

    if len(result) == 1:
        text += '\n\n<b>Запись, которую необходимо удалить'
        text += ', чтобы выполнить действие:</b>'

    elif len(result) > 1:
        text += '\n\n<b>Записи которую необходимо удалить'
        text += ', чтобы выполнить действие:</b>'

    for ind, res in enumerate(result, 1):
        doctor_name = get_doctor_name_by_id(res.doctor_id, case='short')
        day_name = get_day_by_index(res.time.weekday(), short=True)
        date_str = res.time.strftime('%d.%m.%Y')
        time = res.time.strftime('%H:%M')

        text += f'\n{ind}. Врач: <b>{doctor_name}</b>, '
        text += f'Дата: <b>{date_str} ({day_name}) {time}</b>'
        if user_id:
            text += f'\nid: <b><code>{user_id}</code></b>'
        if user_id in admins:
            text += ' (владелец)'
        elif user_id in registrators:
            text += ' (регистратор)'
        if user_name:
            text += f', контакт: <b>{user_name}</b>'
    return text + '\n\n'


async def get_user_info(user_id: int, user_name: str,
                        make_app=False, remove_app=False,
                        move_app=False):
    text = f'id: <code>{user_id}</code>'
    if user_id in admins:
        text += ' (владелец)'
    elif user_id in registrators:
        text += ' (регистратор)'
    if user_name:
        text += f', контакт: {user_name}'

    apps = await AsyncORM.get_visits(user_id=user_id)
    marks = await AsyncORM.get_logs(
        user_ids=[user_id],
        action_types=['mark', 'make_app', 'move_app', 'remove_app'])

    n_all = len(apps)
    n_active = len([app for app in apps if app.time > datetime.now()])
    n_skips = len([app for app in apps if app.skipped])
    n_make_app = len([note for note in marks
                      if note.action_type == "make_app"])
    n_move_app = len([note for note in marks
                      if note.action_type == "move_app"])
    n_remove_app = len([note for note in marks
                        if note.action_type == "remove_app"])
    marks = [note for note in marks if note.action_type == "mark"]

    text += f'\nВсего записей: <b>{n_all}</b>'
    text += f'\nАктивных записей: <b>{n_active}</b>'
    text += f'\nНе приходил: <b>{n_skips}</b>'
    text += f'\nЗаписывался: <b>{n_make_app + make_app}</b>'
    text += f'\nПереносил запись: <b>{n_move_app + move_app}</b>'
    text += f'\nУдалял запись: <b>{n_remove_app + remove_app}</b>'

    if marks:
        text += '\n    <i>Пометки:</i>'
        for ind, note in enumerate(marks):
            date = note.action_time.strftime('%d.%m.%Y')
            m = note.action
            text += f'\n    <i>{ind}. {date} {m}</i>'
    return text
