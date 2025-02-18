from . import api  # 导入蓝图
from flask import Response

import requests

# 健康检查接口
@api.route('/health', methods=['GET','POST'])
def health_check():
    response="healthy"
    return Response(response)