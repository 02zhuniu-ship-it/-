"""把「超自然行动组」真实竞品数据打包成手机APP样式的爆品展示页。

页面特点：
- 手机APP 双栏商品流样式，卡片上有图片、价格、平台标签
- 点开商品卡片弹出抽屉详情（价格、店铺、来源、详情链接）
- 顶部按平台分类tab：全部 / 淘宝 / 闲鱼
- 图片以 base64 内嵌，页面单文件可随处打开
"""

import base64
import json
import os
import re

ARCH = "/workspace/archive/2026-09-30"
OUT = "/workspace/workbench/超自然行动组爆品.html"


def b64(path):
    if not path:
        return None
    # img_file/img_url_local 是相对 archive/ 的路径（如 2026-09-30/...）
    cands = [path, os.path.join("/workspace/archive", str(path))]
    for p in cands:
        if os.path.exists(p):
            ext = os.path.splitext(p)[1].lower().lstrip(".")
            mime = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg"}.get(ext, "jpeg")
            with open(p, "rb") as f:
                return f"data:image/{mime};base64," + base64.b64encode(f.read()).decode()
    return None


def clean(t):
    return re.sub(r"\s+", " ", str(t or "")).strip()


def main():
    items = []

    # 淘宝
    tb = json.load(open(os.path.join(ARCH, "taobao/数据/data_taobao_search_v2.json")))
    for it in tb.get("items", []):
        if it.get("is_demo"):
            continue
        img = b64(it.get("img_file"))
        items.append({
            "platform": "淘宝",
            "title": clean(it.get("title")),
            "price": it.get("price"),
            "shop": clean(it.get("shop")),
            "sales": clean(it.get("sales")),
            "city": clean(it.get("city")),
            "url": it.get("detail_url", ""),
            "img": img or "",
            "points": [clean(s) for s in (it.get("selling_points") or [])],
            "src": clean(it.get("fetch_status")),
        })

    # 闲鱼（虚拟商品，一般无图）
    xy = json.load(open(os.path.join(ARCH, "xianyu/数据/data_xianyu_detail.json")))
    for it in xy.get("items", []):
        if it.get("is_demo"):
            continue
        img = b64(it.get("img_file")) or b64(it.get("img_url_local")) if it.get("img_file") or it.get("img_url_local") else ""
        items.append({
            "platform": "闲鱼",
            "title": clean(it.get("title")),
            "price": it.get("price"),
            "shop": clean(it.get("seller")),
            "sales": clean(it.get("want")),
            "city": clean(it.get("city")),
            "url": it.get("detail_url", ""),
            "img": img or "",
            "points": [clean(it.get("desc_full"))[:200]],
            "src": "虚拟商品",
        })

    payload = json.dumps(items, ensure_ascii=False)

    html = PAGE.replace("__DATA__", payload)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("生成完成:", OUT, "| 商品数:", len(items))


PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>超自然行动组 · 竞品爆品</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg:#f4f2f0;--card:#fff;--text:#1f1b16;--sub:#8a8378;--line:#ece7e1;--tb:#ff5000;--xy:#ffd300}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--text)}
.app{max-width:520px;margin:0 auto;min-height:100vh;position:relative}
/* 顶栏 */
.topbar{position:sticky;top:0;z-index:10;background:#fff;border-bottom:1px solid var(--line)}
.topbar .bar{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 10px}
.topbar h1{font-size:18px;font-weight:700}
.topbar .sub{font-size:12px;color:var(--sub);margin-top:2px}
.tabs{display:flex;padding:0 12px 10px;gap:8px;overflow-x:auto}
.tab{flex:0 0 auto;padding:6px 14px;border-radius:99px;background:#f1ece7;font-size:13px;color:#6b6358;cursor:pointer}
.tab.on{background:#1f1b16;color:#fff;font-weight:600}
/* 商品流 */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:12px}
.card{background:var(--card);border-radius:14px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);cursor:pointer;transition:transform .12s}
.card:active{transform:scale(.97)}
.pic{position:relative;aspect-ratio:1/1;background:#eee;display:flex;align-items:center;justify-content:center;color:#ccc}
.pic img{width:100%;height:100%;object-fit:cover;display:block}
.plat{position:absolute;top:8px;left:8px;font-size:11px;padding:2px 8px;border-radius:6px;color:#fff;background:var(--tb)}
.ismeta{position:absolute;top:8px;right:8px;font-size:10px;padding:2px 6px;border-radius:6px;background:rgba(0,0,0,.55);color:#fff}
.nopic{font-size:12px;color:#aaa}
.cinfo{padding:9px 10px 11px}
.ctitle{font-size:13px;line-height:1.35;height:36px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.cprice{font-size:16px;font-weight:700;color:#e23b1e;margin-top:6px}
.cprice .yuan{font-size:11px;font-weight:500;margin-right:1px}
.cshop{font-size:11px;color:var(--sub);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 详情抽屉 */
.drawer{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:50;opacity:0;visibility:hidden;transition:.25s}
.drawer.show{opacity:1;visibility:visible}
.sheet{position:absolute;bottom:0;left:0;right:0;max-width:520px;margin:0 auto;background:#fff;border-radius:18px 18px 0 0;max-height:88vh;overflow-y:auto;transform:translateY(100%);transition:.3s}
.drawer.show .sheet{transform:translateY(0)}
.sheet .hd{position:sticky;top:0;background:#fff;display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--line)}
.sheet .hd .h{font-size:16px;font-weight:700}
.close{width:30px;height:30px;border-radius:50%;background:#f1ece7;color:#7a7166;font-size:16px;border:none;cursor:pointer;line-height:30px;text-align:center}
.sheet .body{padding:16px}
.pbig{width:100%;border-radius:12px;background:#eee;display:flex;align-items:center;justify-content:center;min-height:220px;color:#ccc;font-size:13px}
.pbig img{width:100%;border-radius:12px;display:block}
.dtitle{font-size:15px;line-height:1.5;margin:14px 0 10px}
.dprice{font-size:22px;font-weight:800;color:#e23b1e}
.dprice .yuan{font-size:13px;font-weight:500}
.drow{display:flex;justify-content:space-between;font-size:13px;padding:9px 0;border-bottom:1px solid var(--line)}
.drow .k{color:var(--sub)} .drow .v{font-weight:500;max-width:65%;text-align:right}
.dbtn{display:block;width:100%;margin:18px 0 6px;padding:13px;border:none;border-radius:12px;background:#1f1b16;color:#fff;font-size:15px;font-weight:600;cursor:pointer;text-align:center;text-decoration:none}
.dbtn:active{opacity:.85}
.tagline{font-size:12px;color:#b3aca2;text-align:center;padding:6px 0 20px}
.badge{display:inline-block;font-size:11px;padding:1px 8px;border-radius:6px;margin-right:6px;color:#fff;background:var(--tb)}
.badge.xy{background:#1f1b16}
.empty{display:none;text-align:center;color:#b3aca2;padding:60px 0}
</style>
</head>
<body>
<div class="app">
  <div class="topbar">
    <div class="bar">
      <div>
        <h1>超自然行动组 · 爆品</h1>
        <div class="sub">同行竞品 · 真实采集</div>
      </div>
    </div>
    <div class="tabs" id="tabs">
      <div class="tab on" data-f="all">全部</div>
      <div class="tab" data-f="淘宝">淘宝</div>
      <div class="tab" data-f="闲鱼">闲鱼</div>
    </div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty">该分类暂无商品</div>
</div>

<div class="drawer" id="drawer">
  <div class="sheet">
    <div class="hd"><div class="h">商品详情</div><button class="close" onclick="closeD()">✕</button></div>
    <div class="body" id="dbody"></div>
  </div>
</div>

<script>
var DATA = __DATA__;
var LIST = DATA;
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function filter(f){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.toggle('on',t.dataset.f===f)});
  var arr = f==='all'?DATA:DATA.filter(function(x){return x.platform===f});
  LIST = arr;
  var g=document.getElementById('grid'); g.innerHTML='';
  if(arr.length===0){document.getElementById('empty').style.display='block';return}
  document.getElementById('empty').style.display='none';
  arr.forEach(function(it){
    var pic;
    if(it.img){pic='<img src="'+it.img+'" alt="" loading="lazy">';}
    else{pic='<div class="nopic">虚拟商品</div>';}
    var mk='<div class="card" onclick="openD('+DATA.indexOf(it)+')">'
      +'<div class="pic">'+pic
      +'<span class="plat" style="background:'+(it.platform==='淘宝'?'var(--tb)':'#1f1b16')+'">'+it.platform+'</span>'
      +(it.src==='虚拟商品'?'<span class="ismeta">虚拟</span>':'')
      +'</div><div class="cinfo">'
      +'<div class="ctitle">'+esc(it.title)+'</div>'
      +'<div class="cprice"><span class="yuan">￥</span>'+esc(it.price)+'</div>'
      +'<div class="cshop">'+esc(it.shop||'')+'</div>'
      +'</div></div>';
    g.insertAdjacentHTML('beforeend',mk);
  });
}
function openD(idx){
  var it = DATA[idx];
  var ps = (it.points||[]).map(function(s){return '<div class="drow"><span class="k">卖点</span><span class="v">'+esc(s)+'</span></div>'}).join('');
  var big = it.img?'<img src="'+it.img+'">':'<div style="padding:60px 0;color:#aaa;font-size:13px">虚拟商品 · 无商品图</div>';
  document.getElementById('dbody').innerHTML =
    '<div class="pbig">'+big+'</div>'
    +'<div class="dtitle">'+esc(it.title)+'</div>'
    +'<div class="dprice"><span class="yuan">￥</span>'+esc(it.price)+'</div>'
    +'<div class="drow"><span class="k">平台</span><span class="v"><span class="badge" style="background:'+(it.platform==='淘宝'?'var(--tb)':'#1f1b16')+'">'+it.platform+'</span></span></div>'
    +'<div class="drow"><span class="k">店铺</span><span class="v">'+esc(it.shop||'-')+'</span></div>'
    +'<div class="drow"><span class="k">来源</span><span class="v">'+esc(it.src||'真实采集')+'</span></div>'
    +'<div class="drow"><span class="k">城市</span><span class="v">'+esc(it.city||'-')+'</span></div>'
    +ps
    +'<a class="dbtn" href="'+esc(it.url)+'" target="_blank" rel="noopener">查看原商品</a>';
  document.getElementById('drawer').classList.add('show');
}
function closeD(){document.getElementById('drawer').classList.remove('show')}
document.getElementById('drawer').addEventListener('click',function(e){if(e.target===this)closeD()});
document.getElementById('tabs').addEventListener('click',function(e){
  var t=e.target.closest('.tab'); if(t)filter(t.dataset.f);
});
filter('all');
</script>
</body>
</html>
"""

main()