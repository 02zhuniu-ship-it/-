"""采集辅助：真实的网络请求、简洁UA、降级处理。抓不到不造假。"""

import re
import json
import time
import requests

import common

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")


def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/json,application/xhtml+xml,*/*;q=0.8",
        "Referer": "https://www.taobao.com/",
    })
    return s


def http_get(url, session=None, timeout=15, **kw):
    """带重试与代理友好的 GET。返回 requests.Response；失败抛异常由上层记录。"""
    s = session or make_session()
    tries = kw.pop("tries", 2)
    last = None
    for i in range(tries):
        try:
            r = s.get(url, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code}")
        except requests.exceptions.RequestException as e:
            last = e
            time.sleep(1.2)
    raise last


def clean_text(raw):
    if not raw:
        return ""
    return re.sub(r"\s+", " ", raw).strip()


def narrow_price(text):
    """从原始字符串里尽量提取最低价/价格区间。返回 (价格文本, 是否确定)。"""
    if not text:
        return common.MARK_NEED_VERIFY, False
    m = re.search(r"([¥￥]?\s*\d+(\.\d+)?)\s*[-~到]\s*([¥￥]?\s*\d+(\.\d+)?)", text)
    if m:
        lo = m.group(1).replace("¥", "").replace("￥", "").strip()
        hi = m.group(3).replace("¥", "").replace("￥", "").strip()
        return f"{lo}~{hi}", True
    m = re.search(r"[¥￥]\s*(\d+(\.\d+)?)", text)
    if m:
        return m.group(0).strip(), True
    return common.MARK_NEED_VERIFY, False


def extract_title(html):
    m = re.search(r'<title>(.*?)</title>', html, re.S)
    return clean_text(m.group(1)) if m else common.MARK_NEED_VERIFY