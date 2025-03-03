import uuid
from . import api  # 导入蓝图
from flask import Response, stream_with_context
from dtos.response_utils import *
import requests
from flask import current_app
# 健康检查接口
@api.route('/health', methods=['GET','POST'])
def health_check():
    response="healthy"
    return Response(response)

@api.route('/test_redis', methods=['GET','POST'])
def test():
    redis_client = current_app.extensions['redis']
    redis_client.set('key', 'value')
    response="healthy"
    return Response(response)

@api.route('/test_response', methods=['GET','POST'])
def test1():
    def generate():
        for i in range(100):
            yield StreamResponse(event=Event.MESSAGE,message_id=str(uuid.uuid4())).to_stream_format()
            if i==2:return
    return Response(stream_with_context(generate()), content_type='text/event-stream')


@api.route('/test_api_response',methods=['GET'])
def test2():
    # return  ApiResponse(code=200,message="12333",data=None)
    return Response(status=200,response= [ "http://123.57.244.236:35001//console/api/installed-apps/0e1144c1-658d-4b33-a180-939d92cd6008/messages",
           "http://123.57.244.236:35001//console/api/installed-apps/4c97a3df-f2cc-4e3b-8ddf-6825f7fa1e85/messages",
           "http://123.57.244.236:35001//console/api/installed-apps/b09fdf1b-e143-4ab1-866a-6dbce4f35392/messages"
           #"http://123.57.244.236:35001//console/api/installed-apps/cbc8823f-3d4d-47f8-a84c-dd3ae8f03576/messages"  
    ]
)