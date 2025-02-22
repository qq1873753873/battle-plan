from pydantic import BaseModel, Field
from typing import List


class Operation(BaseModel):
    id: str
    name: str
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    detail: str


class Task(BaseModel):
    id: str
    name: str
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    detail: str
    operations: List[Operation]


class Phase(BaseModel):
    id: str
    name: str
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    detail: str
    tasks: List[Task]


class Timeline(BaseModel):
    start: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class GanttData(BaseModel):
    timeline: Timeline
    phases: List[Phase]
