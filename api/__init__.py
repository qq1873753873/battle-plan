from flask import Blueprint

# 定义蓝图
api = Blueprint('api', __name__)

# 导入并注册视图
from .conversation import *
from .test import *