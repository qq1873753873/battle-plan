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

# class Conversation(db.Model):
#     __tablename__ = "conversations"
#     __table_args__ = (
#         db.PrimaryKeyConstraint("id", name="conversation_pkey"),
#     )
#     id = db.Column(StringUUID, server_default=db.text("uuid_generate_v4()"))
#     name = db.Column(db.String(255), nullable=False)
#     _inputs: Mapped[dict] = mapped_column("inputs", db.JSON)
#     introduction = db.Column(db.Text)
#     created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP(0)"))
#     updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP(0)"))


#     is_deleted = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))



# class Message(db.Model):
#     __tablename__ = "messages"
#     __table_args__ = (
#         db.PrimaryKeyConstraint("id", name="message_pkey"),
#     )
#     id = db.Column(StringUUID, server_default=db.text("uuid_generate_v4()"))
#     conversation_id = db.Column(StringUUID, db.ForeignKey("conversations.id"), nullable=False)
#     _inputs: Mapped[dict] = mapped_column("inputs", db.JSON)
#     query: Mapped[str] = db.Column(db.Text, nullable=False)
#     message = db.Column(db.JSON, nullable=False)
#     answer: Mapped[str] = db.Column(db.Text, nullable=False)
#     parent_message_id = db.Column(StringUUID, nullable=True)
#     created_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP(0)"))
#     updated_at = db.Column(db.DateTime, nullable=False, server_default=db.text("CURRENT_TIMESTAMP(0)"))
    