from sqlmodel import SQLModel, Field, Column
from uuid import UUID
import uuid
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.dialects.postgresql import ARRAY
from enum import Enum
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String


class Difficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    ADVANCED = "ADVANCED"
    HARD = "HARD"


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class DailyTask(SQLModel, table=True):
    __tablename__ = "tasks"
    task_id: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            pg.UUID, nullable=False, primary_key=True, index=True, unique=True
        ),
    )
    day: int = Field(default=1)
    weekly_task_id: UUID = Field(
        unique=False
    )  # Unique is false because it is passed down not generated and each task for the week needs to have the same weekly id
    user_id: UUID = Field(foreign_key="users.user_id")
    task: str
    task_description: str 
    difficulty:str = Field(
        sa_column=Column(pg.VARCHAR, nullable=True)
    )
    goal_id: UUID = Field(foreign_key="goals.goal_id")
    xp_awarded: int = Field(
        sa_column=Column(pg.INTEGER, nullable=False)
    )  # Xp given to the task
    xp_gained: int = Field(
        sa_column=Column(pg.INTEGER, default=0)
    )  # xp you gained after completion
    task_status: TaskStatus = Field(
        sa_column=Column(
            pg.ENUM(TaskStatus, name="task_status"), default=TaskStatus.PENDING
        )
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).date()
    )


class WeeklyChallenge(SQLModel, table=True):
    __tablename__ = "weeklychallenge"
    challenge_id: UUID = Field(
        default_factory=lambda: uuid.uuid4(), 
        sa_column=Column(pg.UUID, primary_key=True, unique=True),
    )
    user_id: UUID = Field(foreign_key="users.user_id")
    task_id: UUID = Field(foreign_key="tasks.task_id")
    weekly_task_id: UUID  # The weekly challenge islinked to the task at hand
    challenge: str
    challenge_description: str
    goal_id: UUID = Field(foreign_key="goals.goal_id")
    xp_awarded: int = Field(sa_column=Column(pg.INTEGER, nullable=False))
    xp_gained: int = Field(sa_column=Column(pg.INTEGER, default=0))
    task_status: TaskStatus = Field(
        sa_column=Column(
            pg.ENUM(TaskStatus, name="task_status"), default=TaskStatus.PENDING
        )
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),sa_column=Column(pg.TIMESTAMP(timezone=True), nullable=False, default=datetime.now(timezone.utc)))


class ProgressionPath(
    SQLModel, table=True
):  # This tracks the users progression for the prompt so the model underatnds improvement
    path_id: UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID, primary_key=True, nullable=False),
    )
    level: int = Field(unique=True)
    title: str
    user_id: UUID = Field(foreign_key="users.user_id")
    main_focus: str
    description: str
    skills: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    knowledge: List[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))
    practical_abilities: List[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )
    completion_criteria: List[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )
    progression_areas: List[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )
