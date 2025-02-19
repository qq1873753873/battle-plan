import json
from flask_cors import cross_origin
import uuid
from services.conversation_service import ConversationService
#from services.message_service import MessageService
from . import api  
from flask import Response, request, jsonify, app, stream_with_context,session,current_app
import os
from datetime import datetime
import requests
from model.models import db,Conversation

#获取会话列表
@api.route('/conversations', methods=['GET'])
def conversations():
    '''
    本地对应一个battle_conversation_id，和至慧工作流的会话不同，这里一个包含至慧的4个id
    '''
    #没有别的参数，这是获取所有的对话
    conversation_service=ConversationService()
    result=conversation_service.get_conversations()
    # 手动序列化为 JSON 字符串
    json_data = json.dumps(result, ensure_ascii=False)

    # 返回 Response 对象，并设置正确的 MIME 类型和编码
    return Response(json_data, content_type='application/json; charset=utf-8')

#删除会话
@api.route('/conversations/<battle_conversation_id>', methods=['DELETE'])
def delete_conversation(battle_conversation_id):
    conversation_service = ConversationService()
    success = conversation_service.delete(battle_conversation_id)

    if success:
        return '', 204  # 成功时不返回消息
    else:
        return jsonify({"error": "Conversation not found"}), 404


#获取单个会话的历史聊天记录
@api.route('/messages', methods=['GET'])
def messages():
    """
    获取单个会话的历史聊天记录。
    根据 battle_conversation_id 查询数据库中的 id1, id2, id3, id4，
    并分别调用外部 API 获取对应的消息记录。
    """
    # 获取 URL 参数 battle_conversation_id
    battle_conversation_id = request.args.get('battle_conversation_id')

    if not battle_conversation_id:
        return jsonify({"error": "Missing required parameter: battle_conversation_id"}), 400

    # 查询数据库中的记录
    conversation = Conversation.query.filter_by(id=battle_conversation_id).first()
    if not conversation:
        return jsonify({"error": f"No record found for battle_conversation_id: {battle_conversation_id}"}), 404

    # 获取 id1, id2, id3, id4
    ids = [conversation.id1, conversation.id2, conversation.id3, conversation.id4]

    # 外部 API 的基础 URL
    urls =[ "http://123.57.244.236:35001//console/api/installed-apps/0e1144c1-658d-4b33-a180-939d92cd6008/messages",
           "http://123.57.244.236:35001//console/api/installed-apps/4c97a3df-f2cc-4e3b-8ddf-6825f7fa1e85/messages",
           "http://123.57.244.236:35001//console/api/installed-apps/b09fdf1b-e143-4ab1-866a-6dbce4f35392/messages",
           "http://123.57.244.236:35001//console/api/installed-apps/cbc8823f-3d4d-47f8-a84c-dd3ae8f03576/messages"  
    ]

    # 存储所有消息记录
    all_messages = []

    # 遍历 id1, id2, id3, id4，分别调用外部 API
    for i, conversation_id in enumerate(ids, start=1):
        if not conversation_id:
            print(f"id{i} is missing, skipping...")
            continue

        try:
            # 构造请求 URL
            url = f"{urls[i-1]}?conversation_id={conversation_id}"

            # 调用外部 API
            response = requests.get(url)

            # 检查响应状态码
            if response.status_code == 200:
                # 解析 JSON 数据
                messages = response.json()
                all_messages.append({
                    f"id{i}_messages": messages
                })
            else:
                print(f"Failed to fetch messages for id{i}: {response.status_code}")
        except Exception as e:
            print(f"Error fetching messages for id{i}: {e}")

    # 返回合并后的结果
    return jsonify({"battle_conversation_id": battle_conversation_id, "messages": all_messages})

#文件上传
@api.route('/upload', methods=['POST'])
def upload():
    # 检查是否有文件上传
    if 'file' not in request.files:
        return {"error": "No file part in the request"}, 400

    file = request.files['file']
    if file.filename == '':
        return {"error": "No selected file"}, 400

    # 获取其他表单字段
    form_data = request.form.to_dict()

    # 目标服务的 URL
    url = "http://123.57.244.236:35001/console/api/files/upload"

    try:
        # 构造 multipart/form-data 请求
        files = {'file': (file.filename, file.stream, file.content_type)}
        response = requests.post(url, data=form_data, files=files, verify=False)

        # 检查目标服务的响应状态码
        if response.status_code != 201:
            return {"error": "Failed to forward request", "status_code": response.status_code}, 500

        # 返回目标服务的响应
        return Response(response.content, status=response.status_code, content_type=response.headers['Content-Type'])

    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}, 500

#总对话接口
@api.route('/chat',methods=['POST'])
def chat():
    data = request.json
    query = data.get('query')
    battle_conversation_id=data.get('battle_conversation_id')
    if battle_conversation_id=="":
        battle_conversation_id=str(uuid.uuid4())
    if not data:
        return {"error": "No data provided"}, 400
    if 'user_stage' not in session or (session['user_stage'] == 1 and not next_stage(query)):
        session['user_stage'] = 1
        print(f"当前阶段:{session['user_stage']}")
        response_data = extract(data,battle_conversation_id)
    elif session['user_stage'] == 2 and not next_stage(query):
        print(f"当前阶段:{session['user_stage']}")
        response_data = goal(data,battle_conversation_id)
    elif session['user_stage'] == 3 and not next_stage(query):
        print(f"当前阶段:{session['user_stage']}")
        response_data = task(data,battle_conversation_id)
    elif session['user_stage'] == 4:
        print(f"当前阶段:{session['user_stage']}")
        response_data = solution(data,battle_conversation_id)
        #生成一次后返回状态1
        session['user_stage'] = 1
    else:
        return {"error": "Invalid stage"}, 400
    return Response(response_data)

#1. 想定内容提取与对话
def extract(data, battle_conversation_id):
    url = "http://123.57.244.236:35001//console/api/installed-apps/0e1144c1-658d-4b33-a180-939d92cd6008/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False, stream=True)

    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500

    # 返回流式响应
    return generate(response, battle_conversation_id, 1, current_app._get_current_object())


#2. 总体作战目标
def goal(data,battle_conversation_id):
    url = "http://123.57.244.236:35001//console/api/installed-apps/4c97a3df-f2cc-4e3b-8ddf-6825f7fa1e85/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500
    # 返回流式响应
    return generate(response,battle_conversation_id,2, current_app._get_current_object())

#3. 作战任务筹划
def task(data,battle_conversation_id):
    url = "http://123.57.244.236:35001//console/api/installed-apps/b09fdf1b-e143-4ab1-866a-6dbce4f35392/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500
    # 返回流式响应
    return generate(response,battle_conversation_id,3, current_app._get_current_object())


#4. 作战行动方案
def solution(data,battle_conversation_id):
    url = "http://123.57.244.236:35001//console/api/installed-apps/cbc8823f-3d4d-47f8-a84c-dd3ae8f03576/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500
    # 返回流式响应
    return generate(response,battle_conversation_id,4, current_app._get_current_object())

#加工来自至慧工作流的响应
def generate(response, battle_conversation_id, stage, app):
    buffer = ""
    first_conversation_id_found = False  # 标志变量，用于记录是否已处理过 conversation_id

    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            try:
                # 将字节数据解码为字符串
                decoded_chunk = chunk.decode('utf-8')
                buffer += decoded_chunk

                # 按行分割数据块
                lines = buffer.split('\n')
                buffer = lines.pop()  # 最后一行可能是不完整的，留作下一次处理

                # 处理每一行数据
                for line in lines:
                    if line.startswith('data: '):
                        # 提取原始数据部分（去掉 "data: " 前缀）
                        original_data = line[len('data: '):].strip()

                        # 跳过空行或无效数据
                        if not original_data:
                            continue

                        # 解析原始 JSON 数据
                        try:
                            parsed_data = json.loads(original_data)
                        except json.JSONDecodeError as e:
                            print(f"JSON 解析失败: {e}, 数据: {original_data}")
                            continue

                        # 提取 conversation_id
                        conversation_id = parsed_data.get("conversation_id")

                        if conversation_id and not first_conversation_id_found:
                            # 如果是第一次找到 conversation_id，则调用回调函数
                            with app.app_context():  # 使用传入的应用实例
                                ConversationService.save_conversation_id_to_db(
                                    battle_conversation_id, conversation_id, stage
                                )
                            first_conversation_id_found = True  # 设置标志变量

                        # 将 battle_conversation_id 添加到顶层
                        parsed_data["battle_conversation_id"] = battle_conversation_id

                        # 转换为 JSON 字符串并加上 data: 前缀
                        yield f"data: {json.dumps(parsed_data)}\n"
            except UnicodeDecodeError:
                # 如果解码失败，跳过该块
                continue

#根据用户查询判断是否进入下一阶段
def next_stage(query):
    current_stage=session['user_stage']
    if current_stage==1:
        if query == "请你思考一下向我汇报" or "作战目标" in query or "目标" in query:
            session['user_stage']+=1
            return True
        else:
            return False
    elif current_stage==2:
        if query == "审批通过，请制定作战任务" or "作战任务" in query or "任务" in query:
            session['user_stage']+=1
            return True
        else:
            return False
    elif current_stage==3:
        if query == "审批通过，请制定详细作战行动方案" or "作战行动方案" in query or "方案" in query:
            session['user_stage']+=1
            return True
        else:
            return False
    
