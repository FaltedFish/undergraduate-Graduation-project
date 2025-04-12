import json
import os
import pty
import subprocess
from time import sleep

from flask import Flask, request, jsonify
import logging

import service

app = Flask(__name__)
# 创建日志处理器
handler = logging.StreamHandler()

# 创建日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 将日志处理器添加到 Flask 的默认日志记录器
app.logger.addHandler(handler)

# 设置日志级别
app.logger.setLevel(logging.DEBUG)

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

@app.route('/create', methods=['POST'])
def create():
    # 获取请求体中的JSON数据
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No JSON data received'}), 400
        # 将数据写入JSON文件
    with open("mininet/topo.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # 执行 make restart 命令
    app_service.create(app.logger,data)

    return jsonify({'code': '0'}), 200

@app.route('/hosts', methods=['get'])
def get_hosts():
    return json.dumps(app_service.get_hosts()),200

@app.route('/switches', methods=['get'])
def get_switches():
    return json.dumps(app_service.get_switches()),200

@app.route('/rtt', methods=['get'])
def get_rtt():
    server = request.args.get('server', type=str)
    client = request.args.get('client', type=str)
    return app_service.ping(client,server),200

@app.route('/bandwidth',methods=['get'])
def get_bandwidth():
    server = request.args.get('server', type=str)
    client = request.args.get('client', type=str)
    return app_service.iperf( client, server),200

@app.route('/srv6/insert',methods=['post'])
def insert_srv6():
    data = request.get_json()
    app_service.onos_insert(data["device"],data["relay"],data["destination"],app.logger)
    return json.dumps({}),200

@app.route('/onos/query',methods=['get'])
def onos_query():
    device = request.args.get('device', type=str)
    return json.dumps(app_service.onos_query(device)),200

@app.route('/onos/delete',methods=['post'])
def onos_delete():
    device = request.args.get('device', type=str)
    app_service.onos_delete(device)
    return json.dumps({}),200

app_service =None

if __name__ == '__main__':
    app_service = service.Service()
    app.run(host='0.0.0.0',port=5001)
