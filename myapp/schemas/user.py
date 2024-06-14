# schemas/user.py
from typing import List

from pydantic import BaseModel, EmailStr

from myapp.schemas.post import Post


class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    posts: List[Post] = []

    class Config:
        orm_mode = True