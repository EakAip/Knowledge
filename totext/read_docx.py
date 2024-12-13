from docx import Document

def extract_text_from_docx(docx_file):
    # 创建 Document 对象
    doc = Document(docx_file)
    
    # 存储所有文本的列表
    all_text = []
    
    # 遍历每个段落
    for para in doc.paragraphs:
        # 添加段落文本到列表中
        all_text.append(para.text.replace('\n', ' '))
    
    return all_text

# 指定你的 Word 文档路径
docx_file_path = "/opt/jyd01/wangruihua/4090copy/knowledge/data/数据结构实验指导书.docx"

# 调用函数并打印结果
text_from_docx = extract_text_from_docx(docx_file_path)
# 保存
with open('/opt/jyd01/wangruihua/4090copy/knowledge/data/数据结构实验指导书.txt', 'w', encoding='utf-8') as f:
    for text in text_from_docx:
        f.write(text + '\n')
    f.close()