# app.py
from flask import Flask
from flask_cors import CORS
from api import api
from click import argument
from sqlalchemy import text
from model.models import db as database
from flask_redis import FlaskRedis
from dotenv import load_dotenv
import os
# 加载 .env 文件中的环境变量
load_dotenv()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['REDIS_URL'] = os.getenv("REDIS_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # 禁用不必要的警告
app.config['SESSION_COOKIE_SECURE'] = False  # 允许 HTTP 传输 cookie
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止 JavaScript 访问 cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 允许部分跨站请求携带 cookie
CORS(app)
app.secret_key = "ae5d0bf8ce5303689894297c1658e538a5b2a83de104c7f7254391ce319b2e22"
# 绑定 db 对象到 Flask 应用
database.init_app(app)
redis_client = FlaskRedis(app)
app.register_blueprint(api)


def initialize_database():
    """初始化数据库表结构"""
    with app.app_context():
        database.create_all()
    print("Database tables created successfully.")


if __name__ == '__main__':
    initialize_database()
    app.run(host="0.0.0.0",port=5007,debug=True)

