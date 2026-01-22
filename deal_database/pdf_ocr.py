import os
import glob
import shutil
from magic_pdf.data.data_reader_writer import FileBasedDataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze

def deal_pdf(pdf_file_path):
    file_name = os.path.basename(pdf_file_path)
    name_without_suff = os.path.splitext(file_name)[0]
    local_image_dir = "output/images"
    local_md_dir = "output"
    
    os.makedirs(local_image_dir, exist_ok=True)
    os.makedirs(local_md_dir, exist_ok=True)
    
    image_writer = FileBasedDataWriter(local_image_dir)

    with open(pdf_file_path, "rb") as f:
        pdf_bytes = f.read()
    
    ds = PymuDocDataset(pdf_bytes)
    print(f"正在进行 OCR 分析: {file_name} ...")
    
    infer_result = ds.apply(doc_analyze, ocr=True)
    
    pipe_result = infer_result.pipe_ocr_mode(image_writer)

    output_md_path = os.path.join(local_md_dir, f"{name_without_suff}.md")
    
    try:
        content_list = pipe_result.get_content_list(image_writer)
    except TypeError:
        content_list = pipe_result.get_content_list()

    with open(output_md_path, "w", encoding="utf-8") as f:
        for block in content_list:
            text_content = block.get("text", "")
            block_type = block.get("type", "")

            if text_content:
                if block_type in ["title", "header"]:
                    f.write(f"## {text_content}\n\n")
                else:
                    f.write(f"{text_content}\n\n")

    if os.path.exists(local_image_dir):
        try:
            shutil.rmtree(local_image_dir)
        except Exception:
            pass
    for extra_file in ["config.yaml", "log.txt"]:
                extra_path = os.path.join(local_md_dir, extra_file)
                if os.path.exists(extra_path):
                    try:
                        os.remove(extra_path)
                        print(f"已删除: {extra_path}")
                    except Exception as e:
                        print(f"删除 {extra_file} 失败: {e}")

    print(f"处理完成: {output_md_path}")

if __name__ == "__main__":
    data_folder = "data"
    if not os.path.exists(data_folder):
        print(f"错误: 文件夹 '{data_folder}' 不存在")
    else:
        pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))
        if not pdf_files:
            print(f"没有找到 PDF 文件")
        else:
            print(f"共发现 {len(pdf_files)} 个文件")
            for pdf_path in pdf_files:
                try:
                    deal_pdf(pdf_path)
                except Exception as e:
                    import traceback
                    print(f"处理文件 {pdf_path} 失败: {e}")
                    traceback.print_exc()
            print("\n所有任务执行完毕。")