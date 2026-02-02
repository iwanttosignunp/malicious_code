import psycopg2  # 如果你是GraalPy环境，记得换成 import pg8000.dbapi as psycopg2
import yaml
import sys
import os

def get_db_config(yaml_file='settings.yaml'):
    """从配置文件读取数据库配置"""
    if not os.path.exists(yaml_file):
        raise FileNotFoundError(f"找不到配置文件: {yaml_file}")

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

def delete_by_file_name(conn, table_name, file_name):
    """根据文件名删除数据"""
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE file_name = %s;", (file_name,))
        count = cur.fetchone()[0]
        
        if count == 0:
            print(f"未找到文件名为 '{file_name}' 的记录")
            cur.close()
            return
        print(f"找到 {count} 条匹配记录")
        cur.execute(f"DELETE FROM {table_name} WHERE file_name = %s;", (file_name,))
        deleted_count = cur.rowcount
        conn.commit()
        print(f"成功删除 {deleted_count} 条数据")
        cur.close()
    except Exception as e:
        print(f"删除失败: {e}")
        conn.rollback()

def truncate_table(conn, table_name):
    """删除表"""
    try:
        cur = conn.cursor()
        # DROP TABLE 会完全删除表
        print("正在执行 DROP TABLE 操作...")
        cur.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.commit()
        print(f"表 {table_name} 已删除")
        cur.close()
    except Exception as e:
        print(f"删除表失败: {e}")
        conn.rollback()


if __name__ == "__main__":
    conn = None
    try:
        config = get_db_config()
        table_name = config.pop('table_name')
        conn = psycopg2.connect(**config)
        print("数据库连接成功，准备删除表...")
        truncate_table(conn, table_name)
    except FileNotFoundError:
        print("错误: 未找到 settings.yaml 配置文件")
    except KeyError as e:
        print(f"错误: 配置文件中缺少必要的配置项 {e}")
    except psycopg2.Error as e:
        print(f"数据库连接错误: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")
    finally:
        if conn:
            conn.close()
            print("数据库连接已关闭")