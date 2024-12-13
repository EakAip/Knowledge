# funasr_module.py
from funasr import AutoModel
import torch

def run_funasr(input_audio):
    model = AutoModel(
        model="/opt/jyd01/wangruihua/mymodel/modelscope/hub/damo/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        model_revision="v2.0.4", 
        vad_model="/opt/jyd01/wangruihua/mymodel/modelscope/hub/damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        vad_model_revision="v2.0.4",
        punc_model="/opt/jyd01/wangruihua/mymodel/modelscope/hub/damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        punc_model_revision="v2.0.4",
    )

    # 尝试释放未使用的GPU内存
    torch.cuda.empty_cache()

    res = model.generate(input=input_audio)
    return res[0]["text"]

if __name__ == "__main__":
    input_audio = "/opt/jyd01/wangruihua/4090copy/speaker/test/audio.wav"
    result = run_funasr(input_audio)
    print(result)