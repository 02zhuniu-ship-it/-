"""通用工具库：路径、日期、日志、去重、任务记录（数据库）。"""

import json
import os
import hashlib
import logging
from datetime import datetime, timedelta

# ---------- 常量 ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)          # ecommerce-watch/
ARCHIVE_ROOT = os.path.join(PROJECT_ROOT, "archive")  # 云端归档
DB_DIR = os.path.join(ARCHIVE_ROOT, "_system")        # 数据库/索引（不入业务日目录）
TASKS_DB = os.path.join(DB_DIR, "tasks.json")         # 自动化任务记录
DEDUP_DB = os.path.join(DB_DIR, "dedup.json")         # 文件去重表
MANIFEST_DB = os.path.join(DB_DIR, "manifest.json")   # 首页/入库索引

CHINA_TZ = "Asia/Shanghai"
MARK_NEED_VERIFY = "待核验"   # 抓不到又不允许猜的占位符


def now_china() -> datetime:
    """北京时间。沙盒无系统时区感知时用 UTC+8 换算，保证展示为北京时间。"""
    return datetime.utcnow() + timedelta(hours=8)


def today_str() -> str:
    return now_china().strftime("%Y-%m-%d")


def setup_logger(name="ew"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(h)
    return logger


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def sha256_file(path):
    """计算文件哈希，用于去重。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path, default=None):
    if default is None:
        default = []
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- 任务记录（数据库） ----------
def load_tasks():
    return load_json(TASKS_DB, [])


def record_task(task):
    """写入一条自动化任务执行记录。task 为 dict。"""
    tasks = load_tasks()
    tasks.append(task)
    save_json(TASKS_DB, tasks)
    return task


# ---------- 文件去重 ----------
def load_dedup():
    return load_json(DEDUP_DB, {})


def is_duplicate(file_hash, size):
    """在 dedup 表中按 内容哈希+大小 判断是否已上传过（去重）。跟路径无关。"""
    db = load_dedup()
    rec = db.get(file_hash)
    if not rec:
        return False
    return rec.get("size") == size


def mark_ingested(rel_archive_path, file_hash, size, task_name):
    """记录已入库文件，供去重。"""
    db = load_dedup()
    db[file_hash] = {"path": rel_archive_path, "size": size, "task": task_name}
    save_json(DEDUP_DB, db)


def dedup_stats():
    db = load_dedup()
    return len(db)


# ---------- 入库清单（Manifest） ----------
def load_manifest():
    return load_json(MANIFEST_DB, {})


def save_manifest(manifest):
    save_json(MANIFEST_DB, manifest)


def archive_paths_for(date_str, platform, file_type):
    """返回该文件应归档的绝对目录。platform: taobao/xianyu/failure 等。"""
    return ensure_dir(os.path.join(ARCHIVE_ROOT, date_str, platform, file_type))