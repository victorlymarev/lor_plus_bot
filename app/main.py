import asyncio
from create_bot import bot, dp, create_tables, admins, registrators
from handlers.admin_commands import admin_router
from handlers.user_commands import user_router
from handlers.common_commands import common_router
from database.handlers import AsyncORM


from aiogram.types import BotCommand, BotCommandScopeDefault


async def set_commands():
    commands = [BotCommand(command='start', description='Старт'),]
    await bot.set_my_commands(commands, BotCommandScopeDefault())


async def add_admins_to_db():
    tasks = [asyncio.create_task(AsyncORM.check_user(user))
             for user in admins + registrators]
    await asyncio.gather(*tasks)

async def main():

    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(common_router)

    await set_commands()
    await create_tables()
    await add_admins_to_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
