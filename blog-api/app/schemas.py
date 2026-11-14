from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60, examples=["Ayesha Khan"])
    email: EmailStr = Field(examples=["ayesha@example.com"])
    password: str = Field(min_length=6, max_length=72, examples=["secret123"])


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Categories ----------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=40, examples=["Technology"])
    description: str = Field(default="", max_length=200)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=40)
    description: Optional[str] = Field(default=None, max_length=200)


class CategoryOut(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: Optional[datetime] = None


# ---------- Blogs ----------
class BlogCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150, examples=["Getting started with FastAPI"])
    content: str = Field(min_length=10, examples=["FastAPI is a modern Python web framework..."])
    excerpt: Optional[str] = Field(default=None, max_length=300)
    category: Optional[str] = Field(default=None, examples=["Technology"])
    tags: List[str] = Field(default_factory=list, examples=[["python", "fastapi"]])
    published: bool = True


class BlogUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=150)
    content: Optional[str] = Field(default=None, min_length=10)
    excerpt: Optional[str] = Field(default=None, max_length=300)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    published: Optional[bool] = None


class BlogOut(BaseModel):
    id: str
    title: str
    slug: str
    content: str
    excerpt: str = ""
    category: Optional[str] = None
    tags: List[str] = []
    published: bool
    author_id: str
    author_name: str
    views: int = 0
    created_at: datetime
    updated_at: datetime


class BlogList(BaseModel):
    items: List[BlogOut]
    total: int
    page: int
    pages: int
