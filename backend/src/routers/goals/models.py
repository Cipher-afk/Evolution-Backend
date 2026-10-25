from pydantic import BaseModel
from .schema import Goals
from typing import List


class GoalDescriptionModel(BaseModel):
    goal_name:str
    goal_description: str
    duration: str
    niche_name: str


class ListingGoalsModel(BaseModel):
    goal_name: str

class SimilarGoalsModel(BaseModel):
    goal_name:str
    duration: str

class NicheResponseModel(BaseModel):
    niche_name:str
    goals:List[Goals]
