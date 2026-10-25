from sqlmodel import SQLModel, Field, Column, Relationship
import sqlalchemy.dialects.postgresql as pg
import uuid
from uuid import UUID
from typing import List


class Goals(SQLModel, table=True):
    __tablename__ = "goals"
    goal_id: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, unique=True),
    )
    user_id: UUID = Field(foreign_key="users.user_id")
    goal_name: str
    goal_description: str = Field(
        default=None, sa_column=Column(pg.VARCHAR, nullable=True)
    )
    duration: int = Field(default=None, sa_column=Column(pg.VARCHAR, nullable=True))
    niche_id: UUID = Field(foreign_key="niche.niche_id")
    niche: "Niche" = Relationship(
        back_populates="goals", sa_relationship_kwargs={"lazy": "selectin"}
    )


class Niche(SQLModel, table=True):
    __tablename__ = "niche"
    niche_id: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, unique=True),
    )
    user_id: UUID = Field(foreign_key="users.user_id")
    niche_name: str = Field(default=None, sa_column=Column(pg.VARCHAR, nullable=True,unique=False))
    goals: List["Goals"] = Relationship(
        back_populates="niche", sa_relationship_kwargs={"lazy": "selectin"}
    )
