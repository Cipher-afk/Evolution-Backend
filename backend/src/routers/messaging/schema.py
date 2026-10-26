from sqlmodel import SQLModel,Field,Column
from uuid import UUID
import uuid
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime,timezone
from enum import Enum

class RequestStatus(str,Enum):
    ACCEPT = 'accept'
    REJECT = 'reject'
    PENDING = 'pending'

class Message(SQLModel,table=True):
    __tablename__ = 'message'
    message_id:UUID = Field(default_factory=uuid.uuid4,sa_column=Column(pg.UUID,nullable=False,unique=True,primary_key=True))
    user_id:UUID = Field(foreign_key='users.user_id')
    friend_id:UUID = Field(foreign_key='friend.friend_id')
    sender_username:str
    receiver_username:str
    time_sent:datetime = Field(default_factory=lambda: datetime.now(timezone.utc),sa_column=Column(pg.TIMESTAMP(timezone=True)))

class Friend(SQLModel,table=True):
    __tablename__ = 'friend'
    friend_id:UUID = Field(default_factory=uuid.uuid4,sa_column=Column(pg.UUID,nullable=False,unique=True,primary_key=True))
    user_id:UUID = Field(foreign_key='users.user_id')
    friend_username:str = Field(sa_column=Column(pg.VARCHAR,unique=True))
    friend_lifetime_xp:int
    friend_niche_name:str
    friend_goal_name:str

class FriendRequest(SQLModel,table=True):
    __tablename__ = 'friend_request'
    request_id:UUID = Field(default_factory=uuid.uuid4,sa_column=Column(pg.UUID,nullable=False,unique=True,primary_key=True))
    user_id:UUID = Field(foreign_key='users.user_id')
    potential_friend_username:str = Field(sa_column=Column(pg.VARCHAR,unique=True))
    request_status:RequestStatus = Field(sa_column=Column(pg.ENUM(RequestStatus,name='request_status'),default=RequestStatus.PENDING))
