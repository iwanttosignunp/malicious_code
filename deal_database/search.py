import psycopg2
import yaml
import hashlib
import re

def get_db_config(yaml_file='settings.yaml'):
    """从配置文件读取数据库配置"""
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


def generate_hash_code(code_string):
    """
    生成代码字符串的 SHA256 哈希值（二进制格式）
    
    Args:
        code_string: 输入的代码字符串
        
    Returns:
        bytes: SHA256 哈希值的二进制表示
    """
    # 移除所有空白字符和换行符
    formatted_code = ''.join(code_string.split())
    
    # 生成 SHA256 哈希
    hash_obj = hashlib.sha256(formatted_code.encode('utf-8'))
    
    # 返回二进制格式
    return hash_obj.digest()


def search_malicious_code(code_string, yaml_file='settings.yaml'):
    """
    根据代码字符串（或字符串列表）搜索数据库中的恶意代码
    
    Args:
        code_string: 要搜索的代码字符串或字符串列表
        yaml_file: 配置文件路径，默认为 'settings.yaml'
        
    Returns:
        dict: 包含状态和数据的字典
              {
                  'state': 'success' | 'not_found' | 'error',
                  'message': str,
                  'data': list,  # 匹配的记录列表，每个元素包含 code_string 和对应的查询结果
                  'count': int   # 找到数据的 code_string 数量
              }
    """
    # 如果输入是单个字符串，转换为列表
    if isinstance(code_string, str):
        code_strings = [code_string]
    else:
        code_strings = code_string
    
    # 连接数据库
    db_config = get_db_config(yaml_file)
    table_name = db_config.pop('table_name')
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    # 存储所有找到数据的结果
    all_results = []
    
    # 对每个 code_string 执行查询
    for code_str in code_strings:
        # 清理代码字符串
        cleaned_code = re.sub(r'[\s\n]+', '', code_str)
        
        # 生成哈希值
        hash_bytes = generate_hash_code(cleaned_code)
        hash_hex = hash_bytes.hex()
        
        # 查询数据库
        query = f"""
        SELECT id, file_name, title, malicious_code, description, hash_str
        FROM {table_name}
        WHERE hash_code = %s
        """
        
        cur.execute(query, (hash_bytes,))
        rows = cur.fetchall()
        
        # 如果找到了数据，添加到结果中
        if rows:
            records = []
            for row in rows:
                records.append({
                    'id': row[0],
                    'file_name': row[1],
                    'title': row[2],
                    'malicious_code': row[3],
                    'description': row[4],
                    'hash_str': row[5]
                })
            
            all_results.append({
                'code_string': code_str,
                'hash': hash_hex,
                'records': records,
                'count': len(records)
            })
    
    cur.close()
    conn.close()
    
    # 构造返回结果
    if all_results:
        return {
            'state': 'success',
            'message': f'查询成功，找到 {len(all_results)} 个代码字符串的匹配数据',
            'data': all_results,
            'count': len(all_results)
        }
    else:
        return {
            'state': 'not_found',
            'message': '所有代码字符串均未找到匹配的恶意代码',
            'data': [],
            'count': 0
        }


if __name__ == '__main__':
    code = """30 std 0x1003042B0LL:\"~/Library/PubSub/Feeds/db.sqlite3\""""
    
    print("=" * 60)
    print("测试 1: 单个代码字符串搜索")
    print("=" * 60)
    print(f"输入代码: {code.strip()}")
    print("-" * 60)
    
    # 执行搜索
    result = search_malicious_code(code)
    
    # 输出结果
    print(f"状态: {result['state']}")
    print(f"消息: {result['message']}")
    print(f"找到的代码字符串数量: {result['count']}")
    
    if result['data']:
        for item in result['data']:
            print(f"\n代码字符串: {item['code_string'][:50]}...")
            print(f"哈希: {item['hash']}")
            print(f"匹配记录数: {item['count']}")
            for record in item['records']:
                print(f"  - ID: {record['id']}, 文件: {record['file_name']}, 标题: {record['title']}")
    
    # 测试多个代码字符串列表
    print("\n" + "=" * 60)
    print("测试 2: 多个代码字符串列表搜索")
    print("=" * 60)
    
    code_list = [
        """30 std 0x1003042B0LL:\"~/Library/PubSub/Feeds/db.sqlite3\"""",
        """print(\"Hello World\")""",
        """import os"""
    ]
    
    print(f"输入代码列表 ({len(code_list)} 个):")
    for i, c in enumerate(code_list, 1):
        print(f"  {i}. {c.strip()}")
    print("-" * 60)
    
    result = search_malicious_code(code_list)
    
    print(f"状态: {result['state']}")
    print(f"消息: {result['message']}")
    print(f"找到的代码字符串数量: {result['count']}")
    
    if result['data']:
        for item in result['data']:
            print(f"\n代码字符串: {item['code_string'][:50]}...")
            print(f"哈希: {item['hash']}")
            print(f"匹配记录数: {item['count']}")
            for record in item['records']:
                print(f"  - ID: {record['id']}, 文件: {record['file_name']}, 标题: {record['title']}")
    else:
        print("\n所有代码字符串均未找到匹配数据")
