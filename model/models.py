from flask_sqlalchemy import SQLAlchemy
from .types import StringUUID
from sqlalchemy.orm import Mapped, mapped_column
from typing import Any, Literal, Optional

db = SQLAlchemy()

class Conversation(db.Model):
    __tablename__ = "conversations"
    __table_args__ = (
        db.PrimaryKeyConstraint("id", name="conversation_pkey"),
    )
    id = db.Column(StringUUID, server_default=db.text("uuid_generate_v4()"))
    name = db.Column(db.String(255), nullable=False)
    #introduction = db.Column(db.Text)
    id1 = db.Column(StringUUID)
    id2 = db.Column(StringUUID)
    id3 = db.Column(StringUUID)
    id4 = db.Column(StringUUID)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP(0)"))
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP(0)"))
    is_deleted = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))

class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (
        db.PrimaryKeyConstraint("id", name="message_pkey"),
    )
    id = db.Column(StringUUID)
    is_think_message=db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    time_consumed_on_thinking = db.Column(db.Float, nullable=False, server_default=db.text("0.0"))
    
    