from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from create_bot import chat_id, admins, registrators, logger
from database.handlers import AsyncORM
from utils.async_functions import get_log
from keyboards.keyboards import get_universal_kb

common_router = Router()


@common_router.message(Command('get_id'))
async def get_id(message: Message):
    '''Метод возвращает id пользователя
    Команда работает без проверки условия на забаненость
    Нужна для того, чтобы пользователя можно было разблокировать
    '''
    log = await get_log(message=message)
    logger.info(log)
    await message.answer(str(message.from_user.id))


@common_router.message()
async def catch_messages(message: Message):
    '''Фунция ловит все необработанные сообщения и отправяет их в чат'''
    log = await get_log(message=message)
    logger.info(log)

    blocked = (await AsyncORM.check_user(message.from_user.id))[0]
    if ((message.text == '/start')
       or (message.from_user.id in admins + registrators)):
        return None

    reply = f'От пользователя (id: <code>{message.from_user.id}</code>'
    if message.from_user.username:
        reply += f', контакт: @{message.from_user.username}'
    if blocked:
        reply += ' заблокирован'
    reply += ') пришло сообщение:\n\n'
    reply += message.text
    await message.bot.send_message(
        chat_id=chat_id, text=reply)


@common_router.callback_query(F.data == 'placeholder')
async def handle_placeholder(call: CallbackQuery):
    await call.answer()
    log = await get_log(call=call)
    logger.info(log)


@common_router.callback_query()
async def return_main_kb(call: CallbackQuery, state: FSMContext):
    '''Обработчик удаляет сообщение если оно неактуально'''
    log = await get_log(call=call, state=state)
    logger.info(log)
    reply = '<b>Данная клавиатура больше недоступна\n'
    reply += 'Попробуйте повторить действия на новой клавиатуре</b>\n\n'
    reply += call.message.text
    if call.from_user.id in admins + registrators:
        return await call.message.edit_text(
            text=reply,
            reply_markup=get_universal_kb(tp='main rm_mk')
        )
    blocked = (await AsyncORM.check_user(call.from_user.id))[0]
    if blocked:
        return None
    await call.message.edit_text(
        text=reply,
        reply_markup=get_universal_kb(tp='get_user_main_kb rm_mk'))
