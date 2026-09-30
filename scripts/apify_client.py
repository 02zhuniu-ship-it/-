"""Apify 云浏览器采集客户端（真实浏览器渲染，绕过淘宝/闲鱼登录墙）。

用法：环境变量 APIFY_TOKEN = 你的 Apify API 密钥。
不配置 token 时，此模块的采集函数返回 (None)，上层自动降级为免登录探测。

Apify API 调用流程（用 requests 直连，无额外依赖）：
  1. POST      /v2/acts/{actorId}/runs    -> 发起一次 Actor 运行
  2. GET       /v2/actor-runs/{runId}     -> 轮询任务状态直到 SUCCEEDED
  3. GET       /v2/datasets/{datasetId}/items -> 拉取结果数据
"""

import json
import os
import time

import requests

import common


def get_token():
    """优先读环境变量 APIFY_TOKEN，其次读 config.json 里配置的令牌。
    这样即使云端无法设置 GitHub Secret，也能通过配置文件跑真实采集。"""
    env = os.environ.get("APIFY_TOKEN") or ""
    if env:
        return env
    return _cfg().get("data_source", {}).get("apify", {}).get("token", "")


def apify_token_configured():
    return bool(get_token())


def _cfg():
    return common.load_json(os.path.join(common.SCRIPT_DIR, "config.json"), {})


def _api_base():
    return os.environ.get("APIFY_API_BASE", "https://api.apify.com/v2")


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _poll_until_done(token, run_id, timeout=180):
    """轮询 Actor 运行状态，返回 run 对象。超时或失败抛异常。"""
    url = f"{_api_base()}/actor-runs/{run_id}"
    start = time.time()
    while True:
        r = requests.get(url, headers=_headers(token), timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"Apify 查询任务失败 HTTP {r.status_code}: {r.text[:200]}")
        data = r.json().get("data", {})
        status = data.get("status")
        if status in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
            if status != "SUCCEEDED":
                raise RuntimeError(f"Apify Actor 运行失败: status={status}, {data.get('defaultKeyValueStoreId', '')}")
            return data
        if time.time() - start > timeout:
            raise RuntimeError("Apify 采集超时")
        time.sleep(5)


def apify_run_search(actor_id, input_payload, token, keyword, timeout=180):
    """发起一次 Actor 搜索采集，返回商品条目列表。失败抛异常由上层记失败记录。

    注意：Apify POST /acts/{id}/runs 的 body 直接写 Actor 的输入参数，
    不要再用 {"input": ...} 包裹，否则 Actor 会把它当成一个叫 input 的字段而忽略。
    """
    run_url = f"{_api_base()}/acts/{actor_id}/runs"
    body = dict(input_payload)  # 直接作为 Actor 输入，不额外包 input 键
    r = requests.post(run_url, json=body, headers=_headers(token), timeout=30)
    if r.status_code != 201:
        raise RuntimeError(f"Apify 启动 Actor 失败 HTTP {r.status_code}: {r.text[:200]}")
    run_id = r.json()["data"]["id"]
    run = _poll_until_done(token, run_id, timeout=timeout)
    dataset_id = run.get("datasetId") or run.get("defaultDatasetId")
    if not dataset_id:
        raise RuntimeError("Apify 运行未返回数据集")
    items_url = f"{_api_base()}/datasets/{dataset_id}/items"
    rr = requests.get(items_url, headers=_headers(token), timeout=30)
    if rr.status_code != 200:
        raise RuntimeError(f"Apify 拉取结果失败 HTTP {rr.status_code}")
    items = rr.json()
    if not isinstance(items, list):
        items = [items] if items else []
    return items


def collect_taobao_by_apify(keywords, target, common_kw_text):
    """淘宝关键词搜索，返回标准 items 列表。未配置 token 返回 None。"""
    token = get_token()
    if not token:
        return None
    aconf = _cfg()["data_source"]["apify"]
    act = aconf["actor_taobao"]
    max_items = aconf["max_items_per_keyword"]
    timeout = aconf["timeout_seconds"]
    items = []
    for kw in keywords:
        if len(items) >= target:
            break
        # 该 Actor(WYOrcbcxOj3UjwdbP) 输入字段为 keywords[] + maxResultsPerKeyword
        payload = {"keywords": [kw], "maxResultsPerKeyword": max_items}
        try:
            raw = apify_run_search(act, payload, token, kw, timeout=timeout)
            for ent in raw or []:
                title = (ent.get("title") or "").strip()
                if not title:
                    continue
                price = ent.get("price") or ent.get("promoPrice") or ent.get("promoLabel")
                items.append({
                    "rank": len(items) + 1,
                    "title": title,
                    "price": str(price) if price is not None else "",
                    "sales": str(ent.get("searchPosition") or ""),
                    "shop": str(ent.get("shopName") or ""),
                    "city": "",
                    "img_url": ent.get("imageUrl") or (ent.get("images") or [None])[0] or "",
                    "detail_url": ent.get("url") or "",
                    "selling_points": [],
                    "fetch_status": "Apify真实采集",
                    "apify_raw": ent,
                })
        except Exception as e:
            common_kw_text(f"淘宝[{kw}]Apify失败: {e}")
    return items


def collect_xianyu_by_apify(keywords, target, common_kw_text):
    """闲鱼关键词搜索，返回标准 items 列表。未配置 token 返回 None。"""
    token = get_token()
    if not token:
        return None
    acon = _cfg()["data_source"]["apify"]
    act = acon["actor_xianyu"]
    max_items = acon["max_items_per_keyword"]
    timeout = acon["timeout_seconds"]
    items = []
    for kw in keywords:
        if len(items) >= target:
            break
        # 该 Actor(YLcsrxRnWKvfvrLIq) 输入字段为 keywords[] + maxItems
        payload = {"keywords": [kw], "maxItems": max_items}
        try:
            raw = apify_run_search(act, payload, token, kw, timeout=timeout)
            for ent in raw or []:
                title = (ent.get("title") or ent.get("name") or "").strip()
                if not title:
                    continue
                price = ent.get("price") or ent.get("currentPrice") or ent.get("priceText")
                items.append({
                    "rank": len(items) + 1,
                    "title": title,
                    "price": str(price) if price is not None else "",
                    "want": str(ent.get("want") or ent.get("favor") or ""),
                    "views": str(ent.get("views") or ""),
                    "seller": str(ent.get("seller") or ent.get("sellerName") or ent.get("sellerNick") or ""),
                    "trust": str(ent.get("credit") or ent.get("sellerCredit") or ""),
                    "city": str(ent.get("location") or ent.get("city") or ""),
                    "img_url": ent.get("image") or ent.get("images") or ent.get("mainImage") or "",
                    "detail_url": ent.get("url") or ent.get("detailUrl") or ent.get("link") or "",
                    "desc_full": str(ent.get("desc") or ent.get("description") or ""),
                    "fetch_status": "Apify真实采集",
                    "apify_raw": ent,
                })
        except Exception as e:
            common_kw_text(f"闲鱼[{kw}]Apify失败: {e}")
    return items