# 接口8011

# 教材知识图谱

# 使用pypandoc提取文档前20000字

# 调研deepseek V2 接口直接生成目录

# 回调返回结果

# 添加知识点定义

# 拓展最后一级目录(修改为片段命中)

# 知识点去重

# 添加参数 传入参数值为 “1” 的时候，只返回目录

# ①增加程序健壮性，第几篇-->第几章 ②只提取"目录"两个字之后的15000字  ③添加进度条


import requests
import json
import re
import os
import docx

from docx import Document
import time
import threading
from flask import Flask, request, jsonify
from urllib.parse import urlparse
import subprocess


app = Flask(__name__)

dataset_id = '8ac54dab-fda8-4208-baac-63d899d40045'         # "教材" 知识库 
api_key = 'dataset-OiRviBX3nHp5kdHKw7DZr9UM'                # 数据库的API-Key
base_url = 'http://188.18.18.106:5001/v1/datasets/'


def convert_doc_to_docx(doc_path):  # # 将doc文件转换为docx文件
    print("正在将doc格式转换为docx格式...")
    output_path = os.path.splitext(doc_path)[0] + '.docx'
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'docx', doc_path, '--outdir', os.path.dirname(doc_path)])
    print("转换完成！")
    return output_path


def upload_file(dataset_id,file_path,file_name):   # 上传文件到Dify知识库,进行向量化处理

    print(f"正在上传[{file_path}]到知识库..........")

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
        print(f"[{file_name}]上传成功\nbatch ID:{batch_id}\n向量化处理中..........")
        return batch_id,document_id
    else:
        print(f'上传{file_name}到dify失败')
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
            print('获取Dify文档处理状态失败')
        time.sleep(5)  # Wait for 5 seconds before checking again


def extract_catalog(file_path,file_name):  # 调用deepseek V2 接口直接生成目录
    import PyPDF2
    from openai import OpenAI
    import pypandoc
    import time
    from tqdm import tqdm
    import concurrent.futures
    
    # 如果是pdf，需要先转换为docx格式
    if file_path.endswith('.pdf'):
        print(f"【PDF文本提取器】  开始提取[{file_name}]存在目录20000字部分！")
        pdf_reader = PyPDF2.PdfReader(file_path)
        # 存储所有文本的列表
        all_text = []
        # 遍历每一页
        for page in pdf_reader.pages:
            # 添加每页的文本到列表中
            text = page.extract_text()
            if text:
                # 不要换行
                all_text.append(text.replace('\n', ' '))
            else:
                all_text.append("这页未发现文本")
        # 将列表合并为一个字符串
        full_text = ' '.join(all_text)
        # 查找第一次出现“目录”后的文本
        index = full_text.find("目录")
        if index != -1:
            # 从找到的 "目录" 位置开始截取接下来的 20000 个字符
            extracted_text = full_text[index: index + 15000]
            print(f"[{file_name}] 提取目录片段文字成功！")
        else:
            print(f"[{file_name}] 未找到“目录”关键字，提取整篇文章前15000字。")
            extracted_text = full_text[:15000]
    else:
        print(f"\n【DOCX文本提取器】\n   开始提取[{file_name}]目录片段文字！")
        full_text = pypandoc.convert_file(file_path, 'plain')       # 使用 pypandoc 将文档转换为纯文本
        index = full_text.find("目录")
        if index != -1:
            # 从找到的 "目录" 位置开始截取接下来的 20000 个字符
            extracted_text = full_text[index: index + 15000]
            print(f"[{file_name}] 提取目录片段文字成功！")
        else:
            print(f"[{file_name}] 未找到“目录”关键字，提取整篇文章前15000字。")
            extracted_text = full_text[:15000]

    prompt = """请帮我提取上面片段中的目录，采用.划分等级，不要输出无关内容,不允许包含"*"，严格按照下面示例标准格式输出：
第1章 物理学
1.1 什么是物理学
1.1.1 物理学的研究对象
1.1.1.1 宇宙
1.1.1.2 地球
1.1.2 物理学的研究方法
1.1.3 物理量与国际单位制
1.1.4 量纲
1.2 物理学与科学技术
1.2.1 物理规律的普适性
1.2.1.1 物理规律
1.2.1.2 普适性
1.2.2 自然科学的基础
1.2.3 技术革命的源泉
1.2.4 物理学与社会

第2章 质点运动学
2.1 直角坐标系中质点运动的描述
2.1.1 参考系质点模型
2.1.2 位置矢量与运动方程
2.1.2.1 位置矢量
2.1.2.2 运动方程
2.1.3 位移与路程
2.1.4 速度
2.1.5 加速度
2.1.6 质点运动的两类问题举例
2.2 自然坐标系中质点运动的描述
2.2.1 切向加速度与法向加速度
2.2.2 圆周运动及真角量描述
2.2.3 圆周运动中结雷日角量的矢量关系
2.3 相对运动
2.3.1 运动的相对性
2.3.2 伽利略变换与绝对时空观
            """


    content = extracted_text + prompt
    # 文件名字为教材名，去掉教材名字后缀.docx
    file_name = file_name.split('.')[0]
    print(f"[{file_name}]目录标准格式提取中...")


    client = OpenAI(api_key="sk-075f0a3d6eec46e48b58072b9fd279f9", base_url="https://api.deepseek.com/beta")

    # 使用多线程来实现模型调用和进度条同时进行
    def call_model():
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": content},
            ],
            stream=False,
            max_tokens=8192
        )
        return response.choices[0].message.content

    # 使用线程池来并行处理进度条和模型调用
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交任务
        future = executor.submit(call_model)

        # 显示进度条，直到模型返回结果
        with tqdm(total=180, desc="大模型处理中", bar_format='{l_bar}\033[94m{bar}\033[0m [时间剩余: {remaining}]') as pbar:
            for _ in range(180):
                if future.done():
                    pbar.n = 180  # 直接将进度条设为完成状态
                    pbar.update(0)  # 触发更新，显示完整进度
                    break
                time.sleep(1)
                pbar.update(1)

        # 获取模型处理结果
        catalog = future.result()

    # 使用正则表达式将catalog“第_篇”替换为“第_章”
    catalog = re.sub(r'第(\d+)篇', r'第\1章', catalog)
    print(f"{file_name}标准格式目录提取成功！\n目录内容:\n {catalog}")
    # 将目录写入文件保存备份，将file_name.txt文件清空
    with open(f'data/{file_name}目录.txt','w',encoding='utf-8') as f:
        # 先清空
        f.truncate()
        print(f"保存目录前确保[{file_name}]为空，清空成功！")
        # 写入目录
        f.write(catalog)
    print(f"目录已经保存到: data/{file_name}目录.txt")

    return catalog


def parse_text_to_structure(text):      # 提取目录知识结构，到目录最后一节知识点
    lines = text.split('\n')
    lines = [line.lstrip() for line in lines]  # 去除每行前面的空白字符（而不影响行尾的空白）
    structure = {"nodes": [], "message": "成功", "code": 0}
    levels = {}

    for line in lines:
        if not line.strip():
            continue

        chapter_match = re.match(r'第\s*([一二三四五六七八九十\d]+)\s*章[:：]?\s*(.*)', line)
        level_matches = re.findall(r'(\d+(?:\.\d+)*)\s+(.*)', line)

        if chapter_match:
            chapter_number, chapter_title = chapter_match.groups()
            chapter_title = chapter_title.strip()
            current_node = {"level": 1, "name": chapter_title, "child": [], "postponement": "", "definition": ""}
            structure['nodes'].append(current_node)
            levels[1] = current_node
        elif level_matches:
            for match in level_matches:
                level_str, title = match
                title = title.strip()
                level = len(level_str.split('.'))
                current_node = {"level": level, "name": title, "child": [], "postponement": "", "definition": ""}
                if level > 1:
                    levels[level - 1]['child'].append(current_node)
                levels[level] = current_node
        else:
            print(f"无法解析的行,已经跳过：{line}")
            continue

    return structure


def extract_knowledge_points(query, user="abc-123"):    # AIGC拓展知识点
    API_URL = "http://188.18.18.106:5001/v1/workflows/run"
    API_KEY = "app-Jm8aI4B3wFAQGrTp1Gn4TAIf"    # AIGC拓展最后一级知识点工作流的API-KEY—————— 106服务器
    # API_KEY = "app-a3KwoIjA6icp69NEBXKuwi6J"    # AIGC拓展最后一级知识点工作流的API-KEY————————107服务器
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {"query": query},
        "response_mode": "blocking",
        "user": user
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()  # 返回 JSON 数据
    else:
        return {"error": "Request failed", "status_code": response.status_code, "message": response.text}


def enhance_structure_with_model_data(structure):  # 发送最后一级知识点给大模型

    all_nodes = []  # 用来保存所有节点的列表

    def traverse_and_collect(node):  # 在遍历时，将所有节点的名称添加到 all_nodes 列表中
        all_nodes.append(node['name'].strip())
        for child in node['child']:
            traverse_and_collect(child)
    
    def extract_json(text):  # 模型返回json格式不稳定，需要处理
        try:
            json_start = text.index("{")
            json_end = text.rindex("}") + 1
            json_str = text[json_start:json_end]
            return json_str
        except ValueError:
            return text

    def traverse_and_send(node):
        if not node['child']:  # 当前节点是叶子节点
            print("\n*******************************************")
            print(f"发送请求给模型: {node['name']}")
            print("*******************************************")
            model_response = extract_knowledge_points(node['name'])

            if model_response.get('data', {}).get("status") == 'succeeded':
                try:
                    result_data = model_response.get('data').get("outputs").get("result")
                    print(f"提取到的结果数据: {result_data}")
                    json_str = extract_json(result_data)
                    if json_str:
                        result_dict = json.loads(json_str)
                        existing_names = {child['name'].strip() for child in node['child']}
                        print(f"现有知识点: {existing_names}")
                        for value in result_dict.values():
                            value = value.strip()
                            if value not in existing_names and value not in all_nodes:
                                node['child'].append({"level": node['level'] + 1, "name": value,"child": [],"postponement": "", "definition": ""})
                                print(f"成功添加知识点: {value}")
                            else:
                                print(f"知识点 '{value}' 已存在，跳过添加。")
                except json.JSONDecodeError as e:
                    print(f"Failed to decode JSON: {e}")
                except Exception as e:
                    print(f"An error occurred: {e}")
            else:
                print(f"Model request failed with status: {model_response.get('status')}")
                if 'error' in model_response:
                    print(f"Error: {model_response['error']}")
        else:
            for child in node['child']:
                traverse_and_send(child)
     
    for node in structure['nodes']:         # 遍历结构并收集所有节点到 all_nodes 列表
        traverse_and_collect(node)

    for node in structure['nodes']:         # 然后再遍历结构，发送请求
        traverse_and_send(node)


def get_definition(query, user="abc-123"):  # 大模型提取知识点定义
    # API 基本信息和认证设置
    API_URL = "http://188.18.18.106:5001/v1/workflows/run"
    API_KEY = "app-USYkcdNjA7nhTbki1rhgAXnM"                # "生成目录" 工作流API密钥
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 构造请求体
    payload = {
        "inputs": {"query": query},
        "response_mode": "blocking",
        "user": user
    }

    # 发送 POST 请求
    response = requests.post(API_URL, headers=headers, json=payload)
    
    # 尝试解析 JSON 响应并获取定义 如过请求失败，跳过

    try:
        definition = response.json()["data"]["outputs"]["result"]
    except KeyError as e:
        definition = ""
        

    # 检查是否成功收到响应
    if response.status_code == 200:
        print(definition)
        return definition
    else:
        return {"error": "Request failed", "status_code": response.status_code, "message": response.text}
 

def fill_definitions(structure):  # 填充知识点定义
    def traverse_and_fill(node):
        print("\n*******************************************")
        print(f"填充知识点定义: {node['name']}")
        print("*******************************************")
        definition = get_definition(node['name'])
        node['definition'] = definition

        for child in node['child']:
            traverse_and_fill(child)

    for node in structure['nodes']:
        traverse_and_fill(node)


def delete_file(dataset_id, document_id):   # 删除文件
    url = f'{base_url}/{dataset_id}/documents/{document_id}'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        print(f"[{document_id}]在Dify知识库中删除成功")
    else:
        print('删除Dify知识库文件失败')


def process_and_callback(rpId, authorization_token, callback_url, file_path,file_name, dataset_id):

    with app.app_context():
        # 1.上传文件到dify知识库处理        2.提取可能的目录片段        3.读取目录 切分出三级知识树
        # 4.调用千问大模型生成三级知识点      5.调用回调接口        6.返回结果

        batch_id,document_id = upload_file(dataset_id,file_path,file_name)
        # 打印batch_id对应文件处理状态
        check_processing_status(dataset_id, batch_id)

        # 提取可能的目录片段
        catalog = extract_catalog(file_path,file_name)
    
        # # 手动导入目录
        # file_path = f'data_mulucopy/数据结构C语言版.txt'
        # with open(file_path, 'r', encoding='utf-8') as file:
        #      catalog = file.read()

        if batch_id:
            # 删除临时文件
            # os.remove(file_path)


            # 正则处理目录，转换为三级知识结构
            structure = parse_text_to_structure(catalog)
            # 模型处理，拓展知识结构的三级知识点
            enhance_structure_with_model_data(structure)

            
            # 填充定义
            fill_definitions(structure)

            print("*******************************************************************************")
            print(structure)



            # 向回调接口发送内容
            callback_data = {
                "retJsonStr":structure,
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

        delete_file(dataset_id, document_id)

        return jsonify({"code": 0,'msg':"success"})

def process_and_callback_mulu(rpId, authorization_token, callback_url, file_path,file_name, dataset_id):

    with app.app_context():
        # 1.提取可能的目录片段        2.读取目录 切分出三级知识树

        # 提取可能的目录片段
        catalog = extract_catalog(file_path,file_name)
    
        # 正则处理目录，转换为三级知识结构
        structure = parse_text_to_structure(catalog)

        # 向回调接口发送内容
        callback_data = {
            "retJsonStr":structure,
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


        return jsonify({"code": 0,'msg':"success"})



@app.route('/knowledge', methods=['POST'])
def receive_knowledge():
    # 检查必填字段
    required_fields = ["rpId","AuthorizationForPlatform","callBackUrl"]

    for field in required_fields:
        if field not in request.form:
            return jsonify({"code": 5,'msg':f"{field}字段缺失"}), 200

    rpId = request.form.get('rpId')
    authorization_token = request.form.get('AuthorizationForPlatform')
    callback_url = request.form.get('callBackUrl')
    print(f"回调接口:{callback_url}")

    # 验证回调URL是否有效
    parsed_url = urlparse(callback_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return jsonify({"code": 5,'msg':"回调URL无效"}), 200
    
    # 接收文件对象
    file = request.files['text']
    # 获取文件名字
    file_name = file.filename
    # 保存文件到服务器路径
    file_path = os.path.join('data/jiaocai', file_name)
    file.save(file_path)

    # 判断如果是doc文件，则将其转换为docx格式
    if file_name.endswith('.doc'):
        print("程序发现上传文件为doc文件，正在将其转换为docx文件")
        file_path = convert_doc_to_docx(file_path)
        file_name = os.path.basename(file_path)  # 更新 file_name 为新的 docx 文件名
        print(f"转换后文件保存为{file_path}")
    else:
        print("文件格式为docx,程序处理中...")

    modeltype = request.form.get('modeltype')
    if modeltype == '1':
        # 调用目录函数，新线程处理请求
        threading.Thread(target=process_and_callback_mulu,args=(rpId,authorization_token,callback_url,file_path,file_name,dataset_id)).start()
    else:
        # 启用大模型函数，新线程处理请求
        threading.Thread(target=process_and_callback,args=(rpId,authorization_token,callback_url,file_path,file_name,dataset_id)).start()
    
    # 立即返回响应
    return jsonify({"code": 0,"rpId": rpId,"msg":"请求已接收，正在处理中......"}),200



if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8011)
