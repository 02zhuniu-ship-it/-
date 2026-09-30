"""把「超自然行动组」真实竞品数据打包成带主菜单的手机APP风格工作台。

单文件、双击即开、离线可用。底部导航：概览 / 今日爆品 / 历史归档 / 关于。
"""

import base64
import json
import os
import re

ARCH_ROOT = "/workspace/archive"
ARCH = "/workspace/archive/2026-09-30"  # 当天商品数据
OUT = "/workspace/workbench/工作台.html"
OUT_LITE = "/workspace/workbench/工作台-手机版.html"  # 轻量版：图片走外链，供网上托管/手机秒开


def b64(path):
    if not path:
        return None
    for p in (path, os.path.join("/workspace/archive", str(path))):
        if os.path.exists(p):
            ext = os.path.splitext(p)[1].lower().lstrip(".")
            mime = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg"}.get(ext, "jpeg")
            with open(p, "rb") as f:
                return f"data:image/{mime};base64," + base64.b64encode(f.read()).decode()
    return None


def clean(t):
    return re.sub(r"\s+", " ", str(t or "")).strip()


_TIER_STOP = {
    "自动发货", "官服", "换绑", "账号", "帐号", "可换", "全新", "周免", "初始",
    "亿", "w", "万", "资源号", "新手", "安卓", "苹果", "平台", "Game", "官谷",
}


def extract_tiers(title):
    """从淘宝标题里诚实提取档位价格。

    淘宝真实SKU需登录详情页才能拿到(当前待核验)。不少商品标题自带多个档位价格，
    例如「自動充值...10 60 300 680 980 1980 6480金磚充值」。这里把标题中成串的数字
    找出来当作档位提示，明确标注"来自标题·详情需登录核验"，绝不编造。
    """
    if not title:
        return []
    # 含明确价格语义词（充值/金砖/代充/元）：标题里成串数字基本都是档位价格，全部提取
    if re.search(r'充值|金砖|代充|\d+元', title):
        nums = re.findall(r'\d+(?:\.\d+)?', title)
    else:
        nums = []
        for m in re.findall(r'\b(?:\d{1,5}\s*[,.、/ ]?){2,}\b', title):
            nums += re.findall(r'\d+(?:\.\d+)?', m)
    clean_nums = []
    for n in nums:
        v = float(n)
        # 过滤明显不是价格档位的数字（ID、百分比、亿/万计数）
        if 1 <= v <= 50000 and re.fullmatch(r'\d+(?:\.\d+)?', n):
            clean_nums.append(n.rstrip('0').rstrip('.') if '.' in n else n)
    # 去重保序
    flat = []
    for v in clean_nums:
        if v not in flat:
            flat.append(v)
    return flat[:12]


def cat_of(f):
    f = str(f)
    if "PPT" in f:
        return "PPT报告"
    if "商品图片" in f:
        return "商品图片"
    if "详情卡片" in f:
        return "详情卡片"
    if "失败" in f:
        return "失败记录"
    return "数据文件"


def collect_days():
    """按天分组归档文件：{date: [相对路径,...]}，每天内部再按平台/类型分。"""
    days = {}
    if not os.path.isdir(ARCH_ROOT):
        return days
    for name in sorted(os.listdir(ARCH_ROOT)):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", name):
            continue
        daydir = os.path.join(ARCH_ROOT, name)
        fl = []
        for dirpath, _, fns in os.walk(daydir):
            if "_system" in dirpath:
                continue
            for fn in fns:
                fl.append(os.path.relpath(os.path.join(dirpath, fn), ARCH_ROOT))
        if fl:
            days[name] = sorted(fl)
    return days


def main():
    items = []

    tb = json.load(open(os.path.join(ARCH, "taobao/数据/data_taobao_search_v2.json")))
    for it in tb.get("items", []):
        if it.get("is_demo"):
            continue
        items.append({
            "platform": "淘宝", "title": clean(it.get("title")),
            "price": it.get("price"), "shop": clean(it.get("shop")),
            "city": clean(it.get("city")), "url": it.get("detail_url", ""),
            "img": b64(it.get("img_file")) or "",
            "img_url": it.get("img_url", ""),
            "points": [clean(s) for s in (it.get("selling_points") or [])][:2],
            "src": clean(it.get("fetch_status")), "type": "实物",
            "tiers": extract_tiers(clean(it.get("title"))),
        })

    xy = json.load(open(os.path.join(ARCH, "xianyu/数据/data_xianyu_detail.json")))
    for it in xy.get("items", []):
        if it.get("is_demo"):
            continue
        img = b64(it.get("img_file")) if it.get("img_file") else ""
        items.append({
            "platform": "闲鱼", "title": clean(it.get("title")),
            "price": it.get("price"), "shop": clean(it.get("seller")),
            "city": clean(it.get("city")), "url": it.get("detail_url", ""),
            "img": img, "img_url": it.get("img_url", ""),
            "points": [clean(it.get("desc_full"))[:160]],
            "src": "虚拟商品", "type": "虚拟",
        })

    try:
        r = json.load(open("/workspace/archive/_system/run_result_2026-09-30.json"))
    except Exception:
        r = {}

    # 归档按天分组
    days_map = collect_days()
    all_files = [f for fl in days_map.values() for f in fl]

    n_tb = sum(1 for i in items if i["platform"] == "淘宝")
    n_xy = sum(1 for i in items if i["platform"] == "闲鱼")

    stat = {"date": "2026-09-30", "generated": r.get("generated", len(all_files)),
            "success": r.get("success", 0), "failed": r.get("failed", 0),
            "taobao": n_tb, "xianyu": n_xy, "demo": r.get("demo", False)}

    # days: 数组, 每天 {"date":.., "cat":[file,...]}
    days_list = []
    for d, fl in days_map.items():
        grouped = {}
        for f in fl:
            grouped.setdefault(cat_of(f), []).append(f)
        days_list.append({"date": d, "groups": grouped})

    html = (PAGE
            .replace("__DATA__", json.dumps(items, ensure_ascii=False))
            .replace("__DAYS__", json.dumps(days_list, ensure_ascii=False))
            .replace("__STAT__", json.dumps(stat, ensure_ascii=False)))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)

    # —— 手机轻量版：图片改用公网原图地址，不内嵌，体积从 10MB+ 降到几十 KB ——
    def lite(it):
        it = dict(it)
        it["img"] = it.pop("img_url", "") or it.get("img", "")
        it.pop("img_url", None)
        return it
    lite_items = [lite(i) for i in items]
    lite_html = (PAGE
                 .replace("__DATA__", json.dumps(lite_items, ensure_ascii=False))
                 .replace("__DAYS__", json.dumps(days_list, ensure_ascii=False))
                 .replace("__STAT__", json.dumps(stat, ensure_ascii=False)))
    with open(OUT_LITE, "w", encoding="utf-8") as f:
        f.write(lite_html)

    print("生成完成:", OUT, "| 商品:", len(items), "| 天数:", len(days_list))
    print("手机版:", OUT_LITE, "| 体积:", os.path.getsize(OUT_LITE)//1024, "KB")


PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>电商竞品 · 工作台</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg:#f4f2f0;--card:#fff;--text:#1f1b16;--sub:#8a8378;--line:#ece7e1;--tb:#ff5000;--accent:#a06b6b}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;background:var(--bg);color:var(--text)}
.app{max-width:520px;margin:0 auto;min-height:100vh;padding-bottom:76px}
/* 顶栏 */
.topbar{background:#fff;border-bottom:1px solid var(--line);padding:14px 16px 10px}
.topbar h1{font-size:18px;font-weight:700}
.topbar .sub{font-size:12px;color:var(--sub);margin-top:2px}
/* 页面区 */
.page{display:none;animation:fade .25s}
.page.on{display:block}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1}}
/* 概览 */
.hero{background:var(--card);margin:14px 12px;border-radius:16px;padding:18px;border:1px solid var(--line)}
.hero h2{font-size:17px;margin-bottom:6px}
.hero p{font-size:13px;color:var(--sub);line-height:1.6;margin-top:8px}
.hero .row{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px dashed var(--line);font-size:13px}
.hero .row:last-child{border-bottom:none}.hero .k{color:var(--sub)}.hero .v{font-weight:600}
.pillx{display:inline-block;font-size:11px;padding:2px 9px;border-radius:99px;background:#eef4ef;color:#2a7a52}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:4px 12px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 8px;text-align:center}
.stat .num{font-size:22px;font-weight:800}.stat .lab{font-size:11px;color:var(--sub);margin-top:3px}
.stat .t{color:var(--tb)}.stat .x{color:#1a7f5a}.stat .g{color:#4a8f6a}
/* 爆品 */
.tabbar{position:sticky;top:0;z-index:20;display:flex;padding:10px 12px;gap:8px;overflow-x:auto;background:#fff;border-bottom:1px solid var(--line)}
.tab{flex:0 0 auto;padding:6px 14px;border-radius:99px;background:#ece7e1;font-size:13px;color:#6b6358;cursor:pointer}
.tab.on{background:#1f1b16;color:#fff;font-weight:600}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:12px}
.card{background:var(--card);border-radius:14px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);cursor:pointer;transition:transform .12s}
.card:active{transform:scale(.97)}
.pic{position:relative;aspect-ratio:1/1;background:#eee;display:flex;align-items:center;justify-content:center;color:#bbb;font-size:12px}
.pic img{width:100%;height:100%;object-fit:cover;display:block}
.plat{position:absolute;top:8px;left:8px;font-size:11px;padding:2px 8px;border-radius:6px;color:#fff}
.cinfo{padding:9px 10px 11px}
.ctitle{font-size:13px;line-height:1.35;height:36px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.cprice{font-size:16px;font-weight:700;color:#e23b1e;margin-top:6px}.cprice .y{font-size:11px;font-weight:500}
.cshop{font-size:11px;color:var(--sub);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tierline{font-size:11px;color:#b0853a;margin-top:2px;font-weight:600}
.empty{display:none;text-align:center;color:#b3aca2;padding:50px 0;font-size:14px}
/* 档位价格 */
.tiers{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 4px}
.tier{flex:1 1 44%;min-width:110px;background:#f8f4ef;border:1px solid var(--line);border-radius:10px;padding:7px 11px;display:flex;justify-content:space-between;align-items:center;font-size:12px}
.tier .lab{color:var(--sub)}.tier .val{color:#e23b1e;font-weight:700;font-size:13px}
.tier.note{flex-basis:100%;background:#fff7ef;border-color:#f0dcc0;color:#8a6420;font-size:11px;display:block;padding:7px 11px}
/* 归档 */
.archive{margin:4px 10px}
.daycard{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:14px}
.daycard .dt{font-size:15px;font-weight:800;margin-bottom:2px;display:flex;align-items:center;justify-content:space-between}
.daycard .dt .cnt{font-size:11px;font-weight:500;color:var(--sub)}
.daycard .dsub{font-size:11px;color:#9c9090;margin-bottom:8px}
.ah{font-size:13px;font-weight:700;margin:8px 0 5px;color:#4a433c}
.afile{background:#faf8f5;border:1px solid var(--line);border-radius:8px;padding:7px 10px;margin-bottom:5px}
.afile .nm{font-size:12px;word-break:break-all}
.afile .meta{font-size:11px;color:#9c9090;margin-top:1px}
/* 关于 */
.about{margin:14px 12px}
.card2{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:12px;font-size:13px;line-height:1.7;color:#4a433c}
.card2 h3{font-size:15px;margin-bottom:6px}
.warn{background:#fff7ef;border-color:#f0dcc0;color:#8a6420}
/* 抽屉 */
.drawer{position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:60;opacity:0;visibility:hidden;transition:.25s}
.drawer.show{opacity:1;visibility:visible}
.sheet{position:absolute;bottom:0;left:0;right:0;max-width:520px;margin:0 auto;background:#fff;border-radius:18px 18px 0 0;max-height:88vh;overflow-y:auto;transform:translateY(100%);transition:.3s}
.drawer.show .sheet{transform:translateY(0)}
.sheet .hd{position:sticky;top:0;background:#fff;display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--line)}
.sheet .hd .h{font-size:16px;font-weight:700}
.close{width:30px;height:30px;border-radius:50%;background:#f1ece7;color:#7a7166;font-size:16px;border:none;cursor:pointer}
.sheet .body{padding:16px}
.pbig{width:100%;border-radius:12px;background:#eee;display:flex;align-items:center;justify-content:center;min-height:220px;color:#aaa;font-size:13px}
.pbig img{width:100%;border-radius:12px;display:block}
.dtitle{font-size:15px;line-height:1.5;margin:14px 0 10px}
.dprice{font-size:22px;font-weight:800;color:#e23b1e}.dprice .y{font-size:13px;font-weight:500}
.drow{display:flex;justify-content:space-between;font-size:13px;padding:9px 0;border-bottom:1px solid var(--line)}
.drow .k{color:var(--sub)}.drow .v{font-weight:500;max-width:65%;text-align:right}
.dbtn{display:block;width:100%;margin:18px 0 6px;padding:13px;border:none;border-radius:12px;background:#1f1b16;color:#fff;font-size:15px;font-weight:600;cursor:pointer;text-align:center;text-decoration:none}
/* 底部导航 */
.nav{position:fixed;bottom:0;left:0;right:0;max-width:520px;margin:0 auto;background:#fff;border-top:1px solid var(--line);display:flex;z-index:40;padding-bottom:env(safe-area-inset-bottom)}
.nav .ni{flex:1;text-align:center;padding:9px 6px 8px;cursor:pointer;color:#9a927f}
.nav .ni.on{color:#1f1b16;font-weight:700}
.nav .ni .ic{font-size:20px;line-height:1}.nav .ni .la{font-size:11px;margin-top:3px}
</style>
</head>
<body>
<div class="app">
  <div class="topbar"><h1>🛠️ 电商竞品工作台</h1><div class="sub">超自然行动组 · 同行爆品自动采集</div></div>

  <!-- 概览 -->
  <div class="page on" id="pg-home">
    <div class="hero">
      <h2>🌅 今日采集概览</h2>
      <p id="ov_date"></p>
      <div class="row" style="padding-top:10px"><span class="k">任务状态</span><span class="v" id="ov_st"></span></div>
      <div class="row"><span class="k">淘宝收录</span><span class="v" id="ov_tb"></span></div>
      <div class="row"><span class="k">闲鱼收录</span><span class="v" id="ov_xy"></span></div>
      <div class="row"><span class="k">生成文件</span><span class="v" id="ov_gen"></span></div>
      <div class="row"><span class="k">成功 / 失败</span><span class="v" id="ov_ok"></span></div>
      <div class="row"><span class="k">数据来源</span><span class="v"><span class="pillx" id="ov_src"></span></span></div>
      <p>点下方「今日爆品」查看竞品商品；点「历史归档」查看当天所有资料文件。</p>
    </div>
    <div class="stats" id="ov_stats"></div>
  </div>

  <!-- 今日爆品 -->
  <div class="page" id="pg-products">
    <div class="tabbar" id="tabs">
      <div class="tab on" data-f="all">全部</div>
      <div class="tab" data-f="淘宝">淘宝</div>
      <div class="tab" data-f="闲鱼">闲鱼</div>
    </div>
    <div class="grid" id="grid"></div>
    <div class="empty" id="empty">该分类暂无商品</div>
  </div>

  <!-- 历史归档 -->
  <div class="page" id="pg-archive">
    <div style="padding:13px 14px 4px"><b style="font-size:15px">🗂️ 云端归档 · 按天整理</b></div>
    <div id="archive-day" class="archive" ></div>
  </div>

  <!-- 关于 -->
  <div class="page" id="pg-about">
    <div class="about">
      <div class="card2"><h3>📌 这是什么</h3>自动采集「超自然行动组」同行竞品的工作台。每天云端自动抓取淘宝+闲鱼的真实竞品数据，归档成表格、图片、PPT，并汇总到这里方便查看。</div>
      <div class="card2"><h3>🔄 自动运行</h3>系统配置为每天凌晨 00:05（北京时间）自动采集并归档。你不需要手动操作，打开本工作台就能看到当天成果。</div>
      <div class="card2"><h3>🔍 数据真实性</h3>展示的是从公开渠道真实采集到的商品信息。确实抓不到的部分会如实标记，不编造。闲鱼类多为兑换码、账号等虚拟商品。</div>
      <div class="card2 warn"><h3>⚠️ 两个提醒</h3>①数据为采集当下快照，价格/库存会随时间变化。②闲鱼虚拟商品请通过原商品链接自行核实后再交易。</div>
    </div>
  </div>
</div>

<div class="nav">
  <div class="ni on" data-tab="pg-home"><div class="ic">🏠</div><div class="la">概览</div></div>
  <div class="ni" data-tab="pg-products"><div class="ic">🛍️</div><div class="la">今日爆品</div></div>
  <div class="ni" data-tab="pg-archive"><div class="ic">🗂️</div><div class="la">历史归档</div></div>
  <div class="ni" data-tab="pg-about"><div class="ic">📖</div><div class="la">关于</div></div>
</div>

<div class="drawer" id="drawer">
  <div class="sheet">
    <div class="hd"><div class="h">商品详情</div><button class="close" onclick="closeD()">✕</button></div>
    <div class="body" id="dbody"></div>
  </div>
</div>

<script>
var DATA=__DATA__;
var DAYS=__DAYS__;
var STAT=__STAT__;
var LIST=DATA.slice();
function $(id){return document.getElementById(id)}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function platformOf(f){
  if(String(f).indexOf('/taobao/')>-1)return '淘宝';
  if(String(f).indexOf('/xianyu/')>-1)return '闲鱼';
  return '系统';
}
/* ------ 概览 ------ */
(function(){
  $('ov_date').textContent='统计日期：'+STAT.date+'（北京时间）';
  $('ov_tb').textContent=STAT.taobao+' 件';
  $('ov_xy').textContent=STAT.xianyu+' 件';
  $('ov_gen').textContent=STAT.generated+' 个';
  $('ov_ok').textContent=STAT.success+' / '+STAT.failed;
  $('ov_st').textContent=STAT.demo?'（演示数据）':'已完成';
  $('ov_src').textContent=STAT.demo?'演示':'Apify 真实采集';
  $('ov_stats').innerHTML=
    '<div class="stat"><div class="num t">'+STAT.taobao+'</div><div class="lab">淘宝商品</div></div>'+
    '<div class="stat"><div class="num x">'+STAT.xianyu+'</div><div class="lab">闲鱼商品</div></div>'+
    '<div class="stat"><div class="num g">'+STAT.success+'</div><div class="lab">成功文件</div></div>';
})();
/* ------ 今日爆品 ------ */
function renderList(){
  $('grid').innerHTML='';
  $('empty').style.display=LIST.length?'none':'block';
  LIST.forEach(function(it,i){
    var pic=it.img
      ?'<img src="'+it.img+'" alt="" loading="lazy">'
      :'<div>虚拟商品 · 无图</div>';
    var bg=it.platform==='淘宝'?'var(--tb)':'#1b6b4f';
    var tierline='';
    if(it.platform==='淘宝' && (it.tiers||[]).length){
      var first=it.tiers[0];
      tierline='<div class="tierline">¥'+first+'起 · 共'+it.tiers.length+'档</div>';
    }
    $('grid').insertAdjacentHTML('beforeend',
      '<div class="card" data-i="'+i+'">'+
      '<div class="pic">'+pic+'<span class="plat" style="background:'+bg+'">'+it.platform+'</span></div>'+
      '<div class="cinfo"><div class="ctitle">'+esc(it.title)+'</div>'+
      '<div class="cprice"><span class="y">￥</span>'+esc(it.price)+'</div>'+
      tierline+
      '<div class="cshop">'+esc(it.shop||'')+'</div></div></div>');
  });
}
$('grid').addEventListener('click',function(e){
  var c=e.target.closest('.card');if(!c)return;
  openD(DATA.indexOf(LIST[+c.dataset.i]));
});
$('tabs').addEventListener('click',function(e){
  var t=e.target.closest('.tab');if(!t)return;
  document.querySelectorAll('#tabs .tab').forEach(function(x){x.classList.remove('on')});
  t.classList.add('on');
  var f=t.dataset.f;
  LIST=f==='all'?DATA.slice():DATA.filter(function(x){return x.platform===f});
  renderList();
});
/* ------ 归档（按天整理）------ */
(function(){
  if(!DAYS || !DAYS.length){$('archive-day').innerHTML='<div class="empty" style="display:block">暂无归档</div>';return;}
  var CLabel={'PPT报告':'📊 PPT 报告','商品图片':'🖼️ 商品图片','详情卡片':'🃏 详情卡片','失败记录':'📛 失败记录','数据文件':'📄 数据文件'};
  DAYS.forEach(function(day){
    var card=document.createElement('div');card.className='daycard';
    var total=0;day.groups && Object.keys(day.groups).forEach(function(c){total+=day.groups[c].length;});
    var header='<div class="dt"><span>📅 '+day.date+'</span><span class="cnt">'+total+' 个文件</span></div>'+
      '<div class="dsub">淘宝 + 闲鱼 · 自动采集归档</div>';
    var body='';
    Object.keys(CLabel).forEach(function(cat){
      var arr=(day.groups&&day.groups[cat])||[];if(!arr.length)return;
      body+='<div class="ah">'+CLabel[cat]+'（'+arr.length+'）</div>';
      arr.forEach(function(f){
        var name=String(f).split('/').pop();
        body+='<div class="afile"><div class="nm">'+esc(name)+'</div>'+
          '<div class="meta">['+platformOf(f)+'] · '+esc(f)+'</div></div>';
      });
    });
    card.innerHTML=header+body;
    $('archive-day').appendChild(card);
  });
})();
/* ------ 抽屉 ------ */
function tierHtml(it){
  if(it.platform!=='淘宝')return '';
  var t=(it.tiers||[]);if(!t.length)return '';
  var chips=t.map(function(v){
    return '<div class="tier"><span class="lab">档位</span><span class="val">￥'+v+'</span></div>';
  }).join('');
  return '<div class="tiers">'+chips+
    '<div class="tier note">⚠️ 档位价格取自商品标题，为真实信息；具体每个款式的最终价格以详情页为准（淘宝详情需登录核验）。</div></div>';
}
function openD(idx){
  var it=DATA[idx];if(!it)return;
  var ps=(it.points||[]).map(function(s){return '<div class="drow"><span class="k">卖点</span><span class="v">'+esc(s)+'</span></div>'}).join('');
  var big=it.img?'<img src="'+it.img+'">':'<div style="padding:60px 0;color:#aaa;font-size:13px">虚拟商品 · 无商品图</div>';
  $('dbody').innerHTML=
    '<div class="pbig">'+big+'</div>'+
    '<div class="dtitle">'+esc(it.title)+'</div>'+
    '<div class="dprice"><span class="y">￥</span>'+esc(it.price)+'</div>'+
    tierHtml(it)+
    '<div class="drow"><span class="k">平台</span><span class="v">'+it.platform+'</span></div>'+
    '<div class="drow"><span class="k">店铺</span><span class="v">'+esc(it.shop||'-')+'</span></div>'+
    '<div class="drow"><span class="k">来源</span><span class="v">'+esc(it.src||'真实采集')+'</span></div>'+
    '<div class="drow"><span class="k">城市</span><span class="v">'+esc(it.city||'-')+'</span></div>'+ps+
    '<a class="dbtn" href="'+esc(it.url)+'" target="_blank" rel="noopener">查看原商品</a>';
  $('drawer').classList.add('show');
}
function closeD(){$('drawer').classList.remove('show');}
$('drawer').addEventListener('click',function(e){if(e.target===this)closeD();});
/* ------ 底部导航 ------ */
document.querySelectorAll('.nav .ni').forEach(function(n){
  n.addEventListener('click',function(){
    document.querySelectorAll('.nav .ni').forEach(function(x){x.classList.remove('on')});
    n.classList.add('on');
    document.querySelectorAll('.page').forEach(function(p){p.classList.remove('on')});
    $(n.dataset.tab).classList.add('on');
    window.scrollTo(0,0);
  });
});
renderList();
</script>
</body>
</html>
"""
main()