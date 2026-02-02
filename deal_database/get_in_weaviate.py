'''
数据库录入数据
'''
import weaviate
from weaviate.util import generate_uuid5
import pandas as pd
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
import warnings
warnings.filterwarnings("ignore")
import os
import yaml

def load_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def deal_file(file_name, embed_model_name, client, class_name, target_seq_len=1024, batch_size=1):
    df = pd.read_json(file_name, lines=True, encoding="utf-8")
    
    # 初始化模型
    embed_model = HuggingFaceEmbeddings(
        model_name=embed_model_name,
        model_kwargs={"device": "cuda", "trust_remote_code": True},
        encode_kwargs={"normalize_embeddings": True} # 加上归一化，与查询端保持一致
    )

    if hasattr(embed_model, '_client'):
        embed_model._client.max_seq_length = target_seq_len
    elif hasattr(embed_model, 'client'):
        embed_model.client.max_seq_length = target_seq_len
        
    print(f"Embedding model loaded. Max sequence length enforced to: {target_seq_len}")

    num_rows = df.shape[0]
    print(f"Total rows to process: {num_rows}")

    for start_idx in range(0, num_rows, batch_size):
        end_idx = min(start_idx + batch_size, num_rows)
        # 打印进度
        print(f"Processing batch: {start_idx} to {end_idx} ...")
        
        batch_df = df[start_idx:end_idx].reset_index(drop=True)  # 重置索引
        # 使用 code 列进行向量化
        codes = batch_df['code'].tolist()

        # 分批进行嵌入处理
        code_embeddings = embed_model.embed_documents(codes)

        data = {
            "title": batch_df['title'],
            "file_name": batch_df["file_name"],
            "code": codes,
            "describe": batch_df["describe"],
            "hash": batch_df["hash"],
            "embeddings": code_embeddings
        }
        df_with_embed = pd.DataFrame(data).reset_index(drop=True)  # 重置索引

        with client.batch(batch_size=batch_size) as batch:
            for i in range(df_with_embed.shape[0]):
                properties = {
                    "title": df_with_embed.title[i],
                    "file_name": df_with_embed.file_name[i],
                    "code": df_with_embed.code[i],
                    "describe": df_with_embed['describe'][i],
                    "hash": df_with_embed.hash[i]
                }
                custom_vector = df_with_embed.embeddings[i]
                batch.add_data_object(
                    properties,
                    class_name=class_name,
                    vector=custom_vector,
                    uuid=generate_uuid5(properties)
                )

def main():
    # 读取配置文件
    settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'settings.yaml')
    config = load_config(settings_path)
    
    # 获取 embeddings 模型名称
    code_model_config = config.get('models', {}).get('code_model', {})
    embed_model_name = code_model_config.get('model_path')
    target_seq_len = code_model_config.get('max_seq_length', 1024)

    if not embed_model_name:
        print("Error: models:code_model:model_path not found in settings.yaml")
        return

    # 获取输入文件路径
    batch_config = config.get('batch_processing', {})
    output_folder = batch_config.get('output_folder', 'output')
    output_file_name = batch_config.get('output_file_name', 'code_results.jsonl')
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(project_root, output_folder, output_file_name)
    
    if not os.path.exists(file_path):
        print(f"Error: Input file not found at {file_path}")
        return

    # Weaviate 配置
    weaviate_config = config.get('weaviate', {})
    weaviate_url = weaviate_config.get('url', 'http://localhost:8011')
    class_name = weaviate_config['class_name']

    # 初始化 Weaviate 客户端
    client = weaviate.Client(url=weaviate_url)

    # 创建 class
    try:
        class_obj = {
            "class": class_name,
            "vectorIndexConfig": {
                "distance": "cosine"
            }
        }
        client.schema.create_class(class_obj)
        print(f"Class '{class_name}' created successfully.")
    except Exception as e:
        print(f"Class '{class_name}' already exists.")

    print(f"Processing file: {file_path}")
    print(f"Using model: {embed_model_name}")
    print(f"Target sequence length: {target_seq_len}")
    print(f"Weaviate URL: {weaviate_url}")
    print(f"Class Name: {class_name}")
    
    deal_file(file_path, embed_model_name, client, class_name, target_seq_len, batch_size=100)

if __name__ == "__main__":
    main()