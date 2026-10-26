from pydantic import BaseModel, EmailStr
from typing import Dict, TypedDict
from uuid import UUID


class SignUpModel(BaseModel):
    username: str
    email: EmailStr
    password: str


class GoalDescriptionModel(BaseModel):
    goal_description: str
    duration: str
    niche_name: str


class LoginModel(BaseModel):
    email: str
    password: str


class UpdateUserModel(BaseModel):
    email: str
    info: Dict


class UserDataDict(TypedDict):
    user_id: str
    email: str
    username: str 