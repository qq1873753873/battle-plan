from pydantic import BaseModel
from typing import Optional, List, Dict,Any
from enum import Enum

class Event(Enum):
    MESSAGE="message"
    MESSAGE_END="message_end"
    ERROR="error"


class StreamResponse(BaseModel):
    event: Optional[Event] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    answer: Optional[str] = None
    battle_conversation_id: Optional[str] = None
    is_think_content: Optional[bool] = None
    time_consumed: Optional[float] = None
    stage: Optional[int] = None
    error: Optional[str] = None
    status_code: int=None

    def to_json(self) -> str:
        """将对象转换为 JSON 字符串"""
        return self.model_dump_json()
    def to_stream_format(self) -> str:
        """将对象转换为流式响应格式：data: {}\n\n"""
        return f"data: {self.to_json()}\n\n"
    
class MessageFile(BaseModel):
    filename: str
    id: str
    size: int

class MessageResponse(BaseModel):
    answer: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: Optional[int]=0
    id: Optional[str] = None
    message_files: List[MessageFile] = []  # 默认为空列表
    parent_message_id: Optional[str] = None
    query: Optional[str] = None
    stage: Optional[int]=0
    think_content: Optional[str] = None
    time_consumed_on_thinking: Optional[float] = 0

class MessagesResponse(BaseModel):
    battle_conversation_id: Optional[str] = None
    messages: List[MessageResponse]=[]

