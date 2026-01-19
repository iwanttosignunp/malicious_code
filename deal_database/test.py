import requests
import json

API_URL = "http://localhost:8000"


def test_single_code_string():
    """测试单个代码字符串搜索"""
    print("=" * 60)
    print("测试 1: 单个代码字符串搜索")
    print("=" * 60)
    
    code = """v27 = !sub_10015620(v4) || !sub_10010E50();"""
    
    print(f"输入代码: {code.strip()}")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={"code_strings": code}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"状态: {result['state']}")
            print(f"消息: {result['message']}")
            print(f"找到的代码字符串数量: {result['count']}")
            
            if result['data']:
                for item in result['data']:
                    print(f"\n代码字符串: {item['code_string'][:50]}...")
                    print(f"匹配记录数: {item['count']}")
                    for record in item['records']:
                        print(f"  - ID: {record['id']}")
                        print(f"    文件: {record['file_name']}")
                        print(f"    标题: {record['title']}")
                        print(f"    描述: {record.get('description', 'N/A')}")
                        print(f"    代码片段: {record.get('malicious_code', 'N/A')[:100]}..." if record.get('malicious_code') and len(record.get('malicious_code', '')) > 100 else f"    代码片段: {record.get('malicious_code', 'N/A')}")
                        print(f"    哈希字符串: {record.get('hash_str', 'N/A')}")
        else:
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"错误: {e}")
    print()


def test_multiple_code_strings():
    """测试多个代码字符串列表搜索"""
    print("=" * 60)
    print("测试 2: 多个代码字符串列表搜索")
    print("=" * 60)
    
    code_list = [
        """v27 = !sub_10015620(v4) || !sub_10010E50(); bgdsa""",
        """print("Hello World")""",
        """import os"""
    ]
    
    print(f"输入代码列表 ({len(code_list)} 个):")
    for i, c in enumerate(code_list, 1):
        print(f"  {i}. {c.strip()}")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{API_URL}/search",
            json={"code_strings": code_list}
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"状态: {result['state']}")
            print(f"消息: {result['message']}")
            print(f"找到的代码字符串数量: {result['count']}")
            
            if result['data']:
                for item in result['data']:
                    print(f"\n代码字符串: {item['code_string'][:50]}...")
                    print(f"匹配记录数: {item['count']}")
                    for record in item['records']:
                        print(f"  - ID: {record['id']}")
                        print(f"    文件: {record['file_name']}")
                        print(f"    标题: {record['title']}")
                        print(f"    描述: {record.get('description', 'N/A')}")
                        print(f"    代码片段: {record.get('malicious_code', 'N/A')[:100]}..." if record.get('malicious_code') and len(record.get('malicious_code', '')) > 100 else f"    代码片段: {record.get('malicious_code', 'N/A')}")
                        print(f"    哈希字符串: {record.get('hash_str', 'N/A')}")
            else:
                print("\n所有代码字符串均未找到匹配数据")
        else:
            print(f"错误响应: {response.text}")
    except Exception as e:
        print(f"错误: {e}")
    print()




if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("恶意代码搜索 API 测试")
    print("=" * 60)
    print()
    
    # test_single_code_string()
    test_multiple_code_strings()

    print("=" * 60)
    print("所有测试完成")
    print("=" * 60)

