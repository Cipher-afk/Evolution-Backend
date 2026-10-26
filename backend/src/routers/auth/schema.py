from sqlmodel import SQLModel, Field, Column
from uuid import UUID
import uuid
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime
from enum import Enum

# class Rank(Enum, str):
#     S = "s"
#     A = "a"
#     B = "b"
#     C = "c"
#     D = "d"
#     E = "e"
#     F = "f"


class User(SQLModel, table=True):
    __tablename__ = "users"
    user_id: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, unique=True),
    )
    email: str = Field(sa_column=Column(pg.VARCHAR, nullable=False, unique=True))
    username: str = Field(sa_column=Column(pg.VARCHAR,nullable=False,unique=True))
    password_hash: str
    goal_id: UUID = Field(foreign_key="goals.goal_id", nullable=True)
    niche_id:UUID = Field(foreign_key='niche.niche_id',nullable=True)
    lifetime_xp: int = Field(sa_column=Column(pg.INTEGER, default=0))
    weekly_xp: int = Field(sa_column=Column(pg.INTEGER, default=0))
    level_up_xp: int = Field(sa_column=Column(pg.INTEGER, default=1000))
    current_level: int = Field(sa_column=Column(pg.INTEGER, default=1))
    is_verified: bool = Field(default=False)
    online_status:bool = Field(default=False)
    role:str = Field(sa_column=Column(pg.VARCHAR,default='user'))
    niche_invitation_link:str = Field(sa_column=Column(pg.VARCHAR,nullable=True))
    date_joined: float = Field(default_factory=lambda: datetime.now().timestamp())