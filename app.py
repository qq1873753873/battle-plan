# app.py
from flask import Flask
from flask_cors import CORS
from api import api
from click import argument
from sqlalchemy import text
from model.models import db as database

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:difyai123456@localhost:5432/battleplan"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False  # 禁用不必要的警告
app.register_blueprint(api)
# 绑定 db 对象到 Flask 应用
database.init_app(app)
CORS(app)

def initialize_database():
    """初始化数据库表结构"""
    with app.app_context():
        database.create_all()
    print("Database tables created successfully.")


if __name__ == '__main__':
    initialize_database()
    app.run(host="0.0.0.0",port=5007,debug=True)

