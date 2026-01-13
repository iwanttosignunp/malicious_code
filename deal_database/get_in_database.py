import psycopg2
import yaml
import json
import os

# 读取配置文件
def get_file_path(yaml_file='settings.yaml'):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    folder = config['batch_processing']['output_folder']
    filename = config['batch_processing']['output_file_name']
    return os.path.join(folder, filename)

# 读取数据库配置
def get_db_config(yaml_file='settings.yaml'):
    with open(yaml_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    return {
        'host': db_config['host'],
        'port': db_config['port'],
        'user': db_config['user'],
        'password': db_config['password'],
        'database': db_config['database'],
        'table_name': db_config['table_name']
    }


def main():
    jsonl_path = get_file_path()
    
    if not os.path.exists(jsonl_path):
        print(f"错误: 找不到文件 {jsonl_path}")
        return

    try:
        # 连接数据库
        db_config = get_db_config()
        table_name = db_config.pop('table_name')
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        print("数据库连接成功！")

        # 3. 创建表
        # 注意：hash_code 使用 BYTEA 类型存储二进制
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            file_name TEXT,
            title TEXT,
            malicious_code TEXT,
            description TEXT,
            hash_code BYTEA,     
            hash_str TEXT        
        );
        
        -- 为 hash_code 创建索引，因为你说之后要频繁比较它
        CREATE INDEX IF NOT EXISTS idx_hash_code ON {table_name}(hash_code);
        """
        cur.execute(create_table_sql)
        conn.commit()

        # 4. 读取 JSONL 并插入
        print(f"开始读取文件: {jsonl_path}")
        count = 0
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                    
                data = json.loads(line)
                
                # 提取需要的字段
                file_name = data.get('file_name')
                title = data.get('title')
                malicious_code = data.get('malicious_code')
                description = data.get('describe')
                
                # 处理 hash_code: 将十六进制字符串转为二进制
                raw_hash_hex = data.get('hash_code')
                hash_code_bytes = None
                if raw_hash_hex:
                    # bytes.fromhex 将 "a1b2" 这种字符串转为 b'\xa1\xb2'
                    hash_code_bytes = bytes.fromhex(raw_hash_hex)
                
                # hash 字段（原样存储）
                original_hash = data.get('hash')

                # 执行插入 (format_code 被忽略)
                insert_sql = f"""
                INSERT INTO {table_name} 
                (file_name, title, malicious_code, description, hash_code, hash_str) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cur.execute(insert_sql, (
                    file_name, 
                    title, 
                    malicious_code, 
                    description,
                    hash_code_bytes, 
                    original_hash
                ))
                count += 1

        conn.commit()
        print(f"成功插入 {count} 条数据！")

    except Exception as e:
        print(f"发生错误: {e}")
        conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == '__main__':
    main()