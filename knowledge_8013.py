# 接口：8013

# 接口：知识点关联PPT关联(带id)
# 回调返回数据

# 增强健壮性

# 上传文件 -> 查看状态 -> 提取三级知识点 -> 遍历三级知识点 -> 命中PPT -> 删除PPT

# 图片(img)，视频字幕(string)，传进来需要保存为文件

# docx，pptx，pdf，txt，json，csv，xlsx

# 排除多线程影响,目前只支持两个重复文档

# 添加PPT页码


import requests
import json
import re
import os
from docx import Document
import time
import threading
from flask import Flask, request, jsonify
from urllib.parse import urlparse
# 使用Gradio Client进行OCR识别
from gradio_client import Client, file

app = Flask(__name__)


dataset_id = '26289696-27b7-4518-91f4-adc10a794d65'
api_key = 'dataset-19HBiTUzbWufJIC7lc0RUiRZ'                # 数据库的API-Key
base_url = 'http://188.18.18.106:5001/v1/datasets/'

app_api_key = 'app-0Igm882WufEJhRQkD8Qh8CU7'                # 工作流的API-Key
url = f'http://188.18.18.106:5001/v1/workflows/run'

def perform_ocr(image_path):        # 图片进行OCR识别
    client = Client("http://188.18.18.107:8014/")
    result = client.predict(
        image_obj=file(image_path),
        api_name="/handle_image"
    )
    text = result[0]  # 假设返回的文本在结果元组的第一个位置
    return text

def upload_file(dataset_id,file_path,file_name):   # 上传文件到模型知识库

    url = f'{base_url}{dataset_id}/document/create_by_file'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    data = {
        'data': (
            None,
            '{"indexing_technique": "high_quality", "process_rule": {"mode": "automatic", "rules": {}}}',
            'text/plain'
        )
    }
    files = {
        'file': (file_name, open(file_path, 'rb'), 'text/plain')  
    }
    response = requests.post(url, headers=headers, files=files, data=data)
    if response.status_code == 200:
        batch_id = json.loads(response.text)["batch"]
        document_id = json.loads(response.text)["document"].get("id")
        print(f"[{file_name}]上传成功\ndocument_id:{document_id}\nbatch ID:{batch_id}\n向量化处理中..........")
        return batch_id,document_id
    else:
        print('Failed to upload file')
        return None

def check_processing_status(dataset_id, batch_id):   # 查看上传文件处理状态
    url = f'{base_url}{dataset_id}/documents/{batch_id}/indexing-status'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            status_data = json.loads(response.text)
            for document in status_data['data']:
                if document['indexing_status'] == 'completed':
                    print("处理完成,文档总分段数:",status_data["data"][0]["total_segments"])
                    return status_data
                else:
                    print(f"正在处理中,处理状态：{document['indexing_status']}，处理进度：{document['completed_segments']}/{document['total_segments']}")
                    
        else:
            print('Failed to get processing status')
        time.sleep(5)  # Wait for 30 seconds before checking again

def delete_file(dataset_id, document_id):   # 删除文件
    url = f'{base_url}{dataset_id}/documents/{document_id}'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"[{document_id}]删除成功")
        # 打印响应内容和状态码，以便调试
        # print('Status Code:', response.status_code)
        # print('Response:', response.text)
    else:
        print('Failed to delete file')
    
def process_and_callback(rpId,retjsonstr,authorization_token, callback_url, file_path,file_name):  # score > 0.96
    with app.app_context():
        # 上传文件 -> 查看状态 -> 提取三级知识点 -> 遍历三级知识点 -> 命中PPT -> 删除PPT

        batch_id,document_id = upload_file(dataset_id,file_path,file_name)

        check_processing_status(dataset_id, batch_id)

        # 将retjsonstr中true全部替换为"ture"，加上双引号
        retjsonstr = retjsonstr.replace("true", '"true"')
        retjsonstr = retjsonstr.replace("null", '"null"')
        # print(retjsonstr)
        # 将retjsonstr转换为字典
        retjsonstr = json.loads(retjsonstr)

        data = retjsonstr.get("data")

        # 初始化字典来按级别存储节点的zsdName和id
        nodes_info_by_level = {1: [], 2: [], 3: []}

        # 定义一个递归函数来遍历整个数据结构并按级别收集节点的zsdName和id
        def collect_nodes_info_by_level(node):
            level = node['level']
            # 根据节点的level将zsdName和id存储到对应的列表中
            if level in nodes_info_by_level:
                nodes_info_by_level[level].append((node['zsdName'], node['id']))
            
            # 如果存在子节点，递归调用函数处理每个子节点
            if 'childs' in node:
                for child in node['childs']:
                    collect_nodes_info_by_level(child)

        # 遍历数据列表并收集信息
        for node in data:
            collect_nodes_info_by_level(node)

        knowlwdge_list = {}
        for querys in nodes_info_by_level[3]:
            query = querys[0]

            # 请求头部
            headers = {
                'Authorization': f'Bearer {app_api_key}',
                'Content-Type': 'application/json'
            }

            # 请求体数据，替换'name'的值为你想要的知识库名称
            data = {
                "inputs": {"content": query},
                "response_mode": "blocking",
                "user": "abc-123"
            }

            # 发送POST请求
            response = requests.post(url, headers=headers, json=data)

            results = response.json().get('data').get('outputs').get('result')

            for result in results:

                # 打印响应内容 
                try:
                    # 这里只取了第一个result / 外面for循环取了所有result
                    score = result.get('metadata').get('score')
                
                except:
                    score = 0
                    print("异常")

                try:
                    document_name = result.get('metadata').get('document_name')
                    page = result.get('metadata').get('segment_position')
                    

                except:
                    document_name = "None"
                    print("异常")
                if score > 0.96:
                    if document_name == file_name:
                        if query not in knowlwdge_list.values():
                            print(f" {query} 命中，添加到知识库, 页码：{page}")
                            # 添加到字典
                            knowlwdge_list[querys[1]] = query
                        else:
                            print(f"<{query}> 重复")
                    else:
                        print(f" {query} 命中，但 <{document_name}> 不是当前任务")
                    
                else:
                    print(f"<{document_name}> 与知识点关联度极低: {query}")

        print(knowlwdge_list)

        # 将knowlwdge_list转换为字符串,如果后端有需要的话
        # knowlwdge_list = str(knowlwdge_list)
        delete_file(dataset_id, document_id)


        # 向回调接口发送内容
        callback_data = {
                "retJsonStr":knowlwdge_list,
                "rpId":rpId,
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

def process_and_callback2(rpId,retjsonstr,authorization_token, callback_url, file_path,file_name):  # score > 0.8
    with app.app_context():
        # 上传文件 -> 查看状态 -> 提取三级知识点 -> 遍历三级知识点 -> 命中PPT -> 删除PPT

        batch_id,document_id = upload_file(dataset_id,file_path,file_name)

        check_processing_status(dataset_id, batch_id)

        # 将retjsonstr中true全部替换为"ture"，加上双引号
        retjsonstr = retjsonstr.replace("true", '"true"')
        retjsonstr = retjsonstr.replace("null", '"null"')
        # print(retjsonstr)
        # 将retjsonstr转换为字典
        retjsonstr = json.loads(retjsonstr)

        data = retjsonstr.get("data")

        # 初始化字典来按级别存储节点的zsdName和id
        nodes_info_by_level = {1: [], 2: [], 3: []}

        # 定义一个递归函数来遍历整个数据结构并按级别收集节点的zsdName和id
        def collect_nodes_info_by_level(node):
            level = node['level']
            # 根据节点的level将zsdName和id存储到对应的列表中
            if level in nodes_info_by_level:
                nodes_info_by_level[level].append((node['zsdName'], node['id']))
            
            # 如果存在子节点，递归调用函数处理每个子节点
            if 'childs' in node:
                for child in node['childs']:
                    collect_nodes_info_by_level(child)

        # 遍历数据列表并收集信息
        for node in data:
            collect_nodes_info_by_level(node)

        knowlwdge_list = {}
        for querys in nodes_info_by_level[3]:
            query = querys[0]

            # 请求头部
            headers = {
                'Authorization': f'Bearer {app_api_key}',
                'Content-Type': 'application/json'
            }

            # 请求体数据，替换'name'的值为你想要的知识库名称
            data = {
                "inputs": {"content": query},
                "response_mode": "blocking",
                "user": "abc-123"
            }

            # 发送POST请求
            response = requests.post(url, headers=headers, json=data)

            results = response.json().get('data').get('outputs').get('result')

            for result in results:

                # 打印响应内容 
                try:
                    
                    score = result.get('metadata').get('score')
                
                except:
                    score = 0
                    print("异常")

                try:
                    document_name = result.get('metadata').get('document_name')
                    page = result.get('metadata').get('segment_position')

                except:
                    document_name = "None"
                    print("异常")
                if score > 0.8:
                    if document_name == file_name:
                        if query not in knowlwdge_list.values():
                            print(f" {query}命中，添加到知识库, 页码：{page}")
                            # 添加到字典
                            knowlwdge_list[querys[1]] = query
                        else:
                            print(f"<{query}> 重复")
                    else:
                        print(f" {query} 命中，但 <{document_name}> 不是当前任务")
                    
                else:
                    print(f"<{document_name}> 与知识点关联度极低: {query}")


        print(knowlwdge_list)

        # 将knowlwdge_list转换为字符串,如果后端有需要的话
        # knowlwdge_list = str(knowlwdge_list)

        # 删除知识库中的文档
        delete_file(dataset_id, document_id)

  
        # 向回调接口发送内容
        callback_data = {
                "retJsonStr":knowlwdge_list,
                "rpId":rpId,
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

@app.route('/link', methods=['POST'])
def receive_knowledge():
    # 检查必填字段
    required_fields = ["rpId","retJsonStr","AuthorizationForPlatform","callBackUrl"]

    for field in required_fields:
        if field not in request.form:
            return jsonify({"code": 5,'msg':f"{field}字段缺失"}), 400

    rpId = request.form.get('rpId')
    retjsonstr = request.form['retJsonStr']
    authorization_token = request.form.get('AuthorizationForPlatform')
    callback_url = request.form.get('callBackUrl')

    # 验证回调URL是否有效
    parsed_url = urlparse(callback_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return jsonify({"code": 5, 'msg': "回调URL无效"}), 400
    
    text_content = request.form.get('text')  # 获取text字段内容
    file = request.files.get('file')  # 获取file字段内容
    file_name = ""
    file_path = os.path.join('data', f"{rpId}.txt")  # 默认文件路径以rpId命名

    if text_content:
        # 如果text字段有值，将内容保存为txt文件
        with open(file_path, 'w') as f:
            f.write(text_content)
        file_name = f"{rpId}.txt"
        # 启用新线程处理请求
        threading.Thread(target=process_and_callback2, args=(rpId, retjsonstr, authorization_token, callback_url, file_path, file_name)).start()
    elif file:
        # 如果file字段有值，保存文件
        file_name = f"{rpId}{file.filename}" 
        file_path = os.path.join('data', file_name)
        file.save(file_path)
        # 判断文件是否为图像格式，并执行OCR
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
            print("图像格式")
            text_content = perform_ocr(file_path)
            # 保存识别的文字为txt文件
            txt_file_path = os.path.join('data', f"{rpId}.txt")
            print(f"text_file_path:{txt_file_path}")
            with open(txt_file_path, 'w') as txt_file:
                txt_file.write(text_content)
            file_name = f"{rpId}.txt"
            file_path = txt_file_path  # 更新file_path为文本文件路径
            # 启用新线程处理请求
            threading.Thread(target=process_and_callback2, args=(rpId, retjsonstr, authorization_token, callback_url, file_path, file_name)).start()
        else:
            print("文档格式")
            # 启用新线程处理请求
            threading.Thread(target=process_and_callback, args=(rpId, retjsonstr, authorization_token, callback_url, file_path, file_name)).start()
    else:
        return jsonify({"code": 5, 'msg': "需要提供text或file字段"}), 400

    # 立即返回响应
    return jsonify({"code": 0, "rpId": rpId, "msg": "请求已接收，正在处理中......"}), 200


if __name__ == '__main__':
    app.run(port=8013, host='0.0.0.0')  # 运行在8013端口
