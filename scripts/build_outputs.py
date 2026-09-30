"""生成数据文件、淘宝/闲鱼分析PPT、闲鱼详情卡片图。

- 数据文件：data_taobao_search_v2.json / data_xianyu_detail.json（当天版+最新版）
- PPT：淘宝同行爆款分析-日期.pptx、闲鱼同行爆款分析-日期.pptx（分平台、两页/商品）
- 卡片图：闲鱼完整商品描述生成的白色详情卡片图
"""

import os
import json
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

import common
from common import MARK_NEED_VERIFY

DATA_PREFIX = {
    "taobao": "data_taobao_search_v2",
    "xianyu": "data_xianyu_detail",
}


def build_data_file(items_raw, platform, date_str, logger):
    """把采集原始数据整理成正式数据文件。返回数据dict。"""
    return {
        "date": date_str,
        "platform": platform,
        "demo": any(i.get("is_demo") for i in items_raw),
        "generated_at": common.now_china().isoformat(),
        "count": len(items_raw),
        "items": items_raw,
    }


def _tt_layout(platform):
    return ("淘宝", "同行爆款分析") if platform == "taobao" else ("闲鱼", "同行爆款分析")


def make_pptx(data, platform, save_path, logger, with_cards=False, cards_dir=None):
    """用 python-pptx 生成简洁分析PPT。第1页概览，后续每商品1页（闲鱼另拼详情页）。"""
    p = Presentation()
    p.slide_width = Inches(13.333)
    p.slide_height = Inches(7.5)
    blank = p.slide_layouts[6]
    pl_zh, pl_tag = _tt_layout(platform)

    # 封面页
    s = p.slides.add_slide(blank)
    tb = s.shapes.add_textbox(Inches(0.8), Inches(2.8), Inches(11.7), Inches(1.6))
    tf = tb.text_frame
    run = tf.add_paragraph()
    run.text = f"{pl_zh}同行爆款分析"
    run.font.size = Pt(36)
    run.font.bold = True
    run2 = tf.add_paragraph()
    run2.text = f"{data['date'] or common.today_str()}  ·  {data['count']} 个商品"
    run2.font.size = Pt(18)

    demo = data.get("demo")
    if demo:
        ds = s.shapes.add_textbox(Inches(0.8), Inches(4.6), Inches(11.7), Inches(0.6))
        d = ds.text_frame.add_paragraph()
        d.text = "* 本页为【演示数据】，仅用于验证链路"
        d.font.size = Pt(14)
        d.font.color.rgb = RGBColor(0xC0, 0x60, 0x40)

    items = data.get("items", [])
    for it in items:
        _add_item_slide(p, blank, pl_zh, pl_tag, it)
        if platform == "xianyu" and with_cards and cards_dir:
            _add_card_slide(p, blank, it, cards_dir)

    p.save(save_path)
    return save_path


def _add_item_slide(p, blank, pl_zh, pl_tag, it):
    s = p.slides.add_slide(blank)
    tb = s.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12.1), Inches(6.7))
    tf = tb.text_frame
    tf.word_wrap = True
    lines = [
        f"#{it.get('rank', '-')}  {it.get('title', MARK_NEED_VERIFY)}",
        f"价格：{it.get('price', MARK_NEED_VERIFY)}    销量/想要：{it.get('sales', it.get('want', MARK_NEED_VERIFY))}",
        f"店铺/卖家：{it.get('shop', it.get('seller', MARK_NEED_VERIFY))}    发货地：{it.get('city', MARK_NEED_VERIFY)}",
        f"SKU：{_fmt_skus(it.get('skus'))}",
        f"卖点：{'、'.join(it.get('selling_points', []) or []) or MARK_NEED_VERIFY}",
        f"链接：{it.get('detail_url', MARK_NEED_VERIFY)}",
    ]
    for i, ln in enumerate(lines):
        para = tf.add_paragraph()
        para.text = ln
        para.font.size = Pt(18 if i == 0 else 14)
        if i == 0:
            para.font.bold = True


def _add_card_slide(p, blank, it, cards_dir):
    """闲鱼第二页：展示完整详情卡片图。"""
    import re
    card_file = it.get("card_file")
    if not card_file:
        return
    full = os.path.join(cards_dir, os.path.basename(card_file))
    if not os.path.exists(full):
        return
    s = p.slides.add_slide(blank)
    try:
        from PIL import Image
        im = Image.open(full)
        w, h = im.size
    except Exception:
        w, h = 800, 1000
    # 归一化到高度7英寸，宽度按比例
    tgt_h = 6.8
    scale = tgt_h / h if h else 1
    disp_w = w * scale
    pic_x = (13.333 - disp_w) / 2
    s.shapes.add_picture(full, Inches(pic_x), Inches(0.3), height=Inches(tgt_h))
    tb = s.shapes.add_textbox(Inches(0.4), Inches(6.9), Inches(12.5), Inches(0.6))
    t = tb.text_frame.add_paragraph()
    t.text = f"商品详情（完整描述） - {it.get('title', '')}"
    t.font.size = Pt(12)


def _fmt_skus(skus):
    if not skus:
        return MARK_NEED_VERIFY
    if isinstance(skus, dict):
        # sku_fetcher 的返回结构 {'status','skus':[],'reason'}
        inner = skus.get("skus") or []
        if not inner:
            return skus.get("reason") or MARK_NEED_VERIFY
        return " / ".join(f"{s.get('name','')}:{s.get('price','')}" for s in inner)
    return " / ".join(f"{s.get('name','')}:{s.get('price','')}" for s in skus)


def make_card_image(desc_full, title, save_path, logger):
    """白色背景详情卡片图，完整展示描述、自动换行、不截断。"""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    font_path = _find_cjk_font()
    size_base = 22
    pad = 60
    try:
        title_font = ImageFont.truetype(font_path, int(size_base * 1.5))
        body_font = ImageFont.truetype(font_path, size_base)
    except Exception:
        title_font = body_font = ImageFont.load_default()

    desc = desc_full or MARK_NEED_VERIFY
    chars_per_line = 24
    lines = _wrap_lines(desc, chars_per_line)
    line_h = int(size_base * 1.6)
    title_h = 130
    body_h = len(lines) * line_h + 40
    img_w = 900
    img_h = title_h + body_h + pad * 2
    img = Image.new("RGB", (img_w, img_h), "white")
    d = ImageDraw.Draw(img)

    # 标题
    d.text((pad, pad), f"[商品详情] {title[:20]}", font=title_font, fill="#222222")
    y = pad + title_h
    for ln in lines:
        d.text((pad, y), ln, font=body_font, fill="#333333")
        y += line_h
    img.save(save_path)
    return save_path


def _wrap_lines(text, n):
    import re
    out = []
    for seg in text.split("\n"):
        seg = seg.strip()
        if not seg:
            out.append("")
            continue
        while len(seg) > n:
            out.append(seg[:n])
            seg = seg[n:]
        out.append(seg)
    return out


def _find_cjk_font():
    import glob
    cands = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "PingFang.ttc", "MicrosoftYaHei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/mnt/c/Windows/Fonts/msyh.ttc",
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    # 兜底：遍历常见字体目录找任意 .ttc/.ttf/.otf（含不一定带CJK的，尽力而为）
    for base in ["/usr/share/fonts", "/usr/local/share/fonts", "/usr/share/fonts/truetype"]:
        if not os.path.isdir(base):
            continue
        hits = glob.glob(base + "/**/*.[to]t[cf]", recursive=True)
        if hits:
            return sorted(hits)[0]
    return ""


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", choices=["taobao", "xianyu"], required=True)
    ap.add_argument("--task-date", default=common.today_str())
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--demo-root", default=common.SCRIPT_DIR)
    ap.add_argument("--archive-root", default=common.ARCHIVE_ROOT)
    ap.add_argument("--with-cards", action="store_true")  # 闲鱼详情卡片
    args = ap.parse_args()

    logger = common.setup_logger("build_" + args.platform)
    common.ensure_dir(args.archive_root)

    # 读取已采集数据
    if args.demo:
        raw_path = os.path.join(args.demo_root, f"_raw_{args.platform}_{common.today_str()}.json")
    else:
        raw_path = os.path.join(args.demo_root, f"_raw_{args.platform}_{common.today_str()}.json")
        if not os.path.exists(raw_path):
            raw_path = os.path.join(args.demo_root, f"_raw_{args.platform}_{common.today_str()}.json")
    items = []
    if os.path.exists(raw_path):
        items = common.load_json(raw_path, {}).get("items", [])

    # 抓取 SKU/款式+价格（真实详情页尝试；演示地址直接标记待核）
    import fetch_utils as fu
    import sku_fetcher
    session = fu.make_session()
    for it in items:
        if it.get("skus") is None:
            it["skus"] = sku_fetcher.fetch_skus(it, session, logger)

    # 下载商品主图（真实或演示图源），并读取卖点
    from download_images import download_image
    img_dir = common.archive_paths_for(args.task_date, args.platform, "商品图片")
    for idx, it in enumerate(items):
        r = download_image(it, img_dir, logger, session, idx=idx)
        if r["ok"]:
            it["img_file"] = r["file"]
            it["img_url_local"] = r["file"]
        if r["selling_points"]:
            it.setdefault("selling_points", [])
            for sp in r["selling_points"]:
                if sp not in it["selling_points"]:
                    it["selling_points"].append(sp)
        it["img_fetch_note"] = r["reason"] if not r["ok"] else None

    data = build_data_file(items, args.platform, args.task_date, logger)

    # 数据文件落地（当天版 + 最新版）
    data_dir = common.archive_paths_for(args.task_date, args.platform, "数据")
    prefix = DATA_PREFIX[args.platform]
    common.save_json(os.path.join(data_dir, f"{prefix}.json"), data)
    common.save_json(os.path.join(data_dir, f"{prefix}.latest.json"), data)

    # 详情卡片（仅闲鱼）
    cards_dir = None
    if args.platform == "xianyu" and args.with_cards:
        cards_dir = common.archive_paths_for(args.task_date, "xianyu", "详情卡片")
        for idx, it in enumerate(items):
            if not it.get("desc_full"):
                it["desc"] = "描述缺失"
                continue
            fname = f"详情卡片{idx+1}.png"
            fpath = os.path.join(cards_dir, fname)
            try:
                make_card_image(it.get("desc_full"), it.get("title"), fpath, logger)
                it["card_file"] = os.path.relpath(fpath, args.archive_root)
            except Exception as e:
                logger.warning(f"卡片生成失败 {fname}: {e}")

    # PPT
    ppt_dir = common.archive_paths_for(args.task_date, args.platform, "PPT报告")
    tag = {"taobao": "淘宝", "xianyu": "闲鱼"}[args.platform]
    ppt_path = os.path.join(ppt_dir, f"{tag}同行爆款分析-{args.task_date}.pptx")
    make_pptx(data, args.platform, ppt_path, logger,
              with_cards=(args.platform == "xianyu" and args.with_cards),
              cards_dir=cards_dir)

    logger.info(f"[{args.platform}] 输出完成，PPT: {ppt_path}, 商品 {len(items)}, 卡片目录开通: {bool(cards_dir)}")
    print(json.dumps({"platform": args.platform, "items": len(items),
                      "ppt": ppt_path, "has_cards": bool(cards_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()