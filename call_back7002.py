# 回调测试地址模拟

# 接受回调数据，返回状态

# 端口7002

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/kc/resource/knowledgeCallBack', methods=['POST'])
def knowledge_callback():
    # 获取请求参数
    authorization_token = request.headers.get('AuthorizationForPlatform')

    # 知识图谱测试
    ret_json_str = request.json.get('retJsonStr')
    rp_id = request.json.get('rpId')
    print(ret_json_str, rp_id)

    # CV测试
    # data = request.json.get('result')
    # file_name = request.json.get('file_name')
    # print(data,file_name)

    # 返回处理后的结果

    data = {}  # 知识图谱测试返回数据

    # data = {"callback_data": file_name.replace('.mp4', '.txt')}  # CV测试返回数据

    meta = {
        "code": "0",  # 填写状态码，0 表示成功
        "message": "Success",  # 填写消息
        "success": True  # 填写成功状态
    }
    response_data = {
        "data": data,
        "meta": meta
    }

    return jsonify(response_data)

if __name__ == '__main__':
    app.run(port=7002,host='0.0.0.0')  # 运行在7002端口

