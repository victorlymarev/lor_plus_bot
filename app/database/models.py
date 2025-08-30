from sqlalchemy import SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from database.db_create import Base
import datetime


class Appointments(Base):

    __tablename__ = 'appointments'

    id: Mapped[int] = mapped_column(primary_key=True)
    doctor_id = mapped_column(SmallInteger)
    time: Mapped[datetime.datetime]
    user_id: Mapped[int | None]
    user_name: Mapped[str | None]
    available_from_user: Mapped[bool]
    available_from_admin: Mapped[bool]
    skipped: Mapped[bool] = mapped_column(default=False)


class Logs(Base):

    __tablename__ = 'logs'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    action_type: Mapped[str]
    action: Mapped[str]
    action_time: Mapped[datetime.datetime]


class Users(Base):

    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str | None]
    banned: Mapped[bool] = mapped_column(default=False)
