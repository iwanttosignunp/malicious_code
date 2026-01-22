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

4. 修改settings.yaml中的batch_processing:output_folder为输出文件夹，deepseek_ocr:model_path为OCR模型路径，pdf_directory为输入的PDF文件夹  

5. OCR识别：CUDA_VISIBLE_DEVICES=2 python deal_database/pdf_ocr.py

6. 运行model/extract_malicious_code.py抽取恶意代码

7. 安装PostgreSQL：
    conda install -c conda-forge postgresql
    mkdir -p my_pgdata
    initdb -D my_pgdata
    pg_ctl -D my_pgdata -l logfile -o "-p 5435" start
   修改settings.yaml中的postgres配置(port/user/password)

8. deal_database/get_in_database.py将恶意代码存入postgres

9. deal_database/api_server.py部署api服务
   CUDA_VISIBLE_DEVICES=2 nohup python deal_database/api_server.py > server.log 2>&1 &
   ps -ef | grep api_server.py