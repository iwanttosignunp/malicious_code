'''
删除数据库
'''
import weaviate
import warnings
import os
import yaml

warnings.filterwarnings("ignore")

def load_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    # 读取配置文件
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings_path = os.path.join(project_root, 'settings.yaml')
    
    if not os.path.exists(settings_path):
        print(f"Error: Settings file not found at {settings_path}")
        return

    config = load_config(settings_path)

    # Weaviate 配置
    weaviate_config = config.get('weaviate', {})
    weaviate_url = weaviate_config.get('url', 'http://localhost:8011')
    class_name = weaviate_config.get('class_name', 'Security')

    print(f"Deleting class: {class_name}")

    try:
        client = weaviate.Client(url=weaviate_url)
        client.schema.delete_class(class_name)
        print(f"Class '{class_name}' deleted successfully.")
    except Exception as e:
        print(f"Error deleting class '{class_name}': {e}")

if __name__ == "__main__":
    main()