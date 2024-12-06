# 接口8012：生成知识点后置关系

# 回调返回数据

# 后置知识点生成逻辑重写

# 后置只取下一章节同级别知识点

# 前置只取上一章节同级别知识点，并且与后置 相反过来 得到的前置知识点做交集

# （需要Dify新建提取前置知识点的工作流，编写提示词）

import threading
import requests
from flask import Flask, request, jsonify
import time
from urllib.parse import urlparse
import json
import re
import os
from docx import Document

app = Flask(__name__)



def extract_level3_knowledge(query,content):  # 提取structure中所有的三级知识点的后置关系
    
    api_key = 'app-1AygnEJNMtySajNAz2E00EZx'
    url = f'http://188.18.18.106:5001/v1/completion-messages'

    content = ",".join(content)

    # 请求头部
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # 请求体数据，替换'name'的值为你想要的知识库名称
    data = {
        "inputs": {"query": query, "content": content},
        "response_mode": "blocking",
        "user": "abc-123"
    }

    # 发送POST请求
    response = requests.post(url, headers=headers, json=data)

    # 打印响应内容
    answer = json.loads(response.text).get("answer")
    
    return answer


def process_and_callback(rp_id, rejsonstr, authorization_token, callback_url):
    print(f"rpid =  {rp_id}...")
    with app.app_context():  # 创建一个应用上下文

        # 尝试解析成 JSON，查看是否成功
        try:
            structure = json.loads(rejsonstr)
            print("JSON 解析成功:")
        except json.JSONDecodeError as e:
            print("JSON 解析失败:", e)


        # 初始化字典来存储不同level的名称
        last_knowledge_points_by_level1 = {}

        # 递归函数，用于提取每个level1中最后一级的知识点
        def collect_last_knowledge_points(node, level1_name):
            # 检查节点是否有子节点
            if 'child' in node and node['child']:
                # 如果有子节点，递归每个子节点
                for child in node['child']:
                    collect_last_knowledge_points(child, level1_name)
            else:
                # 如果没有子节点，说明是最后一级知识点
                if level1_name not in last_knowledge_points_by_level1:
                    last_knowledge_points_by_level1[level1_name] = []
                last_knowledge_points_by_level1[level1_name].append(node)
        
        # 提取每个level1的最后一级知识点
        for node1 in structure['nodes']:
            # print(f"node1: {node1['name']}")
            collect_last_knowledge_points(node1, node1['name'])

        
        # 遍历last_knowledge_points_by_level1字典，调用API提取后置关系
        level1_names = list(last_knowledge_points_by_level1.keys())
        value = list(last_knowledge_points_by_level1.values())

        # print(f"level1_names: {level1_names}")
        # print(f"value: {value}")

        for i in range(len(level1_names) - 1):
            current_level1 = level1_names[i]
            next_level1 = level1_names[i + 1]

            # 获取当前和下一个level1的最后一级知识点
            current_last_points = last_knowledge_points_by_level1[current_level1]
            next_last_points = [point['name'] for point in last_knowledge_points_by_level1[next_level1]]

            # print(f"当前最后一级知识点：{current_last_points}")
            # print(f"下一个最后一级知识点：{next_last_points}")

            for point in current_last_points:
                # 提取并更新后置知识点
                result = extract_level3_knowledge(point["name"], next_last_points)
                # 新建空列表，保存去除不在names_by_level[3]中的元素
                res = []

                # 添加异常处理
                try :
                    print(result)
                    for a in result.split(';'):
                        # 将a添加到node3的后置关系列表中,以分号分割
                        res.append(a)
                    # 取出res2所有元素修改为";"间隔的字符串   统一格式，方便后端处理
                    point["postponement"] = ";".join(res)
                    print(f"添加：{point['postponement']} 到 {point['name']} 的后置关系")
                except Exception as e:
                    print(f"提取后置关系时出错：{e}")



        # 向回调接口发送内容
        callback_data = {
                "retJsonStr":structure,
                "rpId":rp_id,
            }
            
        headers = {
                'AuthorizationForPlatform': authorization_token
            }

        # 发送数据到回调接口
        response = requests.post(callback_url, json=callback_data,headers=headers)
        print("发送数据到回调接口")

        # 检查回调接口响应
        if response.status_code == 200:
            print("回调接口响应成功")
        else:
            print("回调接口响应失败")



@app.route('/postponement', methods=['POST'])
def receive_knowledge():
    # 检查必填字段是否存在
    required_fields = ['rpId', 'retJsonStr','AuthorizationForPlatform', 'callBackUrl']
    for field in required_fields:
        if field not in request.form:
            return jsonify({'code': 5, 'msg': f'Missing required field: {field}'})

    # 获取请求参数
    rp_id = request.form['rpId']
    print(f"收到rpId：{rp_id}")
    rejsonstr = request.form['retJsonStr']
    print(f"收到字符串：{rejsonstr}")
    authorization_token = request.form['AuthorizationForPlatform']
    print(f"收到token：{authorization_token}")
    callback_url = request.form['callBackUrl']
    print(f"收到回调接口：{callback_url}")

    # 定义一个回调函数（接收到的字符串）

            # 剥离出所有三级知识点
            # 将需要提取后置的知识点和所有知识点一起发给大模型
            # 模型生成后置知识点
            # 后置知识点添加到对应的postponement位置

        # 返回知识点数据


    # 启动新线程处理请求
    threading.Thread(target=process_and_callback, args=(rp_id, rejsonstr, authorization_token, callback_url)).start()

    # 立即返回状态告诉请求方已经成功接收到请求
    return jsonify({'code': 0, 'rpId': rp_id, 'msg': 'Request received, processing...'})



if __name__ == '__main__':
    app.run(port=8012,host='0.0.0.0')  # 运行在8012端口
