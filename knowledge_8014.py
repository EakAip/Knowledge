# 接口：8014

# PPT知识图谱

# 支持：pptx,ppt,pdf

from flask import Flask,request,jsonify
from openai import OpenAI
from pptx import Presentation
import pdfplumber
import os
import re
import threading
import subprocess
from urllib.parse import urlparse
import requests # 用于发送回调请求

app = Flask(__name__)

# 初始化OpenAI客户端
client = OpenAI(api_key="sk-075f0a3d6eec46e48b58072b9fd279f9", base_url="https://api.deepseek.com/beta")


def convert_ppt_to_pptx(input_file, output_dir):
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    # 调用libreoffice命令进行转换
    command = [
        "libreoffice",
        "--headless",
        "--convert-to",
        "pptx",
        input_file,
        "--outdir",
        output_dir
    ]
    subprocess.run(command, check=True)
    print(f"Converted {input_file} to .pptx format in {output_dir}")


# 提取PDF
def extract_text_from_pdf(file_path):
    all_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"

# 提取PPTX
def extract_text_from_pptx(file_path):
    all_text = ""

    # 如果文件是 .ppt 格式，则先转换为 .pptx
    if file_path.endswith('.ppt'):
        print(f"Detected .ppt file, converting {file_path} to .pptx...")
        output_dir = os.path.dirname(file_path)  # 使用相同目录
        try:
            convert_ppt_to_pptx(file_path, output_dir)
            # 更新文件路径为 .pptx
            file_path = file_path.replace('.ppt', '.pptx')
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion: {e}")
            raise ValueError("Failed to convert .ppt to .pptx. Please check the file or LibreOffice installation.")
    
    # 加载 .pptx 文件提取文本
    try:
        presentation = Presentation(file_path)
        # 遍历每个幻灯片
        for slide in presentation.slides:
            # 遍历每个形状
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    all_text += shape.text + "\n"
    except Exception as e:
        print(f"Error reading .pptx file: {e}")
        raise ValueError("Failed to read the .pptx file. Ensure the file is valid.")

    return all_text


# 定义大模型接口
def call_openai_model(content):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": content}
        ],
        stream=False,
        max_tokens=8192
    )
    return response.choices[0].message.content

# 定义提取知识点解析函数
def parse_text_to_structure(text):
    lines = text.split('\n')
    lines = [line.lstrip() for line in lines]  # 去除每行前面的空白字符
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
                if level > 1 and (level - 1) in levels:
                    levels[level - 1]['child'].append(current_node)
                levels[level] = current_node
        else:
            print(f"无法解析的行,已经跳过：{line}")
            continue

    return structure

# 回调
def send_callback(rpId, authorization_token, callback_url, data):
    try:
        
        # 向回调接口发送内容
        callback_data = {
            "retJsonStr":data,
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


    
    except requests.exceptions.RequestException as e:
        print(f"发送回调失败: {e}")


def process_file_and_callback(rpId, authorization_token, callback_url, file_path, file_name, modeltype):
    # 提取文本
    if file_path.endswith('.pdf'):
        all_text = extract_text_from_pdf(file_path)
        
    elif file_path.endswith('.pptx') or file_path.endswith('.ppt'):
        all_text = extract_text_from_pptx(file_path)
        
    else:
        print("不支持的文件类型")
        send_callback(callback_url, {"code": 1, "msg": "不支持的文件类型"})
        return

    # 构建内容
    content = all_text + """
    
请帮我提取下面文字中的章节标题，按照知识结构输出，如下面示例，中文回答：
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

    # 调用模型接口
    result = call_openai_model(content)
    
    print(result)

    # 解析结构
    structure = parse_text_to_structure(result)
    
    print(structure)

    # 发送回调
    send_callback(rpId, authorization_token,callback_url, structure)


@app.route('/knowledge', methods=['POST'])
def receive_knowledge():
    # 检查必填字段
    required_fields = ["rpId", "AuthorizationForPlatform", "callBackUrl"]

    for field in required_fields:
        if field not in request.form:
            return jsonify({"code": 5, 'msg': f"{field}字段缺失"}), 200

    rpId = request.form.get('rpId')
    authorization_token = request.form.get('AuthorizationForPlatform')
    callback_url = request.form.get('callBackUrl')
    print(f"回调接口:{callback_url}")

    # 验证回调URL是否有效
    parsed_url = urlparse(callback_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return jsonify({"code": 5, 'msg': "回调URL无效"}), 200

    # 接收文件对象
    if 'text' not in request.files:
        return jsonify({"code": 5, 'msg': "缺少文件"}), 200

    file = request.files['text']
    if file.filename == '':
        return jsonify({"code": 5, 'msg': "未选择文件"}), 200

    # 检查文件扩展名
    allowed_extensions = {'pdf', 'pptx', 'ppt'}
    file_ext = os.path.splitext(file.filename)[1].lower().replace('.', '')
    if file_ext not in allowed_extensions:
        return jsonify({"code": 5, 'msg': "仅支持上传PDF或PPT文件"}), 200

    # 获取文件名字
    file_name = file.filename
    # 保存文件到服务器路径
    save_dir = 'data/ppt'
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, file_name)
    file.save(file_path)
    print(f"文件已保存到 {file_path}")

    modeltype = request.form.get('modeltype', '1')  # 默认modeltype为'1'

    # 启动新线程处理文件并发送回调
    threading.Thread(target=process_file_and_callback, args=(rpId, authorization_token, callback_url, file_path, file_name, modeltype)).start()

    # 立即返回响应
    return jsonify({"code": 0, "rpId": rpId, "msg": "请求已接收，正在处理中......"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8014)
