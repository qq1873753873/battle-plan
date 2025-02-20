import json
from flask_cors import cross_origin
import uuid
from services.conversation_service import ConversationService
from services.message_service import MessageService
from . import api  
from flask import Response, request, jsonify, app, stream_with_context,session,current_app
import os
from datetime import datetime
import requests
from model.models import db,Conversation
import time

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

#重命名会话
@api.route('/conversations/<battle_conversation_id>/rename', methods=['POST'])
def rename(battle_conversation_id):
    # 从请求体中获取新的名称
    data = request.get_json()
    new_name = data.get("new_name")

    if not new_name or not isinstance(new_name, str):
        return jsonify({"error": "Invalid or missing 'new_name' in request body"}), 400

    # 调用服务层的 rename 方法
    conversation_service = ConversationService()
    success = conversation_service.rename(battle_conversation_id, new_name)

    if success:
        return jsonify({"message": "Conversation renamed successfully"}), 200
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
    conversation_service = ConversationService()
    messageService=MessageService()
    conversation = conversation_service.get_conversation_by_id(battle_conversation_id)
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
                data = response.json().get("data", [])
                #data中的answer中如果有<think></think>的话，需要拆分将这个标签内的数据切到一个新的字段:think_content
                # 遍历每条消息，处理 answer 字段中的 <think> 标签
                for message in data:
                    # 分离思考和回复
                    answer = message.get("answer", "")
                    if "<think>" in answer and "</think>" in answer:
                        # 提取 <think> 标签内的内容
                        think_start = answer.find("<think>") + len("<think>")
                        think_end = answer.find("</think>")
                        think_content = answer[think_start:think_end].strip()
                        
                        # 提取 </think> 之后的内容
                        answer_after_think = answer[think_end + len("</think>"):].strip()
                        
                        # 更新 message 字段
                        message["think_content"] = None if think_content=="\n" or think_content=="\n\n" else think_content
                        message["answer"] = answer_after_think
                    else:
                        message["think_content"] =None
                    #公用字段修改
                    message["time_consumed_on_thinking"]=messageService.get_message_by_id(message.get("id")).time_consumed_on_thinking
                    message["stage"]=i
                    message_files=message.get("message_files", [])
                    # 精简文件信息
                    filtered_message_files = []
                    for message_file in message_files:
                        # 构造新的精简字段
                        filtered_message_files.append({
                            "filename": message_file.get("filename"),
                            "id": message_file.get("id"),
                            "size": message_file.get("size")
                        })
                    message["message_files"] = filtered_message_files
                    # 移除字段
                    fields_to_del=["error","feedback","retriever_resources","status","agent_thoughts"]
                    for field_to_del in fields_to_del:
                        if field_to_del in message:
                            del message[field_to_del]
                all_messages.extend(data)  # 将数据直接加入 all_messages
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
    #增加一个空的必须字段
    data["response_mode"]="streaming"
    data["inputs"]={}
    files=data.get("files")
    if files and files is not [] and isinstance(files[0],str):
        new_files=[]
        for file_id in files:
            file={
                "type": "document",
                "transfer_method": "local_file",
                "url": "",
                "upload_file_id": file_id
                }
            print(file)
            new_files.append(file)
        data["files"]=new_files
    if battle_conversation_id=="":
        session['user_stage'] = 1
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

    response = Response(stream_with_context(response_data), content_type='text/event-stream')
    # 添加 Cache-Control 和 Connection 头部
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    return response

#1. 想定内容提取与对话
def extract(data, battle_conversation_id):
    start_time=time.time()
    url = "http://123.57.244.236:35001//console/api/installed-apps/0e1144c1-658d-4b33-a180-939d92cd6008/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False, stream=True)

    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500

    # 返回流式响应
    return generate(response, battle_conversation_id, 1, current_app._get_current_object(),start_time)


#2. 总体作战目标
def goal(data,battle_conversation_id):
    start_time=time.time()
    url = "http://123.57.244.236:35001//console/api/installed-apps/4c97a3df-f2cc-4e3b-8ddf-6825f7fa1e85/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500
    # 返回流式响应
    return generate(response,battle_conversation_id,2, current_app._get_current_object(),start_time)

#3. 作战任务筹划
def task(data,battle_conversation_id):
    start_time=time.time()
    url = "http://123.57.244.236:35001//console/api/installed-apps/b09fdf1b-e143-4ab1-866a-6dbce4f35392/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500
    # 返回流式响应
    return generate(response,battle_conversation_id,3, current_app._get_current_object(),start_time)


#4. 作战行动方案
def solution(data,battle_conversation_id):
    start_time=time.time()
    url = "http://123.57.244.236:35001//console/api/installed-apps/cbc8823f-3d4d-47f8-a84c-dd3ae8f03576/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500
    # 返回流式响应
    return generate(response,battle_conversation_id,4, current_app._get_current_object(),start_time)

#加工来自至慧工作流的响应

def generate(response, battle_conversation_id, stage, app, start_time):
    messageService=MessageService()
    buffer = ""
    first_conversation_id_found = False
    is_think_content = False
    is_think_message=False
    message_is_saved=False
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            try:
                # 将字节数据解码为字符串
                decoded_chunk = chunk.decode('utf-8')
                buffer += decoded_chunk

                # 检查缓冲区中是否有完整的 JSON 对象
                while buffer:
                    # 查找第一个完整的 JSON 对象（以 "data: " 开头）
                    start_index = buffer.find("data: {")
                    if start_index == -1:
                        break  # 没有找到完整的 JSON 对象，继续等待数据

                    # 提取从 "data: {" 开始的部分
                    buffer = buffer[start_index:]
                    end_index = buffer.find("}\n\n")  # 查找 JSON 对象的结束位置
                    if end_index == -1:
                        break  # 没有找到完整的 JSON 对象，继续等待数据

                    # 提取完整的 JSON 字符串
                    json_str = buffer[:end_index + 1]
                    buffer = buffer[end_index + 2:]  # 移除已处理的部分

                    try:
                        # 解析 JSON 数据
                        parsed_data = json.loads(json_str[len("data: "):])
                    except json.JSONDecodeError as e:
                        print(f"JSON 解析失败: {e}, 数据: {json_str}")
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

                    # 处理消息内容
                    if parsed_data.get("event") == "message":
                        if parsed_data.get("answer") == "<think>":
                            is_think_content = True
                            is_think_message=True
                            parsed_data["is_think_content"] = True
                        elif parsed_data.get("answer") == "</think>":
                            is_think_content = False
                            parsed_data["is_think_content"] = True
                        else:
                            parsed_data["is_think_content"] = is_think_content

                        # 计算耗时
                        parsed_data["time_consumed"] = f"{time.time() - start_time:.1f}"
                        #parsed_data["time_consumed"] = round(time.time() - start_time, 1)
                        # 是思考消息，且刚思考结束的第一次，需要保存一条消息
                        if not message_is_saved:
                            if is_think_message and is_think_content is False:
                                messageService.save_messages(parsed_data.get("message_id"),is_think_message,parsed_data["time_consumed"])
                                is_think_message=False
                            else:
                                messageService.save_messages(parsed_data.get("message_id"),is_think_message,parsed_data["time_consumed"])
                            message_is_saved=True
                        # 精简字段
                        parsed_data = {
                            "event": parsed_data.get("event"),
                            "conversation_id": parsed_data.get("conversation_id"),
                            "message_id": parsed_data.get("message_id"),
                            "answer": parsed_data.get("answer"),
                            "battle_conversation_id": parsed_data.get("battle_conversation_id"),
                            "is_think_content": parsed_data.get("is_think_content"),
                            "time_consumed": parsed_data.get("time_consumed")
                        }

                        # 转换为 JSON 字符串并加上 data: 前缀
                        yield f"data: {json.dumps(parsed_data)}\n\n"
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
    
