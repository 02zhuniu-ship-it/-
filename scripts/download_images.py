"""下载商品主图 + 读取主图上的文字卖点。

真实主图下载用 requests；图片无法读取时记录「图片未获取/无法读取 + 原因」，不编造。
"""

import os
import re

import common
import fetch_utils as fu

# 常见宣传卖点关键词（用于在主图/标题文本中识别卖点文案）
SELLING_HINTS = ["装备包撤离", "首单免费", "永动机", "包", "免费", "特价", "秒", "多退"]


def download_image(item, save_dir, logger, session, idx=0):
    """下载主图到 save_dir。返回 {'file', 'ok', 'reason', 'selling_points'}。"""
    url = item.get("img_url", "")
    img_type = "主图"
    if not url or "example.invalid" in url:
        return _mark_no_image(item, img_type, "无有效主图URL或为演示地址", save_dir)
    try:
        r = fu.http_get(url, session=session, timeout=15)
        ext = _ext_from(url, r.headers.get("content-type", ""))
        filename = f"{item.get('rank', idx+1):02d}_{_safe(item.get('title',''))[:12]}_主图{ext}"
        fpath = os.path.join(save_dir, filename)
        with open(fpath, "wb") as f:
            f.write(r.content)
        selling = read_selling_points_from_text(item.get("title") or url)
        return {"file": os.path.relpath(fpath, common.ARCHIVE_ROOT), "ok": True,
                "reason": None, "selling_points": selling}
    except Exception as e:
        return _mark_no_image(item, img_type, f"下载失败: {e}", save_dir)


def _mark_no_image(item, img_type, reason, save_dir):
    return {"file": None, "ok": False, "reason": f"图片未获取 / {img_type}: {reason}",
            "selling_points": []}


def _ext_from(url, content_type):
    m = re.search(r"\.(jpe?g|png|webp|gif)", url.split("?")[0], re.I)
    if m:
        return ("." + m.group(1).lower()).replace("jpeg", "jpg")
    ct = content_type.split("/")[-1].split(";")[0]
    return f".{ct}" if ct in ("png", "jpeg", "jpg", "webp", "gif") else ".jpg"


def _safe(s):
    return re.sub(r"[\\/:*?\"<>|\s]", "_", s or "unnamed")


def read_selling_points_from_text(text):
    """从标题文字中识别卖点词。真实主图OCR在免登录环境往往不可用，这里先做文本级识别。"""
    pts = [k for k in SELLING_HINTS if k and k.lower() in (text or "").lower()]
    return pts