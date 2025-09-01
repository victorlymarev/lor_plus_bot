import logging
from decouple import Config, RepositoryEnv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.enums import ParseMode
from database.db_create import Base, engine
from omegaconf import OmegaConf
from redis.asyncio import Redis

import os
import locale

os.environ["LC_ALL"] = "ru_RU.UTF-8"
os.environ["LANG"] = "ru_RU.UTF-8"
locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")

config = Config(RepositoryEnv('../.env'))

# чтение переменных среды
# их по идее нужно добавить внутрь конфига, который сможет менять администратор
admins = [int(i) for i in config('ADMINS').split(', ')]
user_appointment_limit = int(config('USER_APPOINTMENTS_LIMIT'))
user_treatment_limit = int(config('USER_TREATMENT_LIMIT'))
registrators = [int(i) for i in config('REG').split(', ')]
chat_id = int(config('CHAT_ID'))

redis = Redis(
    host='localhost',
    port=6380,
    password=config('REDIS_PASSWORD'),
    db=0,
    decode_responses=True
)

# логгер
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s -\
                        %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# бот
bot = Bot(token=config('TOKEN'),
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=RedisStorage(redis=redis))


# бд
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        logger.info('бд создана')


day_config = OmegaConf.to_container(
    OmegaConf.load("../data/yaml_configs/day_config.yaml"))
week_config = OmegaConf.to_container(
    OmegaConf.load("../data/yaml_configs/week_config.yaml"))
doctors = OmegaConf.to_container(
    OmegaConf.load("../data/yaml_configs/doctors.yaml"))
messeges = OmegaConf.to_container(
    OmegaConf.load("../data/yaml_configs/messeges.yaml"))
m_final = OmegaConf.to_container(
    OmegaConf.load("../data/yaml_configs/m_final.yaml"))
m_final_short = OmegaConf.to_container(
    OmegaConf.load("../data/yaml_configs/m_final_short.yaml"))
day_names = OmegaConf.to_container(
    OmegaConf.load("../data/yaml_configs/day_names.yaml"))
