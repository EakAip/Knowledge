import PyPDF2
import os

def extract_text_from_pdf(pdf_file):
    # 打开PDF文件
    with open(pdf_file, 'rb') as file:
        # 创建PDF阅读器对象
        pdf_reader = PyPDF2.PdfReader(file)
        
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
                all_text.append("No text found on this page.")
        
    return all_text

# 指定你的PDF文件路径
pdf_file_path = "/home/jyd01/wangruihua/knowledge_ner/data/Python核心编程第三版.pdf"

# 调用函数并提取文字
text_from_pdf = extract_text_from_pdf(pdf_file_path)

# 获取保存文件的路径
save_path = os.path.join(os.path.dirname(pdf_file_path), "Python核心编程第三版.txt")

# 保存提取的文字到本地文件
with open(save_path, 'w', encoding='utf-8') as file:
    for text in text_from_pdf:
        file.write(text)

# 打印文件保存位置
print(f"提取的文字已保存到 {save_path} 文件中。")
