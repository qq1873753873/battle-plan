from model.models import db,Conversation
from sqlalchemy import select,desc
class ConversationService():
    def get_conversations(self):
        # 查询所有未被删除的 Conversation 记录
        query = select(Conversation).where(Conversation.is_deleted == False).order_by(desc(Conversation.updated_at))

        # 执行查询
        result = db.session.execute(query).scalars().all()

        # 打印结果
        for conversation in result:
            print(conversation.id, conversation.name)
        # 转换为字典列表
        conversations_data = [
            {
                "battle_conversation_id": conversation.id,
                "name": conversation.name,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            }
            for conversation in result
        ]
        return conversations_data
    
    def delete(self, battle_conversation_id):
        """
        逻辑删除指定 ID 的对话记录
        :param conversation_id: 对话记录的 ID
        :return: 是否删除成功
        """
        # 查询指定 ID 的记录
        conversation = db.session.get(Conversation, battle_conversation_id)

        if not conversation:
            # 如果记录不存在，返回 False 或抛出异常
            return False

        # 更新 is_deleted 字段为 True
        conversation.is_deleted = True

        try:
            # 提交事务
            db.session.commit()
            return True
        except Exception as e:
            # 如果提交失败，回滚事务
            db.session.rollback()
            print(f"Error during logical delete: {e}")
            return False
        
    def rename(self, battle_conversation_id, new_name):
        """
        更新指定 ID 的对话记录的名称
        :param battle_conversation_id: 对话记录的 ID
        :param new_name: 新的对话名称
        :return: 是否更新成功
        """
        # 查询指定 ID 的记录
        # 查询指定 ID 且未被删除的记录
        query = select(Conversation).where(
            Conversation.id == battle_conversation_id,
            Conversation.is_deleted == False
        )
        conversation = db.session.execute(query).scalar_one_or_none()

        if not conversation:
            # 如果记录不存在，返回 False 或抛出异常
            return False

        # 检查新名称是否为空或无效
        if not new_name or not isinstance(new_name, str):
            print("Invalid new name provided.")
            return False

        # 更新对话记录的名称
        conversation.name = new_name

        try:
            # 提交事务
            db.session.commit()
            return True
        except Exception as e:
            # 如果提交失败，回滚事务
            db.session.rollback()
            print(f"Error during renaming: {e}")
            return False
    
    def get_conversation_by_id(self, battle_conversation_id):
        """
        根据 battle_conversation_id 查询会话记录。
        :param battle_conversation_id: 会话的 ID
        :return: 如果找到会话记录，则返回该记录；否则返回 None
        """
        # 构造查询
        query = select(Conversation).where(
            Conversation.id == battle_conversation_id,
            Conversation.is_deleted == False  # 确保只查询未被删除的记录
        )

        # 执行查询并获取结果
        result = db.session.execute(query).scalar_one_or_none()

        return result
    
    @staticmethod
    def save_conversation_id_to_db(battle_conversation_id, conversation_id, stage):
        """
        根据 battle_conversation_id 和 stage 将 conversation_id 保存到数据库中。
        :param battle_conversation_id: conversations 表的主键
        :param conversation_id: 要保存的 conversation_id
        :param stage: 阶段值（1, 2, 3, 4），决定保存到 id1, id2, id3, id4 中
        """
        # 检查 stage 是否合法
        if stage not in {1, 2, 3, 4}:
            raise ValueError("Invalid stage value. Must be 1, 2, 3, or 4.")

        try:
            # 查询是否已存在 battle_conversation_id 对应的记录
            conversation = db.session.query(Conversation).filter_by(id=battle_conversation_id).first()

            if not conversation:
                # 如果不存在，则创建新记录
                conversation = Conversation(
                    id=battle_conversation_id,
                    name="New Conversation"  # 默认名称
                )
                db.session.add(conversation)
                db.session.flush()  # 确保新记录的 ID 可用

            # 根据 stage 更新对应的字段
            field_name = f"id{stage}"
            setattr(conversation, field_name, conversation_id)

            # 提交更改
            db.session.commit()
            print(f"Saved conversation_id '{conversation_id}' to {field_name} for battle_conversation_id '{battle_conversation_id}'")
        except Exception as e:
            # 回滚事务
            db.session.rollback()
            print(f"Error saving conversation_id: {e}")