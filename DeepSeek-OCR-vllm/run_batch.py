import os
import glob
import subprocess
import re
import sys
import yaml

# 加载配置文件
def load_settings():
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.yaml')
    with open(settings_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

settings = load_settings()

PDF_DIRECTORY = settings['deepseek_ocr']['pdf_directory']  # 从 settings.yaml 读取
CONFIG_FILE = 'DeepSeek-OCR-vllm/config.py'
SCRIPT_TO_RUN = 'DeepSeek-OCR-vllm/run_dpsk_ocr_pdf.py'



def main():
    if not os.path.isdir(PDF_DIRECTORY):
        print(f"错误: 文件夹 '{PDF_DIRECTORY}' 未找到。")
        return
    if not os.path.isfile(CONFIG_FILE):
        print(f"错误: 配置文件 '{CONFIG_FILE}' 未找到。")
        return
    if not os.path.isfile(SCRIPT_TO_RUN):
        print(f"错误: 主脚本 '{SCRIPT_TO_RUN}' 未找到。")
        return
    pdf_files = glob.glob(os.path.join(PDF_DIRECTORY, '*.pdf'))

    print(f"找到了 {len(pdf_files)} 个 PDF 文件准备处理。")
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            original_config_content = f.read()
    except Exception as e:
        print(f"读取 '{CONFIG_FILE}' 失败: {e}")
        return

    for i, file_path in enumerate(pdf_files):
        normalized_path = file_path.replace('\\', '/')
        print(f"\n[{i+1}/{len(pdf_files)}] 正在处理: {normalized_path}")
        try:
            new_config_content = re.sub(
                r"INPUT_PATH\s*=\s*.*", 
                f"INPUT_PATH = '{normalized_path}'",
                original_config_content
            )
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(new_config_content)
        except Exception as e:
            print(f"  > 写入 '{CONFIG_FILE}' 失败: {e}")
            continue
        print(f"  > 正在运行 {SCRIPT_TO_RUN}...")
        try:
            subprocess.run([sys.executable, SCRIPT_TO_RUN], check=True, text=True)
            print(f"  > 成功处理: {normalized_path}")
        except subprocess.CalledProcessError as e:
            print(f"  > 处理 '{normalized_path}' 时出错 (返回码: {e.returncode}):")
            print(f"  > 错误信息: {e.stderr}")
        except Exception as e:
            print(f"  > 执行 {SCRIPT_TO_RUN} 失败: {e}")

    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(original_config_content)
        print(f"\n处理完成。已恢复 '{CONFIG_FILE}'。")
    except Exception as e:
        print(f"警告: 恢复 '{CONFIG_FILE}' 失败: {e}")

if __name__ == "__main__":
    main()