import weaviate
import yaml
import os
import sys
import torch
import uvicorn
from typing import Optional, List, Union
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from openai import OpenAI, AsyncOpenAI

# Add root directory to sys.path to import model package
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from model.extract_prompt import CLEAN_MALICIOUS_CODE_PROMPT

class ChatModel:
    def __init__(self, chat_config):
        self.model_name = chat_config['model_name']
        self.api_key = chat_config['GRAPHRAG_API_KEY']
        self.base_url = chat_config['api_base']
        self.timeout = chat_config.get('timeout', chat_config['max_single_time'])
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        print(f"ChatModelClient模型{self.model_name}初始化成功")

    def get_chat(self, system_prompt="You are a helpful assistant", user_prompt="Hello, how can I help you?", timeout=None):
        actual_timeout = timeout if timeout is not None else self.timeout
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            timeout=actual_timeout
        )
        return response.choices[0].message.content

    async def get_chat_async(self, system_prompt="You are a helpful assistant", user_prompt="Hello, how can I help you?", timeout=None):
        actual_timeout = timeout if timeout is not None else self.timeout
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = await self.async_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            timeout=actual_timeout
        )
        return response.choices[0].message.content

    async def close_async(self):
        if self.async_client:
            await self.async_client.close()

# 全局变量存储资源
app_state = {}

def load_config():
    # 读取同级或上级目录的 settings.yaml
    settings_path = os.path.join(base_dir, 'settings.yaml')
    with open(settings_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def clean_code_logic(code: str, chat_model: ChatModel) -> str:
    """
    Cleans the input code string using LLM if it's too long.
    Uses logic similar to z.py.
    """
    try:
        system_prompt = "You are a code security analysis expert."
        user_prompt = CLEAN_MALICIOUS_CODE_PROMPT.format(CODE=code)
        
        cleaned_content = chat_model.get_chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        # Post-processing
        cleaned_content = cleaned_content.strip()
        
        # Remove markdown code blocks if present
        if cleaned_content.startswith("```"):
            lines = cleaned_content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_content = "\n".join(lines).strip()
            
        if cleaned_content == "CLEAN_CODE":
            return "" # Return empty if absolutely no malicious code found
            
        return cleaned_content
        
    except Exception as e:
        print(f"LLM Processing Error during cleaning: {e}")
        return code

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时加载配置和模型
    config = load_config()
    app_state['config'] = config
    
    # 提取配置
    weaviate_conf = config.get('weaviate', {})
    model_conf = config.get('models', {}).get('code_model', {})
    vector_search_conf = config.get('vector_search', {})
    chat_conf = config.get('models', {}).get('chat_model', {})

    # 初始化 Weaviate 客户端
    weaviate_url = weaviate_conf.get('url', 'http://localhost:8011')
    app_state['class_name'] = weaviate_conf.get('class_name', 'Security')
    app_state['client'] = weaviate.Client(url=weaviate_url)
    
    # 存储最大线程数和top_k
    app_state['max_threads'] = vector_search_conf.get('max_threads', 20)
    app_state['top_k'] = vector_search_conf.get('top_k', 5)
    app_state['certainty'] = vector_search_conf.get('certainty', 0.8)
    app_state['max_clean_threshold'] = vector_search_conf.get('max_clean_threshold', 1200)

    # 初始化 ChatModel 用于代码清洗
    try:
        app_state['chat_model'] = ChatModel(chat_conf)
        print(f"ChatModel initialized with model: {chat_conf.get('model_name')}")
    except Exception as e:
        print(f"Failed to initialize ChatModel: {e}")
        app_state['chat_model'] = None
    
    # 初始化 Embedding 模型
    model_path = model_conf.get('model_path')
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading embedding model on {device} from: {model_path} ...")
    
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
    print(f"Embedding model loaded successfully. Max sequence length set to: {target_seq_len}")
    
    yield
    
    # 关闭时清理资源
    app_state.clear()

app = FastAPI(title="Vector Search API with Code Cleaning", lifespan=lifespan)

class SearchRequest(BaseModel):
    query_code: Union[str, List[str]]

@app.post("/vector_search")
def search_code(request: SearchRequest):
    # 使用 def 而非 async def，因为 embedding 和 weaviate 客户端是阻塞的，FastAPI 会在线程池中运行
    try:
        client = app_state['client']
        embed_model = app_state['embed_model']
        class_name = app_state['class_name']
        chat_model = app_state.get('chat_model')
        threshold = app_state.get('max_clean_threshold', 1200)

        # 归一化输入为列表
        queries = [request.query_code] if isinstance(request.query_code, str) else request.query_code
        if not queries:
            return {"message": "Empty query", "data": []}

        # 应用代码清洗逻辑 (z.py logic)
        cleaned_queries = []
        for q in queries:
            if len(q) > threshold and chat_model:
                print(f"Code length {len(q)} exceeds threshold {threshold}. Applying cleaning...")
                cleaned_q = clean_code_logic(q, chat_model)
                cleaned_queries.append(cleaned_q)
            else:
                cleaned_queries.append(q)
        query_vectors = embed_model.embed_documents(cleaned_queries)

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
        
        # 组装返回结果，包含原始输入代码
        formatted_results = []
        for original_code, matches in zip(queries, results_list):
            formatted_results.append({
                "input_code": original_code,
                "records": matches
            })
        
        # 统计是否全为空
        if all(not res.get("matches") for res in formatted_results):
            return {"message": "No results found for any query", "data": formatted_results}
            
        return {"message": "Success", "data": formatted_results}

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
