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
        # format_code 用于子串匹配（去除空格后的代码）
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            file_name TEXT,
            title TEXT,
            malicious_code TEXT,
            description TEXT,
            format_code TEXT,    
            hash_str TEXT        
        );
        
        -- 为 format_code 创建索引，用于子串匹配
        CREATE INDEX IF NOT EXISTS idx_format_code ON {table_name}(format_code);
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
                format_code = data.get('format_code')  # 读取 format_code
                
                # hash 字段（原样存储）
                hash = data.get('hash')

                # 执行插入
                insert_sql = f"""
                INSERT INTO {table_name} 
                (file_name, title, malicious_code, description, format_code, hash_str) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cur.execute(insert_sql, (
                    file_name, 
                    title, 
                    malicious_code, 
                    description,
                    format_code,
                    hash
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