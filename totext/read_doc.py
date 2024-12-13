import os
import subprocess
from docx import Document

def convert_doc_to_docx(doc_file):
    # 确保文件路径正确且文件存在
    if not os.path.exists(doc_file):
        print("File does not exist.")
        return None
    
    # 获取文件的目录
    doc_dir = os.path.dirname(doc_file)
    
    # 新的docx文件路径
    new_file = doc_file.replace(".doc", ".docx")
    
    # 转换为docx文件
    command = f"libreoffice --headless --convert-to docx:\"Office Open XML Text\" \"{doc_file}\" --outdir \"{doc_dir}\""
    subprocess.call(command, shell=True)
    
    return os.path.join(doc_dir, os.path.basename(new_file))

def extract_text_from_docx(docx_file):
    # 创建 Document 对象
    doc = Document(docx_file)
    
    # 存储所有文本的列表
    all_text = []
    
    # 遍历每个段落
    for para in doc.paragraphs:
        # 添加段落文本到列表中
        all_text.append(para.text.replace("\n", " "))
    
    return all_text

# 指定你的.doc文件路径
doc_file_path = "/home/jyd01/wangruihua/knowledge_ner/data/数据结构实验指导书.doc"

# 将.doc文件转换为.docx
docx_file_path = convert_doc_to_docx(doc_file_path)

# 检查转换是否成功
if docx_file_path:
    # 从.docx文件中提取文本
    text_from_docx = extract_text_from_docx(docx_file_path)
    # 保存文件

    with open("/home/jyd01/wangruihua/knowledge_ner/data/数据结构实验指导书.txt", "w", encoding="utf-8") as f:

        for line in text_from_docx:
            f.write(line + "\n")
    print("Text extracted and saved successfully.")

for text in text_from_docx:
        print(text)
else:
    print("Conversion failed.")


    