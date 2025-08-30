from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    action_type = State()

    doctor_id = State()
    date = State()
    time = State()

    doctor_id_from = State()
    date_from = State()
    time_from = State()

    user_name = State()
    message = State()
    msg_id = State()
    user_id = State()
    user_actions = State()
    mark = State()
    doctor_true = State()


class UserForm(StatesGroup):
    doctor_id_from = State()
    date_from = State()
    time_from = State()
    doctor_id = State()
    date = State()
    time = State()
    action_type = State()
