# from model.models import db,Message
# from sqlalchemy import select
# class MessageService():
#     def get_messages(self, conversation_id):
#         """
#         根据 conversation_id 获取所有消息记录
#         :param conversation_id: 会话 ID
#         :return: 消息记录列表（字典格式）
#         """
#         # 查询指定 conversation_id 的消息记录，并按创建时间排序
#         query = (
#             select(Message)
#             .where(Message.conversation_id == conversation_id)
#             .order_by(Message.created_at.asc())  # 按时间升序排列
#         )

#         # 执行查询
#         result = db.session.execute(query).scalars().all()

#         # 如果没有找到任何消息，返回空列表
#         if not result:
#             return []

#         # 转换为字典列表
#         messages_data = [
#             {
#                 "id": str(message.id),
#                 "conversation_id": str(message.conversation_id),
#                 "inputs": message._inputs,
#                 "query": message.query,
#                 "message": message.message,
#                 "answer": message.answer,
#                 "parent_message_id": str(message.parent_message_id) if message.parent_message_id else None,
#                 "created_at": message.created_at.isoformat(),
#                 "updated_at": message.updated_at.isoformat()
#             }
#             for message in result
#         ]

#         return messages_data