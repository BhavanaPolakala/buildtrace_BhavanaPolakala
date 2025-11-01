# app/models.py
from pydantic import BaseModel
from typing import List

class Geometry(BaseModel):
    id: str
    type: str
    x: float
    y: float
    width: float
    height: float

class CompareRequest(BaseModel):
    old: List[Geometry]
    new: List[Geometry]

class CompareResponse(BaseModel):
    added: List[str]
    removed: List[str]
    moved: List[str]
    summary: str
