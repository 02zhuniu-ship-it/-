"""淘宝同行商品采集。

真实逻辑：尝试从淘宝公开搜索页面/接口抓取。淘宝有登录墙与风控，
云端环境常拿不到真实数据 → 如实标记「待核」，并写入失败记录，绝不编造。

`--demo` 参数：生成本地演示数据（明确标注"演示数据"），仅用于本地验证整条链路跑通。
"""

import argparse
import json
import time

import common
import fetch_utils as fu
import apify_client


def collect_taobao_real(keywords, exclude_shops, target, logger, failures, session):
    """尝试真实抓取：优先 Apify 云浏览器，失败降级免登录探测。返回商品列表。"""

    # —— 1) 优先用 Apify 真实浏览器采集 ——
    def warn(txt):
        logger.warning(txt)
    try:
        apify_items = apify_client.collect_taobao_by_apify(keywords, target, warn)
        if apify_items:
            # 过滤掉自己的店铺
            filtered = [it for it in apify_items
                        if not any(excl and excl in it.get("shop", "") for excl in exclude_shops)]
            logger.info(f"[淘宝] Apify 采集到 {len(filtered)} 个真实商品")
            return filtered
        if apify_client.apify_token_configured():
            logger.warning("[淘宝] Apify 已配置但未采到数据，按失败记录")
    except Exception as e:
        logger.warning(f"[淘宝] Apify 采集异常: {e}")
        failures.append({"step": "淘宝采集", "keyword": "全部", "field": "商品列表",
                         "reason": f"Apify异常: {e}", "status": "失败"})

    # —— 2) 降级：免登录页面探测 ——
    results = []
    got = 0
    for kw in keywords:
        if got >= target:
            break
        try:
            logger.info(f"[淘宝] 降级免登录探测关键词: {kw}")
            url = f"https://s.taobao.com/search?q={fu.requests.utils.quote(kw)}"
            r = fu.http_get(url, session=session, timeout=12)
            html = r.text
            if "item" not in html:
                raise RuntimeError("页面无商品结构化数据（登录/风控墙）")
            raise RuntimeError("淘宝搜索公开接口返回受限，无法免登录解析结构化商品数据")
        except Exception as e:
            logger.warning(f"[淘宝] 关键词[{kw}]失败: {e}")
            failures.append({
                "step": "淘宝采集", "keyword": kw,
                "field": "商品列表", "reason": str(e),
                "tried": "GET s.taobao.com/search", "status": "失败",
            })
            time.sleep(1)
    logger.info(f"[淘宝] 真实采集结束，成功获取 {got} 个商品")
    return results


def collect_taobao_demo(keywords, logger):
    """本地演示数据（明确标注），用于验证全链路。"""
    logger.info("[淘宝] 使用【演示数据】验证链路")
    items = []
    n = 0
    for kw in keywords:
        for i in range(1, 4):
            if len(items) >= 10:
                return items
            n += 1
            items.append({
                "is_demo": True,
                "rank": len(items) + 1,
                "title": f"[演示] {kw} 同行款 {i}号 摸金陪玩装备",
                "price": f"{9.9 + i * 5:.1f}",
                "sales": f"{100 * i}",
                "shop": f"演示店铺{i}",
                "city": "浙江杭州",
                "tags": ["演示", "装备包撤离"],
                "img_url": f"https://picsum.photos/seed/tb{i}{n}/400/400",
                "detail_url": f"https://example.invalid/demo/taobao/{n}",
                "selling_points": ["装备包撤离", "首单免费"],
                "fetch_status": "演示数据",
            })
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-date", default=common.today_str())
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    logger = common.setup_logger("taobao")
    cfg = common.load_json(common.SCRIPT_DIR + "/config.json", {})
    kw_cfg = cfg.get("keywords", {})

    keywords = kw_cfg.get("example_demo", kw_cfg.get("taobao")) if args.demo else kw_cfg.get("taobao", [])
    target = cfg.get("target_counts", {}).get("taobao", 10)
    exclude = cfg.get("my_shop_exclude", {}).get("taobao", [])

    failures = []
    if args.demo:
        items = collect_taobao_demo(keywords, logger)
        fetches = [{"is_demo": True, "step": "淘宝采集", "reason": "演示数据未走真实网络"}]
    else:
        session = fu.make_session()
        items = collect_taobao_real(keywords, exclude, target, logger, failures, session)
        fetches = failures

    # 保留当天版本 + 最新版本
    for suffix in ["", ".latest"]:
        # 写入已采集原始数据；后续交给 build_outputs 生成正式 data_*.json
        pass

    out = {
        "date": args.task_date,
        "platform": "taobao",
        "demo": bool(args.demo),
        "items": items,
        "fetches": fetches or failures,
    }
    common.save_json(common.SCRIPT_DIR + f"/_raw_taobao_{common.today_str()}.json", out)
    logger.info(f"[淘宝] 采集完成，共 {len(items)} 个商品，失败 {len(failures)} 条")

    # 输出供 run_all 汇总
    print(json.dumps({"count": len(items), "failures": len(failures)}, ensure_ascii=False))


if __name__ == "__main__":
    main()