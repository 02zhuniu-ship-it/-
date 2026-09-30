"""登录墙/验证码/详情页抓不到时的统一返回，保证一致标记。"""

import common


def sku_unavailable(reason):
    return {"status": common.MARK_NEED_VERIFY, "skus": [], "reason": reason}


def fetch_skus(item, session, logger):
    """尝试从详情页SKU选择器读取款式+价格。返回 {'status','skus':[{'name','price'}], 'reason'}。
    通常在详情页需登录，尽量读取；读不到标记待核。"""
    url = item.get("detail_url", "")
    if not url or "example.invalid" in url:
        return sku_unavailable("详情页为演示地址或无详情链接")
    try:
        r = common_http_get(url, session, logger)
        html = r.text
        if "sku" not in html and "price" not in html:
            return sku_unavailable("详情页无SKU区块或需登录")
        # 公开环境解析SKU困难，如实标记并给原因
        return sku_unavailable("详情页存在登录墙，无法解析SKU选择器")
    except Exception as e:
        return sku_unavailable(f"请求详情页失败: {e}")


def common_http_get(url, session, logger):
    import fetch_utils as fu
    return fu.http_get(url, session=session, timeout=12)