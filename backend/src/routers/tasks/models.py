from pydantic import BaseModel,ConfigDict
from .schema import Difficulty, TaskStatus
from typing import List
from uuid import UUID


class TaskModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    task_id: UUID
    day: int
    task: str
    task_description: str
    difficulty: str
    xp_awarded: int
    xp_gained: int
    task_status: str
    

class PreviousDayTaskModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    task_id:UUID
    weekly_task_id: UUID
    task_id: UUID
    day: int
    task: str
    task_description: str
    difficulty: Difficulty
    xp_awarded: int
    xp_gained: int 
    task_status: str


class CurrentLevelPathModel(BaseModel):
    title: str
    main_focus: str
    description: str
    skills: List[str]
    knowledge: List[str]
    practical_abilities: List[str]
    completion_criteria: List[str]
    progression_areas: List[str]


class WeeklyChallengeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    challenge_id: UUID
    task_id: UUID
    challenge: str
    challenge_description: str
    xp_awarded: int
    xp_gained: int
    task_status: str
