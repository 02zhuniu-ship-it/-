"""闲鱼同行商品采集。与淘宝同理：真实尝试，抓不到如实标记，不编造。"""

import argparse
import json
import time

import common
import fetch_utils as fu
import apify_client


def collect_xianyu_real(keywords, exclude_shops, target, logger, failures, session):
    results = []

    # —— 1) 优先用 Apify 真实浏览器采集 ——
    def warn(txt):
        logger.warning(txt)
    try:
        apify_items = apify_client.collect_xianyu_by_apify(keywords, target, warn)
        if apify_items:
            filtered = [it for it in apify_items
                        if not any(excl and excl in it.get("seller", "") for excl in exclude_shops)]
            logger.info(f"[闲鱼] Apify 采集到 {len(filtered)} 个真实商品")
            return filtered
        if apify_client.apify_token_configured():
            logger.warning("[闲鱼] Apify 已配置但未采到数据")
    except Exception as e:
        logger.warning(f"[闲鱼] Apify 采集异常: {e}")
        failures.append({"step": "闲鱼采集", "keyword": "全部", "field": "商品列表",
                         "reason": f"Apify异常: {e}", "status": "失败"})

    # —— 2) 降级：免登录页面探测 ——
    for kw in keywords:
        if len(results) >= target:
            break
        try:
            logger.info(f"[闲鱼] 降级免登录探测关键词: {kw}")
            url = f"https://www.goofish.com/search?k={fu.requests.utils.quote(kw)}"
            r = fu.http_get(url, session=session, timeout=12)
            html = r.text
            if "card" not in html and "item" not in html:
                raise RuntimeError("页面无商品数据（登录/风控墙）")
            raise RuntimeError("闲鱼公开搜索接口返回受限，无法免登录解析结构化商品数据")
        except Exception as e:
            logger.warning(f"[闲鱼] 关键词[{kw}]失败: {e}")
            failures.append({
                "step": "闲鱼采集", "keyword": kw,
                "field": "商品列表", "reason": str(e),
                "tried": "GET goofish.com/search", "status": "失败",
            })
            time.sleep(1)
    return results


def collect_xianyu_demo(keywords, logger):
    logger.info("[闲鱼] 使用【演示数据】验证链路")
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
                "title": f"[演示] 闲鱼 {kw} 同行 {i}号",
                "price": f"{15.0 + i * 6:.1f}",
                "want": f"{20 * i}人想要",
                "views": f"{300 * i}",
                "seller": f"卖家{i}（演示）",
                "trust": "芝麻信用良好",
                "city": "广东深圳",
                "img_url": f"https://picsum.photos/seed/xy{i}{n}/400/400",
                "detail_url": f"https://example.invalid/demo/xianyu/{n}",
                "desc_full": (
                    f"[演示数据] 超自然行动组 摸金陪玩 服务说明：\n"
                    f"1. 全程陪伴摸金玩法，装备包撤离无忧。\n"
                    f"2. 首单免费体验，约{i}小时起。\n"
                    f"3. 支持语音连麦，随时在线，打包更优惠。\n"
                    f"4. 玩家口碑好评多，回头率高。\n"
                    f"（此为链路演示文本，非真实商品描述）"
                ),
                "fetch_status": "演示数据",
            })
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-date", default=common.today_str())
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    logger = common.setup_logger("xianyu")
    cfg = common.load_json(common.SCRIPT_DIR + "/config.json", {})
    kw_cfg = cfg.get("keywords", {})
    keywords = kw_cfg.get("example_demo", kw_cfg.get("xianyu")) if args.demo else kw_cfg.get("xianyu", [])
    target = cfg.get("target_counts", {}).get("xianyu", 10)
    exclude = cfg.get("my_shop_exclude", {}).get("xianyu", [])

    failures = []
    if args.demo:
        items = collect_xianyu_demo(keywords, logger)
        fetches = [{"is_demo": True, "step": "闲鱼采集", "reason": "演示数据未走真实网络"}]
    else:
        session = fu.make_session()
        items = collect_xianyu_real(keywords, exclude, target, logger, failures, session)
        fetches = failures

    out = {
        "date": args.task_date,
        "platform": "xianyu",
        "demo": bool(args.demo),
        "items": items,
        "fetches": fetches or failures,
    }
    common.save_json(common.SCRIPT_DIR + f"/_raw_xianyu_{common.today_str()}.json", out)
    logger.info(f"[闲鱼] 采集完成，共 {len(items)} 个商品，失败 {len(failures)} 条")
    print(json.dumps({"count": len(items), "failures": len(failures)}, ensure_ascii=False))


if __name__ == "__main__":
    main()