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
logger = logging.getLogger('main_logger')
logger.setLevel(logging.INFO)  # 🔴 Важно: установите уровень логирования
logging.getLogger('aiogram').setLevel(logging.WARNING)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(module)s:%(lineno)d - %(levelname)s - %(message)s'
)

log_dir = '../data/logs'
os.makedirs(log_dir, exist_ok=True)

file_handler = logging.FileHandler(
    filename=os.path.join(log_dir, 'app.log'),
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# бот
bot = Bot(token=config('TOKEN'),
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=RedisStorage(redis=redis))

# бд
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        logger.info('База данных создана')


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
