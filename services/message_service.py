import datetime
import uuid
from model.models import db,Message
from sqlalchemy import select
from dtos.response_utils import *
class MessageService():
    def save_messages(self,message_id,is_think_message,time_consumed_on_thinking):
        '''
        用于前三个阶段的计时
        '''
        new_message = Message(
            id=message_id,
            is_think_message=is_think_message,
            time_consumed_on_thinking=time_consumed_on_thinking
        )
        db.session.add(new_message)
        try:
            # 提交事务
            db.session.commit()
            return True
        except Exception as e:
            # 如果提交失败，回滚事务
            db.session.rollback()
            print(f"Error during save message: {e}")
            return False
        
    def save_message(self,
        id=str(uuid.uuid4()),
        battle_conversation_id=None,
        is_think_message=False,
        think_content="",
        time_consumed_on_thinking=0.0,
        query="",
        answer="",
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    ):
        """
        保存一条 Message 记录到数据库，用于第四阶段记录消息
        
        :param data: 包含需要保存的数据的字典
        """
        try:
            # 创建 Message 实例
            message = Message(
                id=id, 
                battle_conversation_id=battle_conversation_id,
                is_think_message=is_think_message,
                think_content=think_content,
                time_consumed_on_thinking=time_consumed_on_thinking,
                query=query,
                answer=answer,
                created_at=created_at,  
                updated_at=updated_at   
            )

            # 添加到数据库会话
            db.session.add(message)

            # 提交事务
            db.session.commit()

            print(f"Message with ID {message.id} saved successfully.")
            return message.id  # 返回保存的记录 ID

        except Exception as e:
            # 如果发生错误，回滚事务并打印错误信息
            db.session.rollback()
            print(f"Error saving message: {e}")
            return None

    def get_message_by_id(self, message_id):
        """
        根据消息 ID 查询消息记录。
        :param message_id: 消息的 ID
        :return: 如果找到消息记录，则返回该记录；否则返回 None
        """
        # 构造查询
        query = select(Message).where(Message.id == message_id)

        # 执行查询并获取结果
        result = db.session.execute(query).scalar_one_or_none()

        return result

    def get_messages_by_battle_conversation_id(self, battle_conversation_id):
        """
        根据 battle_conversation_id 获取所有消息记录
        :param battle_conversation_id: 作战会话 ID
        :return: 消息记录列表（字典格式）
        """
        # 查询指定 conversation_id 的消息记录，并按创建时间排序
        query = (
            select(Message)
            .where(Message.battle_conversation_id == battle_conversation_id)
            .order_by(Message.created_at.asc())  # 按时间升序排列
        )

        # 执行查询
        result = db.session.execute(query).scalars().all()

        # 如果没有找到任何消息，返回空列表
        if not result:
            return []
        # 转换为字典列表
        messages_data = [
            MessageResponse(
                id=str(message.id),
                conversation_id="",
                query=message.query,
                message_files=[],
                answer=message.answer,
                parent_message_id=None,
                created_at=round(message.created_at.timestamp()),
                think_content=message.think_content,
                stage=4,
                time_consumed_on_thinking=message.time_consumed_on_thinking
            
            )
            for message in result
        ]

        return messages_data