1. pip install -r requirements.txt
pip install vllm==0.8.5
pip install flash-attn --no-cache-dir

3. 启动chat模型：
CUDA_VISIBLE_DEVICES=1 nohup python -m vllm.entrypoints.openai.api_server \
--model /opt/share/models/Qwen/Qwen2.5-32B-Instruct-awq \
--served-model-name Qwen2.5 \
--gpu_memory_utilization=0.8 \
--dtype=half \
--port=8213> vllm_chat_test.out &

4. OCR识别：CUDA_VISIBLE_DEVICES=0 python deal_database/pdf_ocr.py

5. 运行model/extract_code.py抽取恶意代码

6. deal_database/get_in_weaviate.py将恶意代码存入向量库

7. 修改settings.yaml中的code_model的model_path
   CUDA_VISIBLE_DEVICES=0 nohup python deal_database/search_postdeal_weaviate_api.py > server.log 2>&1 & 部署api服务
   ps -ef | grep search_postdeal_weaviate_api.py

deal_database/delete_weaviate.py可以删除向量库内容