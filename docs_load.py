# 用户前端传来uploaded_file为streamlit格式，处理这个uploaded_file，判断其类型,加载内容为list[document]
import tempfile
import os
from typing import Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
# from file_utils.docx_processor import extract_text_from_docx
# from file_utils.pdf_mineru_convert import mineru_convert
from langchain_community.document_loaders import TextLoader

class DocumentLoad:
    def __init__(self, config):
        self.config = config
        self.magic_numbers = {
            'pdf': [b'%PDF'],
            'docx': [b'PK\x03\x04'],
            'jpg': [b'\xff\xd8\xff'],
            'png': [b'\x89PNG\r\n\x1a\n'],
            'txt': None
            }

    def load_document(self, uploaded_file):
        """加载上传的文档"""
        # 1. 保存创建的临时文件
        # Streamlit 上传的是内存对象，但 LangChain 的 Loader 需要物理路径
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
            # 上传的文件全部内容以 bytes 形式取出来
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name  # 获取临时路径
        print(tmp_path)
        try:
            # 2. 加载生成的临时文件
            # 2-1. 根据文件类型(基于后缀)动态选择加载器
            if uploaded_file.name.endswith('.pdf'):
                loader = PyPDFLoader(tmp_path)
            elif uploaded_file.name.endswith('.docx'):
                loader = Docx2txtLoader(tmp_path)  # 必须安装 docx2txt： pip install docx2txt
            elif uploaded_file.name.endswith('.txt'):
                loader = TextLoader(tmp_path, encoding='utf-8')
            elif uploaded_file.name.endswith('.md'):
                loader = TextLoader(tmp_path, encoding='utf-8')
            else:
                raise ValueError(f"不支持的文件类型: {uploaded_file.name}")

            # 2-2. 执行加载，返回 langchain 的 Document 文档对象列表
            documents = loader.load()
            return documents
        finally:
            # 3. 清理临时文件
            # 必须清理，否则server上会遗留大量的生成的临时文件
            if os.path.exists(tmp_path):
                # linux 写法：删除文件本质上是删除文件系统中的一个“硬链接”。当一个文件的链接数变为 0 时，磁盘空间才会被释放。
                # windows 也支持，等价于：os.remove(tmp_path)
                os.unlink(tmp_path)


# ===============================================================
    #
    # def detect_file_type_by_magic(self, file_path: str) -> Optional[str]:
    #     """通过魔数识别文件类型"""
    #     try:
    #         with open(file_path, 'rb') as f:
    #             header = f.read(16)
    #             for ext, signatures in self.magic_numbers.items():
    #                 if signatures is None: continue
    #                 for sig in signatures:
    #                     if header.startswith(sig):
    #                         return ext
    #             _, ext = os.path.splitext(file_path)
    #             if ext.lower() == '.txt': return 'txt'
    #             return None
    #     except Exception as e:
    #         print(f"不支持的文件类型: {e}")
    #         return None



                # def load_docs(self, uploaded_file):
    #     # 用户只能上传一个文件吗？
    #     with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
    #         tmp_file.write(uploaded_file.getvalue())
    #         tmp_path = tmp_file.name
    #     try:
    #         docs = []
    #         file_type = self.detect_file_type_by_magic(uploaded_file.name)
    #         if file_type == 'docx':
    #             docs = extract_text_from_docx(tmp_path)
    #         elif file_type == 'pdf':
    #             # miner u 解析
    #             success_file_paths = mineru_convert(tmp_path)
    #             for success_file_path in success_file_paths:
    #                 for success_file_name in os.listdir(success_file_path):
    #                     if success_file_name.endswith(".md"):
    #                         md_file_path = os.path.join(success_file_path, success_file_name)
    #                         loader = TextLoader(md_file_path, encoding="utf-8")
    #                         md_docs = loader.load()
    #                         docs.extend(md_docs)
    #         elif file_type == 'txt':
    #             pass
    #         else:
    #             raise ValueError("不支持的文件类型")
    #         return docs
    #     finally:
    #         if os.path.exists(tmp_path):
    #             os.unlink(tmp_path)
