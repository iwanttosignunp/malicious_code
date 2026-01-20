import os
# os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-75110b0c-02dd-489d-b333-df66a28e2085"
# os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-7945f2fb-fb58-4532-b5a4-26a091441f58"
# os.environ["LANGFUSE_HOST"] = "http://localhost:3000"
# from langfuse.openai import OpenAI, AsyncOpenAI
from openai import OpenAI, AsyncOpenAI
from typing import Any
import re
import json
import os
import hashlib
from config import load_config
from extract_prompt import (
    EXTRACT_CODE_SYSTEM_PROMPT,
    EXTRACT_CODE_USER_PROMPT,
    EXTRACT_MALICIOUS_SYSTEM_PROMPT,
    EXTRACT_MALICIOUS_USER_PROMPT,
    MODIFIED_PROMPT,
    DESCRIBE_MALICIOUS_CODE_PROMPT
)

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

def split_and_clean_code_prompt(code_prompt: str):
    raw_fragments = code_prompt.split("&&&")
    cleaned_fragments = []
    for fragment in raw_fragments:
        lines = fragment.splitlines()
        non_empty_lines = [line.strip('\n') for line in lines if line.strip()]
        cleaned_fragment = '\n'.join(non_empty_lines)
        if cleaned_fragment.strip():
            cleaned_fragments.append(cleaned_fragment)
    return cleaned_fragments

def read_md_and_split_by_h1(file_path: str):
    """读取MD文件并按一级标题分割，返回(标题, 内容)列表"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 按一级标题分割（匹配# 开头的标题）
    h1_pattern = re.compile(r'^#\s+.+', re.MULTILINE)
    h1_matches = list(h1_pattern.finditer(content))
    
    fragments = []
    if h1_matches:
        for i in range(len(h1_matches)):
            match = h1_matches[i]
            title = match.group().strip('# ').strip()
            start = match.end()
            end = h1_matches[i+1].start() if i+1 < len(h1_matches) else len(content)
            fragment_content = content[start:end].strip()
            if fragment_content:
                fragments.append((title, fragment_content))
    else:
        # 无一级标题的情况，使用默认标题
        fragments.append(("默认标题", content.strip()) if content.strip() else ("默认标题", ""))
    
    return fragments

def is_valid_malicious_code(code: str) -> bool:
    """
    判断是否为有效恶意代码
    规则：非空、不是提示文本（如"未发现恶意代码"、"无"等）、有实际代码内容
    """
    if not code or not code.strip():
        return False
    
    # 转换为小写便于判断
    code_lower = code.strip().lower()
    
    # 定义无效内容的关键词
    invalid_keywords = [
        "未发现恶意代码", "无恶意代码", "没有恶意代码", "无相关代码",
        "no malicious code", "not found", "none", "n/a", "无", "空",
        "未检测到", "不存在", "没有发现", "暂无", "未提取到代码片段"
    ]
    
    # 检查是否包含无效关键词
    for keyword in invalid_keywords:
        if keyword in code_lower:
            return False
    
    # 检查是否有实际代码内容（至少包含一些代码特征）
    code_features = [
        r'\{|\}', r'\(|\)', r';', r'=', r'\+', r'-', r'\*', r'/',
        r'if|else|for|while|function|class',  # 编程语言关键字
        r'cmd|powershell|bash|python|php|java|c\+\+|c#',  # 编程语言
        r'http|https|ftp|ip|domain|url',  # 网络相关
        r'exec|system|process|file|registry',  # 系统操作
        r'encrypt|decrypt|malware|virus|trojan'  # 恶意行为
    ]
    
    # 如果内容长度较短且没有代码特征，判定为无效
    if len(code.strip()) < 10:
        has_feature = any(re.search(pattern, code) for pattern in code_features)
        if not has_feature:
            return False
    
    return True

def write_single_item_to_jsonl(data_item, output_file):
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 追加写入单条数据
    with open(output_file, 'a', encoding='utf-8') as f:
        json.dump(data_item, f, ensure_ascii=False)
        f.write('\n')

def init_jsonl_file(output_file):
    """初始化JSONL文件"""
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(output_file, 'w', encoding='utf-8') as f:
        pass

def main(hash = "hash"):
    # 配置加载
    SETTINGS_FILE = "settings.yaml"
    config = load_config(SETTINGS_FILE)
    llm_client = ChatModel(config['models']['chat_model'])
    
    # 从配置文件读取批量处理路径
    batch_config = config.get('batch_processing', {})
    output_folder = batch_config.get('output_folder', 'output')
    output_file_name = batch_config.get('output_file_name', 'malicious_code_results.jsonl')
    
    # 构建输出文件路径
    output_file = os.path.join(output_folder, output_file_name)
    
    # 初始化JSONL文件（清空原有内容）
    init_jsonl_file(output_file)
    
    # 获取output_folder下所有.md文件
    if not os.path.exists(output_folder):
        print(f"输入文件夹不存在: {output_folder}")
        return
    
    md_files = [f for f in os.listdir(output_folder) if f.endswith('.md')]
    
    if not md_files:
        print(f"在文件夹 {output_folder} 中未找到任何.md文件")
        return
    
    print(f"找到 {len(md_files)} 个MD文件待处理")
    print(f"输入文件夹: {output_folder}")
    print(f"输出文件夹: {output_folder}")
    print(f"输出文件: {output_file}")
    print("=" * 60)
    
    # 全局统计
    global_total_written = 0
    global_total_skipped = 0
    
    # 遍历处理每个MD文件
    for file_idx, md_file in enumerate(md_files, 1):
        md_file_path = os.path.join(output_folder, md_file)
        print(f"\n🔄 [{file_idx}/{len(md_files)}] 正在处理: {md_file}")
        
        try:
            # 按一级标题分割，获取(标题, 内容)列表
            text_fragments = read_md_and_split_by_h1(md_file_path)
            
            # 单文件统计
            file_written = 0
            file_skipped = 0
            
            for idx, (title, text_content) in enumerate(text_fragments, 1):
                try:
                    code_prompt = llm_client.get_chat(
                        system_prompt=EXTRACT_CODE_SYSTEM_PROMPT,
                        user_prompt=EXTRACT_CODE_USER_PROMPT.format(TEXT=text_content)
                    )
                    code_fragments = split_and_clean_code_prompt(code_prompt)
                    
                    # 处理每个代码片段
                    for code_idx, code_fragment in enumerate(code_fragments, 1):
                        if not code_fragment.strip():
                            file_skipped += 1
                            continue
                        # 提取恶意代码相关信息
                        malicious_code = llm_client.get_chat(
                            system_prompt=EXTRACT_MALICIOUS_SYSTEM_PROMPT,
                            user_prompt=EXTRACT_MALICIOUS_USER_PROMPT.format(CODE=code_fragment, TEXT=text_content)
                        )
                        malicious_code = re.sub(r'[\u4e00-\u9fa5]', '', malicious_code)
                        malicious_code_list = malicious_code.split('<SEPARATOR>')
                        
                        for single_malicious_code in malicious_code_list:
                            if not single_malicious_code.strip():
                                continue

                            # 修正代码格式
                            modified_code = llm_client.get_chat(
                                user_prompt=MODIFIED_PROMPT.format(CODE=single_malicious_code)
                            )
                            modified_code = modified_code.strip('`\n')
                            # 检查是否为有效恶意代码
                            if not is_valid_malicious_code(modified_code):
                                file_skipped += 1
                                continue
                            
                            # 生成format_code：去掉所有换行和空格
                            format_code = re.sub(r'[\s\n]+', '', modified_code)
                            
                            # 生成代码描述
                            describe_content = llm_client.get_chat(
                                user_prompt=DESCRIBE_MALICIOUS_CODE_PROMPT.format(CODE=modified_code, TEXT=text_content)
                            )

                            # 构建数据条目
                            data_item = {
                                "file_name": md_file,
                                "title": title,
                                "malicious_code": modified_code.strip(),
                                "describe": describe_content,
                                "format_code": format_code,
                                "hash": hash
                            }
                            
                            # 立即写入JSONL文件
                            write_single_item_to_jsonl(data_item, output_file)
                            print(f"   + 已提取并写入: {title}")
                            file_written += 1
                        
                except Exception as e:
                    print(f"处理标题 '{title}' 时出错: {str(e)}")
                    file_skipped += 1
                    continue
            
            # 更新全局统计
            global_total_written += file_written
            global_total_skipped += file_skipped
            
            print(f" 文件处理完成 - 写入: {file_written} 条, 跳过: {file_skipped} 条")
            
        except Exception as e:
            print(f" 处理文件 {md_file} 时出错: {str(e)}")
            continue
    
    print("\n" + "=" * 60)
    print(f"处理完成！")
    print(f"总体统计信息:")
    print(f"   - 处理文件数: {len(md_files)} 个")
    print(f"   - 成功写入有效恶意代码: {global_total_written} 条")
    print(f"   - 跳过无效/空数据: {global_total_skipped} 条")
    print(f"   - 输出文件: {output_file}")

if __name__ == "__main__":
    main(hash = "hash")