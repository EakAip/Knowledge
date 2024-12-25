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

# 切换本地接口生成目录

# 使用正则精准提取目录


import requests
import json
import re
import os
import docx
import logging
from docx import Document
import time
import threading
from flask import Flask,request,jsonify
from urllib.parse import urlparse
import subprocess

app = Flask(__name__)

dataset_id = '8ac54dab-fda8-4208-baac-63d899d40045'         # "教材" 知识库 
api_key = 'dataset-OiRviBX3nHp5kdHKw7DZr9UM'                # 数据库的API-Key
base_url = 'http://188.18.18.106:5001/v1/datasets/'


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def convert_doc_to_docx(doc_path):
    logging.info("正在将doc格式转换为docx格式...")
    output_path = os.path.splitext(doc_path)[0] + '.docx'
    subprocess.run(['libreoffice', '--headless', '--convert-to', 'docx', doc_path, '--outdir', os.path.dirname(doc_path)])
    logging.info("转换完成！")
    return output_path

def upload_file(dataset_id,file_path,file_name):
    logging.info(f"[{file_name}]正在被上传到知识库......")
    url = f'{base_url}{dataset_id}/document/create_by_file'
    headers = {
        'Authorization':f'Bearer {api_key}'
    }
    data = {
        'data': (
            None,
            '{"indexing_technique": "high_quality", "process_rule": {"mode": "automatic", "rules": {}}}',
            'text/plain'
        )
    }
    files = {
        'file':(file_name,open(file_path,'rb'),'text/plain')
    }
    response = requests.post(url,headers=headers,files=files,data=data)
    if response.status_code == 200:
        batch_id = json.loads(response.text)["batch"]
        document_id = json.loads(response.text)["document"].get("id")
        logging.info(f"[{file_name}]上传成功,batch ID:{batch_id}")
        logging.info(f"[{file_name}]向量化处理中......")
        return batch_id,document_id
    else:
        logging.info(f"上传{file_name}到dify失败")
        return None
    
def extract_catalog(file_path,file_name):  # 修改为调用本地Qwen模型
    import PyPDF2
    import pypandoc
    import time
    from tqdm import tqdm
    import concurrent.futures
    
    # 如果是pdf，使用PyPDF2读取
    if file_path.endswith('.pdf'):
        logging.info(f"[{file_name}]正在被【PDF提取器】提取教材可能存在目录的10000字部分")
        pdf_reader = PyPDF2.PdfReader(file_path)
        # 存储所有文本的列表
        all_text = []
        # 遍历每一页
        for page in pdf_reader.pages:
            # 添加每页的文本到列表中
            text = page.extract_text()
            if text:
                # 剔除换行(后续可增加剔除空格)
                text = text.replace('\n',' ')
                # 剔除空格
                text = text.replace('  ','')
                all_text.append(text)                
            else:
                all_text.append("这页未发现文本")
        
        # 将列表合并为一个字符串
        full_text = " ".join(all_text)

        # 使用正则表达式查找“目录”及其变体（允许任意数量的空格）
        pattern = r"目\s*录"
        match_start = re.search(pattern, full_text)
        
        if match_start:
            logging.info(f"{file_name}找到目录起始位置")
            index1 = match_start.start()
            
            # 使用正则表达式查找“附录”及其变体（允许任意数量的空格）
            pattern2 = r"附\s*录"
            match_end = re.search(pattern2, full_text[index1:])
        
            # 使用正则表达式查找“参考文献”及其变体
            pattern3 = r"参\s*考\s*文\s*献"
            match_end2 = re.search(pattern3, full_text[index1:])
        
            if match_end:
                index2 = index1 + match_end.start()
                logging.info(f"{file_name}找到目录结束位置{index2}")
                # 从找到的 "目录" 位置开始截取到找到的 "附录" 位置
                extracted_text = full_text[index1:index2]
                logging.info(f"[{file_name}]提取目录片段文字成功！")
            elif match_end2:
                index2 = index1 + match_end2.start()
                logging.info(f"[{file_name}]找到目录后的“参考文献”位置{index2}")                
                # 从找到的 "目录" 位置开始截取到找到的 "参考文献" 位置
                extracted_text = full_text[index1:index2]
            else:
                logging.info(f"[{file_name}]未找到“附录”或者“参考文献”关键字，提取整篇文章目录后的8000字！")
                extracted_text = full_text[:8000]
        else:
            logging.info(f"[{file_name}] 为找到“目录”关键字，提取整篇文档的前10000字！")
            extracted_text = full_text[:10000]
    else:
        logging.info(f"[{file_name}]开始被【DOCX文本提取器】提取教材可能存在目录的10000字部分")
        full_text = pypandoc.convert_file(file_path,'plain')
        full_text = full_text.replace('\n',' ')
        # 剔除空格 
        full_text = full_text.replace('  ','')
        # 剔除"--"字符
        full_text = full_text.replace('--','')
        # 剔除"…"字符
        full_text = full_text.replace('…','')
        # 剔除". ."字符
        full_text = full_text.replace('. .','')
        
        # 使用正则表达式查找“目录”及其变体（允许任意数量的空格）
        pattern = r"目\s*录"
        match_start = re.search(pattern, full_text)
        
        if match_start:
            
            index1 = match_start.start()
            logging.info(f"[{file_name}]找到目录起始位置{index1}")
            # 使用正则表达式查找“附录”及其变体（允许任意数量的空格）
            pattern2 = r"附\s*录"
            match_end = re.search(pattern2, full_text[index1:])
            # 使用正则表达式查找“参考文献”及其变体
            pattern3 = r"参\s*考\s*文\s*献"
            match_end2 = re.search(pattern3, full_text[index1:])
        
            if match_end:
                index2 = index1 + match_end.start()
                logging.info(f"[{file_name}]找到目录后的“附录”位置{index2}")
                # 从找到的 "目录" 位置开始截取到找到的 "附录" 位置
                extracted_text = full_text[index1:index2]
                logging.info(f"[{file_name}]提取目录片段文字成功！")
            elif match_end2:
                index2 = index1 + match_end2.start()
                logging.info(f"找到目录后的“参考文献”位置{index2}")                
                # 从找到的 "目录" 位置开始截取到找到的 "参考文献" 位置
                extracted_text = full_text[index1:index2]
            else:
                logging.info(f"[{file_name}]未找到“附录”关键字，提取整篇文章目录后的8000字！")
                extracted_text = full_text[:8000]
        else:
            logging.info(f"[{file_name}] 未找到“目录”关键字，提取整篇文档的前10000字！")
            extracted_text = full_text[:10000]
            
    # print(extracted_text)
    
    # API 基本信息和认证设置
    API_URL = "http://188.18.18.106:5001/v1/completion-messages"
    API_KEY = "app-SNY0wCFB0plnC3prW8SmS9Lw"                # "生成目录" 工作流API密钥
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    
    payload = {
        "inputs": {"query": extracted_text},
        "response_mode": "streaming",  # 设置为流式模式
        "user": "abc-123"
    }
    
    result = ""
    
    try:
        with requests.post(API_URL, headers=headers, json=payload, stream=True, timeout=120) as response:
            if response.status_code != 200:
                logging.info(f"请求失败，状态码：{response.status_code}")
                try:
                    error_data = response.json()
                    logging.info(f"错误信息：{error_data}")
                except ValueError:
                    logging.info("响应内容不是有效的 JSON，无法获取错误信息")
                return

            # 逐行读取响应内容
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        json_str = decoded_line[6:]  # 移除 "data: " 前缀
                        try:
                            data = json.loads(json_str)
                        except json.JSONDecodeError:
                            print(f"无法解析 JSON: {json_str}")
                            continue

                        # 处理不同的事件类型
                        event = data.get("event", "message")  # 默认为 'message' 类型
                        if event == "message":
                            answer = data.get("answer", "")
                            # 使用 end='' 和 flush=True 使输出不换行
                            print(answer, end='', flush=True)
                            result += answer
                        elif event == "tts_message":
                            audio = data.get("audio", "")
                            print(f"TTS 音频块: {audio}")
                        elif event == "tts_message_end":
                            # print("TTS 音频流结束")
                            pass
                        elif event == "message_end":
                            print("消息流结束")
                        elif event == "message_replace":
                            replaced_answer = data.get("answer", "")
                            print(f"替换后的回答: {replaced_answer}")
                        elif event == "error":
                            status = data.get("status", "")
                            code = data.get("code", "")
                            message = data.get("message", "")
                            print(f"错误事件 - 状态码: {status}, 错误码: {code}, 消息: {message}")
                        elif event == "ping":
                            print("收到 ping 事件，保持连接存活")
                        else:
                            print(f"未知事件类型: {event}")
            # 不要file_name后缀
            filename = file_name.split('.')[0]
            # 将目录写入文件保存备份，将file_name.txt文件清空
            with open(f'data/catalog/{filename}目录.txt','w',encoding='utf-8') as f:
                # 先清空
                f.truncate()
                logging.info(f"[{file_name}] data/catalog/{filename}目录.txt——————>>>清空成功！")
                # 写入目录
                f.write(result)
                logging.info(f"[{file_name}]目录已经保存到: data/catalog/{filename}目录.txt")
            return result
    except requests.exceptions.Timeout:
        logging.info("请求超时")
    except requests.exceptions.RequestException as e:
        logging.info(f"请求异常: {e}")
    
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
            logging.info(f"无法解析的行,已经跳过：{line}")
            continue

    return structure
    
def check_processing_status(dataset_id, batch_id,file_name):   # 查看上传文件处理状态
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
                    logging.info(f"[{file_name}]处理完成,文档总分段数: {status_data['data'][0]['total_segments']}")
                    return status_data
                else:
                    logging.info(f"[{file_name}]正在处理中,处理状态：{document['indexing_status']}，处理进度：{document['completed_segments']}/{document['total_segments']}")
                    
        else:
            logging.info('获取Dify文档处理状态失败')
        time.sleep(5)  # Wait for 5 seconds before checking again







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


def enhance_structure_with_model_data(structure,file_name):  # 发送最后一级知识点给大模型

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

    def traverse_and_send(node,file_name):
        if not node['child']:  # 当前节点是叶子节点
            logging.info(f"[{file_name}]*******************************************")
            logging.info(f"[{file_name}]发送请求给模型: {node['name']}")
            logging.info(f"[{file_name}]*******************************************")
            model_response = extract_knowledge_points(node['name'])

            if model_response.get('data', {}).get("status") == 'succeeded':
                try:
                    result_data = model_response.get('data').get("outputs").get("result")
                    # logging.info(f"[{file_name}]提取到的结果数据: {result_data}")
                    json_str = extract_json(result_data)
                    if json_str:
                        result_dict = json.loads(json_str)
                        existing_names = {child['name'].strip() for child in node['child']}
                        # logging.info(f"[{file_name}]现有知识点: {existing_names}")
                        for value in result_dict.values():
                            value = value.strip()
                            if value not in existing_names and value not in all_nodes:
                                node['child'].append({"level": node['level'] + 1, "name": value,"child": [],"postponement": "", "definition": ""})
                                logging.info(f"[{file_name}]成功添加知识点: {value}")
                            else:
                                logging.info(f"[{file_name}]知识点 '{value}' 已存在，跳过添加。")
                except json.JSONDecodeError as e:
                    logging.info(f"Failed to decode JSON: {e}")
                except Exception as e:
                    logging.info(f"An error occurred: {e}")
            else:
                print(f"Model request failed with status: {model_response.get('status')}")
                if 'error' in model_response:
                    prilogging.infont(f"Error: {model_response['error']}")
        else:
            for child in node['child']:
                traverse_and_send(child,file_name)
     
    for node in structure['nodes']:         # 遍历结构并收集所有节点到 all_nodes 列表
        traverse_and_collect(node)

    for node in structure['nodes']:         # 然后再遍历结构，发送请求
        traverse_and_send(node,file_name)


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
        # logging.info(definition)
        return definition
    else:
        return {"error": "Request failed", "status_code": response.status_code, "message": response.text}
 

def fill_definitions(structure,file_name):  # 填充知识点定义
    def traverse_and_fill(node,file_name):
        logging.info(f"[{file_name}]*******************************************")
        logging.info(f"[{file_name}]填充知识点定义: {node['name']}")
        logging.info(f"[{file_name}]*******************************************")
        definition = get_definition(node['name'])
        node['definition'] = definition

        for child in node['child']:
            traverse_and_fill(child,file_name)

    for node in structure['nodes']:
        traverse_and_fill(node,file_name)


def delete_file(dataset_id, document_id,file_name):   # 删除文件
    url = f'{base_url}/{dataset_id}/documents/{document_id}'
    headers = {
        'Authorization': f'Bearer {api_key}'
    }

    response = requests.delete(url, headers=headers)
    if response.status_code == 200:
        logging.info(f"[{file_name}]在Dify知识库中删除成功")
    else:
        logging.info('删除Dify知识库文件失败')







def process_and_callback_catalog(rpId,authorization_token,callback_url,file_path,file_name,dataset_id):
    
    with app.app_context():
        # 提取可能的目录片段  # 读取目录 # 切分出三级知识树
        
        # 提取可能的目录片段
        catalog = extract_catalog(file_path,file_name)
        
        # 正则处理目录，转换为三级知识结构
        structure = parse_text_to_structure(catalog)

        # 向回调接发送内容
        callback_data = {
            "retJsonStr":structure,
            "rpId":rpId
        }
        
        headers = {
            'AuthorizationForPlatform':authorization_token
        }
        
        # 发送数据到回调接口
        response = requests.post(callback_url,json=callback_data,headers=headers)
        logging.info(f"[{file_name}]发送数据到回调接口")
        
        # 检查回调接口响应
        if response.status_code == 200:
            logging.info(f"[{file_name}]回调接口响应成功")
        else:
            logging.info("回调接口相应失败")

        return jsonify({
            "code":0,
            "msg":"success"
        })


def process_and_callback_definition(rpId,authorization_token,callback_url,file_path,file_name,dataset_id):
    
    with app.app_context():
        # 1.上传文件到dify知识库处理        2.提取可能的目录片段        3.读取目录 切分出三级知识树
        # 4.调用千问大模型生成三级知识点      5.调用回调接口        6.返回结果 

        
        batch_id,document_id = upload_file(dataset_id,file_path,file_name)  # 1.上传文件到dify知识库处理

        check_processing_status(dataset_id, batch_id,file_name)  # 打印该文件的处理状态

        # 提取可能的目录片段
        catalog = extract_catalog(file_path,file_name)

        if batch_id:
            # 删除临时文件
            # os.remove(file_path)


            # 正则处理目录，转换为三级知识结构
            structure = parse_text_to_structure(catalog)
            # 模型处理，拓展知识结构的三级知识点
            enhance_structure_with_model_data(structure,file_name)

            
            # 填充定义
            fill_definitions(structure,file_name)

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

        delete_file(dataset_id, document_id,file_name)

        return jsonify({"code": 0,'msg':"success"})









@app.route('/knowledge',methods=['POST'])
def receive_knowledge():
    # 检查必填字段
    required_fields = ['rpId',"AuthorizationForPlatform","callBackUrl"]

    for field in required_fields:
        if field not in request.form:
            return jsonify({"code":5,'msg':f"{field}字段缺失"}),200
        
    rpId = request.form.get('rpId')
    authorization_token = request.form.get('AuthorizationForPlatform')
    callback_url = request.form.get('callBackUrl')
    logging.info(f"[回调接口]：{callback_url}")
    
    # 验证回调接口是否有效
    parsed_url = urlparse(callback_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return jsonify({"code":5,"msg":"回调URL无效"}),200
    
    # 接收文件对象
    file = request.files['text']
    file_name = file.filename
    # 保存文件到服务器路径
    file_path = os.path.join("data/jiaocai",file_name)
    file.save(file_path)
    
    # 判断如果是doc文件则转换为docx格式
    if file_name.endswith('doc'):
        logging.info(f"程序发现上传的[{file_name}]为doc文件，正在将其转换为docx格式")
        file_path = convert_doc_to_docx(file_path)
        file_name = os.path.basename(file_path)
        logging.info(f"{file_name}转换后的文件保存为{file_path}")
    else:
        logging.info(f"[{file_name}]为可处理格式，无需转换....")
        
        

    modeltype = request.form.get('modeltype')
    if modeltype == '1':
        # 调用只提取目录函数
        threading.Thread(target=process_and_callback_catalog,args=(rpId,authorization_token,callback_url,file_path,file_name,dataset_id)).start()
    else:
        # 调用大模型函数，生成知识点定义
        threading.Thread(target=process_and_callback_definition,args=(rpId,authorization_token,callback_url,file_path,file_name,dataset_id)).start()
        
    return jsonify({"code":0, "rpId":rpId, "msg":"请求已经接收，正在处理中......"})

if __name__ == '__main__':
    
    app.run(host='0.0.0.0',port=8011)
    # extract_catalog("/opt/jyd01/wangruihua/api/knowledge/data/jiaocai/高等数学 第7版 上册 同济大学.docx","测试")
