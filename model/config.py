import yaml
import re

def _resolve_variable_references(config_data, context=None):
    """
    解析配置中的变量引用
    Args:
        config_data: 配置数据（dict, list, str等）
        context: 上下文字典，用于查找变量值
    Returns:
        解析后的配置数据
    """
    if context is None:
        context = config_data
    
    if isinstance(config_data, dict):
        return {k: _resolve_variable_references(v, context) for k, v in config_data.items()}
    elif isinstance(config_data, list):
        return [_resolve_variable_references(item, context) for item in config_data]
    elif isinstance(config_data, str):
        # 匹配 ${section:key} 格式的变量引用
        pattern = r'\$\{([^:}]+):([^}]+)\}'
        
        def replace_var(match):
            section = match.group(1)
            key = match.group(2)
            # 从context中查找值
            if isinstance(context, dict) and section in context:
                section_data = context[section]
                if isinstance(section_data, dict) and key in section_data:
                    return str(section_data[key])
            # 如果找不到，保持原样
            return match.group(0)
        
        return re.sub(pattern, replace_var, config_data)
    else:
        return config_data

def load_config(config_path):
    """
    从指定路径加载 YAML 配置文件，并解析变量引用。
    """
    print("正在从 '{}' 加载配置...".format(config_path))
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            if config_data is None:
                raise ValueError("配置文件为空或格式错误。")
            # 解析变量引用
            config_data = _resolve_variable_references(config_data)
            return config_data
    except Exception as e:
        print("加载配置时发生错误: {}".format(e))
        raise