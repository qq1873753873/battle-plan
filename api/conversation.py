from flask_cors import cross_origin
from . import api  # 导入蓝图
from flask import Response, request, jsonify, app, stream_with_context
import os
from datetime import datetime
import requests

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


#想定内容提取与对话
@api.route('/extract', methods=['POST'])
def extract():
    # 从前端请求中获取 JSON 数据
    data = request.json
    if not data:
        return {"error": "No data provided"}, 400
    url = "http://123.57.244.236:35001//console/api/installed-apps/c5496d3f-2be2-4cdd-97cd-6807625ed3f6/chat-messages"
    # 发送 POST 请求
    response = requests.post(url, json=data, verify=False,stream=True)
    # 检查目标服务的响应状态码
    if response.status_code != 200:
        return {"error": "Failed to forward request", "status_code": response.status_code}, 500
    return Response(response)


# 总体作战目标
@api.route('/chat', methods=['POST','GET'])
def chat():
    user_input=None
    if request.method == 'POST' and request.is_json:
        user_input = request.json.get('user_input', user_input)  # 获取 JSON 中的 'user_input'
    # 处理 GET 请求中的查询参数
    if request.method == 'GET':
        user_input = request.args.get('user_input', user_input)  # 获取 GET 请求中的 'user_input'
    return Response(stream_with_context((user_input)), content_type='text/plain; charset=utf-8')


#作战任务筹划

#作战行动方案