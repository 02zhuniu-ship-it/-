"""全流程总控：一键串联 采集→抓详情→下载图→生成→失败记录→校验→入库→归档。

用法：
  python3 run_all.py --demo            # 本地演示，验证链路跑通（演示数据）
  python3 run_all.py                   # 真实采集（抓不到标记待核）
"""

import argparse
import os
import sys
import json
import subprocess

import common

SCRIPT_DIR = common.SCRIPT_DIR
PY = sys.executable


def run(script, *args, cwd=None):
    cmd = [PY, os.path.join(SCRIPT_DIR, script)] + list(args)
    r = subprocess.run(cmd, cwd=cwd or common.PROJECT_ROOT, capture_output=True, text=True)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--task-date", default=common.today_str())
    ap.add_argument("--with-cards", action="store_true", help="闲鱼生成详情卡片")
    args = ap.parse_args()

    logger = common.setup_logger("run_all")
    date = args.task_date
    demo = args.demo
    logger.info(f"=== 竞品采集全流程开始 {date} (demo={'是' if demo else '否'}) ===")

    failures = []

    # 1) 采集淘宝 & 闲鱼
    for plat in ("taobao", "xianyu"):
        r = run("collect_" + plat + ".py", "--task-date", date,
                *(["--demo"] if demo else []))
        if r.returncode != 0:
            logger.error(f"[{plat}] 采集脚本异常: {r.stderr[-500:]}")
            failures.append({"step": f"{plat}采集", "reason": "脚本异常"})
        # 读取采集脚本产出的失败/抓取记录，合并进统一失败列表
        raw_f = os.path.join(SCRIPT_DIR, f"_raw_{plat}_{date}.json")
        if os.path.exists(raw_f):
            raw = common.load_json(raw_f, {})
            for f in raw.get("fetches", []) or []:
                if f.get("is_demo"):
                    continue
                failures.append(f)
            # 真实采集返回0个且不是demo → 记录"未获取到任何真实商品"
            if not demo and not raw.get("items"):
                failures.append({
                    "step": f"{plat}采集", "keyword": "全部",
                    "field": "商品列表", "reason": "免登录真实采集被登录/风控墙拦截，未获取到任何商品",
                    "tried": "多关键词搜索公开页面/接口", "status": "失败",
                })

    # 2) 生成数据文件 + PPT + 卡片
    for plat in ("taobao", "xianyu"):
        extra = ["--with-cards"] if (args.with_cards and plat == "xianyu") else []
        r = run("build_outputs.py", "--platform", plat, "--task-date", date,
                *(["--demo"] if demo else []), *extra)
        if r.returncode != 0:
            logger.error(f"[{plat}] 生成输出异常: {r.stderr[-500:]}")
            failures.append({"step": f"{plat}输出", "reason": r.stderr[-300:]})

    # 3) 读取所有当日文件
    files = []
    task_name = "每日淘宝+闲鱼竞品分析"
    if os.path.isdir(os.path.join(common.ARCHIVE_ROOT, date)):
        for dirpath, _, filenames in os.walk(os.path.join(common.ARCHIVE_ROOT, date)):
            if "_system" in dirpath:
                continue
            for fn in filenames:
                files.append(os.path.join(dirpath, fn))

    # 4) 生成失败说明
    from report_failures import build_failure_report
    build_failure_report(failures, date, logger)

    # 5) 校验文件
    import importlib
    verify_files = importlib.import_module("verify_files")
    v = verify_files.verify_files(date, logger)

    # 6) 入库登记（文件已在归档结构内，仅去重登记 + 更新索引，不复制）
    from ingest import ingest
    for plat in ("taobao", "xianyu", "失败记录"):
        plat_dir = os.path.join(common.ARCHIVE_ROOT, date, plat)
        if not os.path.isdir(plat_dir):
            continue
        for dtype in os.listdir(plat_dir):
            dpath = os.path.join(plat_dir, dtype)
            if not os.path.isdir(dpath):
                continue
            plat_files = [os.path.join(dpath, fn) for fn in os.listdir(dpath)]
            if not plat_files:
                continue
            ingest(plat_files, task_name, date, plat, dtype, source="auto",
                   logger=logger, register_only=True)

    # 7) 汇总结果
    logger.info("=== 全部完成 ===")
    logger.info(f"生成文件总数: {v['total']}  成功: {v['ok']}  失败: {v['failed']}")
    result = {
        "date": date, "demo": demo, "task_name": task_name,
        "generated": v["total"], "success": v["ok"], "failed": v["failed"],
        "bad_files": v["bad_files"], "failures": failures,
        "ts": common.now_china().isoformat(),
    }
    common.record_task(result)
    common.save_json(os.path.join(common.DB_DIR, f"run_result_{date}.json"), result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()