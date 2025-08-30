from aiogram.types import Message, CallbackQuery
from aiogram.filters import Filter
from database.handlers import AsyncORM
from create_bot import bot, chat_id


class IsAdmin(Filter):
    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in self.admin_ids


class IsUser(Filter):
    def __init__(self,
                 admin_ids: list[int],
                 registrator_ids: list[int]
                 ) -> None:

        self.registrator_ids = registrator_ids
        self.admin_ids = admin_ids

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if event.from_user.id in (self.registrator_ids +
                                  self.admin_ids
                                  ):
            return False
        if event.from_user.username is not None:
            user_name = '@' + event.from_user.username
        else:
            user_name = None
        banned, first = await AsyncORM.check_user(
            event.from_user.id, user_name)

        if first:
            reply = '<b>Новый пользователь</b>'
            reply += f'\nid: <code>{event.from_user.id}</code>'
            if user_name is not None:
                reply += f', контакт: {user_name}'

            await bot.send_message(chat_id=chat_id, text=reply)
        return not banned
