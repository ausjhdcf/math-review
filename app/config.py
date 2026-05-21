# app/config.py
import os

QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen-vl-plus")
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_BUCKET = "math-images"

UPLOAD_TYPES = ["错题", "笔记", "讲义"]
SUBJECTS = ["高数", "线代", "概率论", "待AI识别"]
ERROR_CATEGORIES = ["计算粗心", "概念不清", "方法选错", "审题失误", "不会做"]

MVP_USER_ID = "00000000-0000-0000-0000-000000000000"
