import json
from flask_cors import cross_origin
import uuid
from dtos.response_utils import *
from services.conversation_service import ConversationService
from services.message_service import MessageService
from . import api  
from flask import Response, request, jsonify, app, stream_with_context,current_app
import os
from datetime import datetime
import requests
from model.models import db,Conversation,Message
import time
from model.gantt_model import GanttData
from openai import OpenAI

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
def messages(separator="\n---\n"):
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
           "http://123.57.244.236:35001//console/api/installed-apps/b09fdf1b-e143-4ab1-866a-6dbce4f35392/messages"
           #"http://123.57.244.236:35001//console/api/installed-apps/cbc8823f-3d4d-47f8-a84c-dd3ae8f03576/messages"  
    ]

    # 存储所有消息记录
    all_messages=MessagesResponse(battle_conversation_id=battle_conversation_id)
    # 遍历前三个依赖至慧的 id1, id2, id3，分别调用外部 API
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
                    message_response=MessageResponse()
                    message_response.created_at=message.get("created_at")
                    # 处理拼接last_answer和query导致的query需要分割的问题
                    query_parts=message.get("query").split(separator)
                    if len(query_parts)>=2:
                        message_response.query=query_parts[-1]
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
                        message_response.think_content = None if think_content=="\n" or think_content=="\n\n" else think_content
                        message_response.answer = answer_after_think
                    else:
                        message_response.think_content =None
                    #公用字段修改
                    message_with_time=messageService.get_message_by_id(message.get("id"))
                    message_response.time_consumed_on_thinking=message_with_time.time_consumed_on_thinking if message_with_time else 10.0
                    message_response.stage=i
                    message_response.id=message.get("id")
                    message_files=message.get("message_files", [])             
                    # 精简文件信息
                    for message_file in message_files:
                        message_response.message_files.append(MessageFile(
                            filename=message_file.get("filename"),
                            id=message_file.get("id"),
                            size=message_file.get("size")
                        ))
                    all_messages.messages.append(message_response) 
            else:
                print(f"Failed to fetch messages for id{i}: {response.status_code}")
        except Exception as e:
            print(f"Error fetching messages for id{i}: {e}")
    #TODO: 根据当前的battleid查第4步的消息
    message_ganta=messageService.get_messages_by_battle_conversation_id(battle_conversation_id)
    all_messages.messages.extend(message_ganta)
    # 返回合并后的结果
    return jsonify(all_messages.model_dump())

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
            new_files.append(file)
        data["files"]=new_files
    if battle_conversation_id=="":
        battle_conversation_id=str(uuid.uuid4())
    if not data:
        error_message = {
                "error": "No data provided",
                "status_code": 400
            }
        return generate_single_stream_response(error_message)
    next_stage,changed=get_next_stage(query=query,battle_conversation_id=battle_conversation_id)
    #如果改变工作流了，就清空这个工作流的两个字段，避免报错
    if changed:
        data["conversation_id"]=None
        data["parent_message_id"]=None
    if next_stage==1:
        if data.get('parent_message_id')=="": #防止前端输成"",会报错
            data["parent_message_id"]=None 
        print(f"当前阶段:1")
        response_data = extract(data,battle_conversation_id)
    elif next_stage==2:
        print(f"当前阶段:2")
        response_data = goal(data,battle_conversation_id)
    elif next_stage==3:
        print(f"当前阶段:3")
        response_data = task(data,battle_conversation_id) 
    elif next_stage==4:
        print(f"当前阶段:4")
        response_data = solution(data,battle_conversation_id)    
    response = Response(stream_with_context(response_data), content_type='text/event-stream')
    # 添加 Cache-Control 和 Connection 头部
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    return response

#停止回复
@api.route('/stop', methods=['POST'])
def stop():
    data = request.json
    battle_conversation_id = data.get('battle_conversation_id')  # 获取任务 ID
    redis_client=current_app.extensions['redis']
    if battle_conversation_id:
        redis_client.set(f'stop:{battle_conversation_id}',"true")#设置为应该停止
        #TODO: 统一返回消息格式
        return jsonify({"message": f"Stop signal sent for battle_conversation_id: {battle_conversation_id}"}), 200
    else:
        return jsonify({"error": "Missing battle_conversation_id"}), 400
    
#1. 想定内容提取与对话
def extract(data, battle_conversation_id):
    #第一阶段不需要拼接，因为都在工作流一的上下文中
    #data['query']=data.get('last_answer','')+data.get('query','')
    start_time=time.time()
    url = "http://ty1.puhuacloud.com:20015//console/api/installed-apps/0e1144c1-658d-4b33-a180-939d92cd6008/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False, stream=True)

    # 检查目标服务的响应状态码
    if response.status_code != 200:
        error_message = {
                "error": "Failed to forward request",
                "status_code": response.status_code
            }
        print(f'"error": "Failed to forward request", "status_code": {response.status_code}')
        return generate_single_stream_response(error_message)
    battle_conversation_name=data['query'][:10] if data['query'] and data['query'] !="" else "New Conversation"
    # 返回流式响应
    return generate(response, battle_conversation_id, 1, current_app._get_current_object(),start_time,battle_conversation_name)

#2. 总体作战目标
def goal(data,battle_conversation_id,separator="\n---\n"):
    data['query']=data.get('last_answer','')+separator+data.get('query','')
    start_time=time.time()
    url = "http://ty1.puhuacloud.com:20015//console/api/installed-apps/4c97a3df-f2cc-4e3b-8ddf-6825f7fa1e85/chat-messages"
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    # 如果是带着上次的conversation和message参数请求访问工作流，会报错404，清空这两个参数重新访问
    if response.status_code ==404:
        data["conversation_id"]=None
        data["parent_message_id"]=None
        response = requests.post(url, json=data, verify=False,stream=True)
    if response.status_code != 200:
        error_message = {
                "error": "Failed to forward request",
                "status_code": response.status_code
            }
        print(f'"error": "Failed to forward request", "status_code": {response.status_code}')
        return generate_single_stream_response(error_message)

    # 返回流式响应
    return generate(response,battle_conversation_id,2, current_app._get_current_object(),start_time)

#3. 作战任务筹划
def task(data,battle_conversation_id,separator="\n---\n"):
    data['query']=data.get('last_answer','')+separator+data.get('query','')
    start_time=time.time()
    url = "http://ty1.puhuacloud.com:20015//console/api/installed-apps/b09fdf1b-e143-4ab1-866a-6dbce4f35392/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    if response.status_code ==404:
        data["conversation_id"]=None
        data["parent_message_id"]=None
        response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        error_message = {
                "error": "Failed to forward request",
                "status_code": response.status_code
            }
        print(f'"error": "Failed to forward request", "status_code": {response.status_code}')
        return generate_single_stream_response(error_message)
    # 返回流式响应
    return generate(response,battle_conversation_id,3, current_app._get_current_object(),start_time)


#4. 作战行动方案
def solution(data,battle_conversation_id):
    #当前不是流式，所以判断两次：开始前和返回前
    redis_client=current_app.extensions['redis']
    if redis_client.get(f'stop:{battle_conversation_id}')==b"true":
        redis_client.set(f'stop:{battle_conversation_id}',"false")
        return
    client = OpenAI(
        api_key="EMPTY",
        base_url="http://123.57.244.236:1740/v1"
    )
    completion = client.chat.completions.create(
        model="deepseek-14B",
        messages=[
            {
                "role": "user",
                "content": data.get('last_answer','')+data.get('query',''),
            }
        ],
        extra_body={"guided_json": GanttData.model_json_schema()},
        #stream=True
    )
    #当前不是流式，所以判断两次：开始前和返回前
    if redis_client.get(f'stop:{battle_conversation_id}')==b"true":
        redis_client.set(f'stop:{battle_conversation_id}',"false")
        return
    model_response = completion.choices[0].message.content

    # 生成唯一的 message_id（这里使用 UUID）
    message_id = str(uuid.uuid4())

    # 如果 model_response 是字典或者其他复杂类型，将其转换为 JSON 字符串
    model_response_str = json.dumps(model_response, ensure_ascii=False) if isinstance(model_response, (dict, list)) else str(model_response)


    streamSponse=StreamResponse(
        event=Event.MESSAGE,
        conversation_id= str(uuid.uuid4()), 
        message_id=message_id,
        answer=f'```json\n{model_response_str}\n```\n\n',
        battle_conversation_id=battle_conversation_id,
        is_think_content=False,
        time_consumed= 0,
        error=None,
        status_code=200
    )
    messageService=MessageService()
    messageService.save_message(
        id=message_id,
        battle_conversation_id=battle_conversation_id,
        is_think_message=False,
        think_content=None,
        time_consumed_on_thinking=0,
        query=data.get("query"),
        answer=f'```json\n{model_response_str}\n```\n\n',
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    # 格式化返回的字符串，符合你需要的格式
    yield streamSponse.to_stream_format()
    return

#加工来自至慧工作流的响应

def generate(response, battle_conversation_id, stage, app, start_time,battle_conversation_name="New Conversation"):
    messageService=MessageService()
    buffer = ""
    first_conversation_id_found = False
    is_think_content = False
    is_think_message=False
    message_is_saved=False
    stop_urls_pre=[
        "http://ty1.puhuacloud.com:20015//console/api/installed-apps/0e1144c1-658d-4b33-a180-939d92cd6008/chat-messages/",
        "http://ty1.puhuacloud.com:20015//console/api/installed-apps/4c97a3df-f2cc-4e3b-8ddf-6825f7fa1e85/chat-messages/",
        "http://ty1.puhuacloud.com:20015//console/api/installed-apps/b09fdf1b-e143-4ab1-866a-6dbce4f35392/chat-messages/",
        "",
    ]
    redis_client=current_app.extensions['redis']
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
                                battle_conversation_id, conversation_id, stage,battle_conversation_name
                            )
                        first_conversation_id_found = True  # 设置标志变量
                    # 将 battle_conversation_id 添加到顶层
                    parsed_data["battle_conversation_id"] = battle_conversation_id

                    # 处理消息内容
                    if parsed_data.get("event") == Event.MESSAGE.value:
                        if parsed_data.get("answer") == "<think>":
                            is_think_content = True
                            is_think_message=True
                            parsed_data["is_think_content"] = True
                        elif parsed_data.get("answer") == "</think>":
                            is_think_content = False
                            parsed_data["is_think_content"] = True
                        else:
                            parsed_data["is_think_content"] = is_think_content
                        parsed_data["time_consumed"] = round(time.time() - start_time, 1)
                        # 是思考消息，且刚思考结束的第一次，需要保存一条消息
                        if not message_is_saved:
                            if is_think_message and is_think_content is False:
                                messageService.save_messages(parsed_data.get("message_id"),is_think_message,parsed_data["time_consumed"])
                                is_think_message=False
                            else:
                                messageService.save_messages(parsed_data.get("message_id"),is_think_message,parsed_data["time_consumed"])
                            message_is_saved=True
                        taskId=parsed_data.get("task_id")
                        streamResponse=StreamResponse(
                            event=parsed_data.get("event"),
                            conversation_id=parsed_data.get("conversation_id"),
                            message_id=parsed_data.get("message_id"),
                            answer=parsed_data.get("answer"),
                            battle_conversation_id=battle_conversation_id,
                            is_think_content=parsed_data.get("is_think_content"),
                            time_consumed= parsed_data.get("time_consumed"),
                            stage=stage,
                            error= None,
                            status_code=200
                        )
                        # 判断是否需要停止
                        if redis_client.get(f'stop:{battle_conversation_id}')==b"true":
                            #首先调用至慧的stop接口停止生成，然后停止标志位变为false
                            stop_url=stop_urls_pre[stage-1]+str(taskId)+'/stop'
                            print(f'stop-URL:{stop_url}')
                            response = requests.post(stop_url,verify=False,stream=False)
                            if response.status_code==200:
                                print(f"{battle_conversation_id}停止成功")
                                redis_client.set(f'stop:{battle_conversation_id}',"false")
                            else :
                                print(f"{battle_conversation_id}停止失败:{response.status_code}")#下次重试
                        # 转换为 JSON 字符串并加上 data: 前缀
                        yield streamResponse.to_stream_format()
                    elif parsed_data.get("event") == Event.ERROR.value:
                        streamResponse=StreamResponse(
                            error= parsed_data.get("message"),
                            status_code=404
                        )
                        #return generate_single_stream_response(parsed_data)
                        yield streamResponse.to_stream_format()
                        return
                    elif parsed_data.get("event")==Event.MESSAGE_END.value and redis_client.get(f'stop:{battle_conversation_id}'):
                        #TODO:如果不加message_end消息的话，就什么都不用动，加的话，只要碰到end，都需要返回一条消息才可以。
                        return
            except UnicodeDecodeError:
                # 如果解码失败，跳过该块
                continue


#根据用户查询判断是否进入下一阶段
def get_next_stage(query,battle_conversation_id):
    conversationService=ConversationService()
    battle_conversation=conversationService.get_conversation_by_id(battle_conversation_id)
    #如果返回为True，需要清空前端传回的conversationid和messageid
    if battle_conversation is None:
        return 1,False
    ids = [battle_conversation.id1, battle_conversation.id2, battle_conversation.id3, battle_conversation.id4]
    if ids[3] is not None:
        return 4,False
    elif ids[3] is None and ids[2] is not None:
        if query == "审批通过，请制定详细作战行动方案" or "作战行动方案" in query or "方案" in query:
            return 4,True
        else:
            return 3,False
    elif ids[2] is None and ids[1] is not None:
        if query == "审批通过，请制定作战任务" or "作战任务" in query or "任务" in query:
            return 3,True
        else:
            return 2,False
    elif ids[1] is None and ids[0] is not None:
        if query == "请你思考一下向我汇报" or "作战目标" in query or "目标" in query:
            return 2,True
        else:
            return 1,False
    else:
        return 1,False

    
def generate_single_stream_response(message):
    """
    生成一个符合 SSE 格式的错误响应。
    
    :param error_message: dict - 错误信息
    :return: generator - 流式响应生成器
    """
    def single_stream():
        yield f"data: {message}\n\n".encode("utf-8")  # 确保返回的是字节类型
    return single_stream()