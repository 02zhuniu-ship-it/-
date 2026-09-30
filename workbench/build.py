# -*- coding: utf-8 -*-
"""把 archive 归档数据编译成一个双击即看的本地工作台 (工作台.html)。

用法:
    python3 workbench/build.py
输出:
    workbench/工作台.html   （双击它就能看，无需联网、无需服务器）
说明:
    - 图片用相对路径 <img>，本地双击 HTML 就能正常显示（不走 fetch，无 CORS 限制）
    - PPT / 数据文件用相对路径 <a download>，点击即可下载到电脑
"""
import os, json, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ecommerce-watch/
ARCHIVE = os.path.join(ROOT, "archive")
MANIFEST = os.path.join(ARCHIVE, "_system", "manifest.json")


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fmt_size(path):
    try:
        n = os.path.getsize(path)
        return f"{n/1024:.0f}KB" if n < 1024 * 1024 else f"{n/1024/1024:.1f}MB"
    except Exception:
        return ""


def rel(p):
    # 相对 workbench/ 的路径，并对每个路径段做 URL 编码（处理中括号、空格、中文等）
    from urllib.parse import quote
    rel_from_root = os.path.relpath(p, ROOT).replace(os.sep, "/")
    parts = rel_from_root.split("/")
    return "../" + "/".join(quote(part) for part in parts)


def main():
    today = sys.argv[1] if len(sys.argv) > 1 else sorted(
        os.listdir(ARCHIVE))[-1] if os.path.isdir(ARCHIVE) else "2026-09-30"
    today = today.strip("/") if os.path.isdir(today) else today

    manifest = {}
    try:
        manifest = json.load(open(MANIFEST, encoding="utf-8"))
    except Exception:
        manifest = {}

    dates = [d for d in manifest.keys()] or [today]
    dates.sort(reverse=True)

    cards = []   # 各日期板块
    for d in dates:
        g = manifest.get(d, {})
        if not g:
            continue
        plat_html = []
        for plat_key in ("taobao", "xianyu"):
            label = {"taobao": "淘宝", "xianyu": "闲鱼"}[plat_key]
            color = {"taobao": "#c47046", "xianyu": "#4a9a7a"}[plat_key]
            pdict = g.get(plat_key, {})
            if not pdict:
                continue
            block = []
            blocks = {"商品图片": _grid_images(pdict.get("商品图片", []), color),
                      "详情卡片": _grid_images(pdict.get("详情卡片", []), color, 3),
                      "PPT报告": _download_list(pdict.get("PPT报告", []), "PPT"),
                      "数据": _download_list(pdict.get("数据", []), "JSON")}
            for title in ("商品图片", "详情卡片", "PPT报告", "数据"):
                if blocks[title]:
                    block.append(f'<div class="sub"><div class="subtitle">{title}</div>{blocks[title]}</div>')
            if block:
                cnt = sum(len(pdict.get(k, [])) for k in pdict)
                plat_html.append(f'<div class="plat-card"><div class="plat-head"><span class="dot" style="background:{color}"></span><b style="color:{color}">{label}</b><span class="count">{cnt} 个文件</span></div>{"".join(block)}</div>')
        # 失败记录
        fail = g.get("失败记录", {})
        if fail:
            for ty, files in fail.items():
                for f in files:
                    plat_html.append(f'<div class="plat-card"><div class="plat-head"><span class="dot" style="background:#b0564f"></span><b style="color:#b0564f">失败记录</b></div><div class="sub">{_download_list([f], "MD")}<div style="color:#9c9090;font-size:12px">未抓到的数据会如实标注「待核验」，绝不编造</div></div></div>')
        if plat_html:
            cards.append(f'<div class="day"><div class="day-title">📆 {d}</div>{"".join(plat_html)}</div>')

    status_html = _status(today, manifest, dates)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>个人工作台 · 电商竞品自动分析</title>
<style>
:root{{--bg:#f5f1f0;--card:#fff;--line:#e7e0de;--text:#3a3434;--sub:#7a6e6e;--weak:#9c9090;--accent:#a06b6b}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px 18px 90px}}
header{{margin-bottom:20px}}
header h1{{font-size:22px}} header .date{{color:var(--sub);font-size:13px}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;margin-bottom:18px;box-shadow:0 4px 18px rgba(58,52,52,.05)}}
h2{{font-size:15px;margin-bottom:14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}
.stat{{background:#f8f4f3;border:1px solid var(--line);border-radius:12px;padding:14px;text-align:center}}
.stat .num{{font-size:26px;font-weight:700}} .stat .lab{{font-size:12px;color:var(--sub)}}
.day{{margin-bottom:22px}}
.day-title{{font-size:17px;font-weight:700;margin-bottom:12px}}
.plat-card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}}
.plat-head{{display:flex;align-items:center;gap:8px;margin-bottom:12px}}
.plat-head .dot{{width:10px;height:10px;border-radius:99px}}
.plat-head .count{{margin-left:auto;color:var(--weak);font-size:12px}}
.sub{{margin-bottom:12px}}
.subtitle{{font-size:12px;color:var(--sub);margin-bottom:8px}}
.imgs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px}}
.imgs.cardgrid{{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}}
.imgbox{{background:#f8f4f3;border:1px solid var(--line);border-radius:10px;padding:6px;text-align:center}}
.imgbox img{{width:100%;height:110px;object-fit:cover;border-radius:6px;cursor:zoom-in}}
.imgbox .cap{{font-size:11px;color:var(--sub);margin-top:4px;word-break:break-all}}
.dl{{display:flex;flex-wrap:wrap;gap:8px}}
.dl a{{display:inline-flex;align-items:center;gap:6px;background:#f8f4f3;border:1px solid var(--line);border-radius:8px;padding:6px 12px;color:var(--accent);text-decoration:none;font-size:12px}}
.dl a:hover{{background:#f0e8e8}}
.dl .tg{{font-size:11px;color:#fff;background:var(--accent);border-radius:4px;padding:1px 6px}}
.empty{{color:var(--weak);font-size:13px;padding:12px;text-align:center}}
.note{{background:#fdf3f1;border:1px solid #ecd7d2;border-radius:12px;padding:14px;color:#8a5a50;font-size:13px;margin-bottom:18px}}
.note b{{color:#b0564f}}
.lightbox{{position:fixed;inset:0;background:rgba(0,0,0,.75);display:none;align-items:center;justify-content:center;z-index:99;cursor:zoom-out}}
.lightbox img{{max-width:90%;max-height:90%;border-radius:8px}}
</style>
</head>
<body>
<div class="wrap">
<header><h1>📊 个人工作台</h1><div class="date">电商竞品自动采集 · 本地归档 · 双击即看</div></header>
<div class="note">⚠️ <b>这页是演示数据。</b>真实数据需要先登录采集并保存到本机 <code>archive/</code> 文件夹后，重跑一次工作台生成即可看到最新结果。图片/PPT/数据都在这台电脑上，点开即看。</div>

{status_html}

<div id="days">{''.join(cards) if cards else '<div class="panel"><div class="empty">暂无归档数据</div></div>'}</div>
</div>
<div class="lightbox" id="lb" onclick="this.style.display='none'"><img id="lbimg" alt=""></div>
<script>
var m = {json.dumps(manifest, ensure_ascii=False)};
function zoom(img){{var lb=document.getElementById('lb');var i=document.getElementById('lbimg');i.src=img.getAttribute('src');lb.style.display='flex';}}
</script>
</body>
</html>
"""
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "工作台.html")
    open(out, "w", encoding="utf-8").write(html)
    print("已生成:", out)


def _grid_images(files, color, cols=4):
    out = []
    for f in files:
        p = os.path.join(ARCHIVE, f)
        nm = os.path.basename(f)
        out.append(f'<div class="imgbox"><img src="{esc(rel(p))}" onclick="zoom(this)"><div class="cap">{esc(nm)}</div></div>')
    if not out:
        return ""
    gridcls = "cardgrid" if cols == 3 else ""
    return f'<div class="imgs {gridcls}">{"".join(out)}</div>'


def _download_list(files, tag):
    out = []
    for f in files:
        p = os.path.join(ARCHIVE, f)
        out.append(f'<a download href="{esc(rel(p))}"><span class="tg">{tag}</span>{esc(os.path.basename(f))} · {esc(fmt_size(p))}</a>')
    return f'<div class="dl">{"".join(out)}</div>' if out else ""


def _status(today, manifest, dates):
    g = manifest.get(today, {})
    def cnt(plat):
        p = g.get(plat, {}) or {}
        return sum(len(p.get(k, [])) for k in p)
    tb, xy = cnt("taobao"), cnt("xianyu")
    total = sum(cnt(p) for p in ("taobao", "xianyu")) + cnt("失败记录")
    return f"""<div class="panel"><h2>🌅 今日竞品采集 · {esc(today)}</h2><div class="grid">
  <div class="stat"><div class="num">00:05</div><div class="lab">计划执行时间（北京）</div></div>
  <div class="stat"><div class="num" style="color:#4a8f6a">已完成</div><div class="lab">状态</div></div>
  <div class="stat"><div class="num" style="color:#c47046">{tb}</div><div class="lab">淘宝收录</div></div>
  <div class="stat"><div class="num" style="color:#4a9a7a">{xy}</div><div class="lab">闲鱼收录</div></div>
  <div class="stat"><div class="num">{total}</div><div class="lab">归档文件</div></div>
</div></div>"""


if __name__ == "__main__":
    main()