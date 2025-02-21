from model.models import db,Message
from sqlalchemy import select
class MessageService():
    def save_messages(self,message_id,is_think_message,time_consumed_on_thinking):
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

    # def get_messages(self, conversation_id):
    #     """
    #     根据 conversation_id 获取所有消息记录
    #     :param conversation_id: 会话 ID
    #     :return: 消息记录列表（字典格式）
    #     """
    #     # 查询指定 conversation_id 的消息记录，并按创建时间排序
    #     query = (
    #         select(Message)
    #         .where(Message.conversation_id == conversation_id)
    #         .order_by(Message.created_at.asc())  # 按时间升序排列
    #     )

    #     # 执行查询
    #     result = db.session.execute(query).scalars().all()

    #     # 如果没有找到任何消息，返回空列表
    #     if not result:
    #         return []

    #     # 转换为字典列表
    #     messages_data = [
    #         {
    #             "id": str(message.id),
    #             "conversation_id": str(message.conversation_id),
    #             "inputs": message._inputs,
    #             "query": message.query,
    #             "message": message.message,
    #             "answer": message.answer,
    #             "parent_message_id": str(message.parent_message_id) if message.parent_message_id else None,
    #             "created_at": message.created_at.isoformat(),
    #             "updated_at": message.updated_at.isoformat()
    #         }
    #         for message in result
    #     ]

    #     return messages_data