import weaviate
import yaml
import os
import torch
import uvicorn
from typing import Optional, List, Union
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

# 全局变量存储资源
app_state = {}

def load_config():
    # 读取同级或上级目录的 settings.yaml
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings_path = os.path.join(base_dir, 'settings.yaml')
    with open(settings_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时加载配置和模型
    config = load_config()
    app_state['config'] = config
    
    # 提取配置
    weaviate_conf = config.get('weaviate', {})
    model_conf = config.get('models', {}).get('code_model', {})
    vector_search_conf = config.get('vector_search', {})
    
    # 初始化 Weaviate 客户端
    weaviate_url = weaviate_conf.get('url', 'http://localhost:8011')
    app_state['class_name'] = weaviate_conf.get('class_name', 'Security')
    app_state['client'] = weaviate.Client(url=weaviate_url)
    
    # 存储最大线程数和top_k
    app_state['max_threads'] = vector_search_conf.get('max_threads', 20)
    app_state['top_k'] = vector_search_conf.get('top_k', 5)
    app_state['certainty'] = vector_search_conf.get('certainty', 0.8)
    
    # 初始化 Embedding 模型
    model_path = model_conf.get('model_path')
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading model on {device} from: {model_path} ...")
    
    # 初始化模型
    embeddings = HuggingFaceEmbeddings(
        model_name=model_path,
        model_kwargs={"device": device, "trust_remote_code": True},
        encode_kwargs={"normalize_embeddings": True} # 推荐加上归一化
    )
    
    target_seq_len = model_conf.get('max_seq_length', 1024)

    # 设置底层 SentenceTransformer 的最大长度
    if hasattr(embeddings, '_client'):
        embeddings._client.max_seq_length = target_seq_len
    elif hasattr(embeddings, 'client'):
        embeddings.client.max_seq_length = target_seq_len

    app_state['embed_model'] = embeddings
    print(f"Model loaded successfully. Max sequence length set to: {target_seq_len}")
    
    yield
    
    # 关闭时清理资源
    app_state.clear()

app = FastAPI(title="Vector Search API", lifespan=lifespan)

class SearchRequest(BaseModel):
    query_code: Union[str, List[str]]

@app.post("/vector_search")
def search_code(request: SearchRequest):
    # 使用 def 而非 async def，因为 embedding 和 weaviate 客户端是阻塞的，FastAPI 会在线程池中运行
    try:
        client = app_state['client']
        embed_model = app_state['embed_model']
        class_name = app_state['class_name']

        # 归一化输入为列表
        queries = [request.query_code] if isinstance(request.query_code, str) else request.query_code
        if not queries:
            return {"message": "Empty query", "data": []}

        # 批量生成向量 (使用 embed_documents 加速)
        # HuggingFaceEmbeddings 如果在 GPU 上，批量处理会显著快于单次循环
        query_vectors = embed_model.embed_documents(queries)

        # 定义单个查询函数
        def _single_query(vector):
            near_vec = {"vector": vector, "certainty": app_state['certainty']}
            
            resp = (
                client.query
                .get(class_name, ["title", "file_name", "code", "describe"])
                .with_near_vector(near_vec)
                .with_limit(app_state['top_k'])
                .with_additional(["distance", "certainty"])
                .do()
            )
            if "errors" in resp:
                raise Exception(str(resp["errors"]))
            return resp["data"]["Get"][class_name]

        max_threads = min(len(query_vectors), app_state['max_threads'])
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            # map 返回的结果顺序与输入顺序一致
            results_list = list(executor.map(_single_query, query_vectors))
        
        # 统计是否全为空
        if all(not res for res in results_list):
            return {"message": "No results found for any query", "data": results_list}
            
        return {"message": "Success", "data": results_list}

    except Exception as e:
        import traceback
        error_msg = f"Error processing request: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    # 读取配置启动服务
    config = load_config()
    server_conf = config.get('vector_search', {})
    host = server_conf.get('host', '0.0.0.0')
    port = server_conf.get('port', 5127)
    
    uvicorn.run(app, host=host, port=port)