"""通用自动入库接口（GENERIC INGEST API）。

任何自动化任务（电商采集 / AI生图 / AI视频 / 客户资料 / 模板 / 提示词...）
只需提供：任务名称、日期、项目、平台、文件类型、文件路径列表、来源，
即可自动：按"日期/平台/文件类型"归档 + 文件去重 + 写入任务记录 + 更新manifest。

用法（命令行）：
  python3 ingest.py --task-name "每日竞品分析" --date 2026-09-30 --platform taobao --type 数据 [--project 电商] --files a.json b.json --source auto

支持交互：把文件复制进 archive/<date>/<platform>/<type>/。
去重：按 文件哈希+大小 判断，已在库则标记"已存在"，不重复保存。
"""

import argparse
import os
import shutil

import common


def ingest(files, task_name, date, platform, file_type, project="", source="auto", logger=None, register_only=False):
    if logger is None:
        logger = common.setup_logger("ingest")

    dest_root = os.path.join(common.ARCHIVE_ROOT, date, platform, file_type)
    if not register_only:
        common.ensure_dir(dest_root)

    uploaded = []
    existed = []
    failed = []
    rels = []

    for f in files:
        if not os.path.exists(f):
            failed.append({"file": f, "reason": "源文件不存在"})
            continue
        size = os.path.getsize(f)
        fhash = common.sha256_file(f)
        dup = common.is_duplicate(fhash, size)
        if register_only:
            # 仅登记（文件已在归档结构内）：去重 + 更新索引，不复制
            dest = os.path.join(dest_root, os.path.basename(f))
            if dup:
                existed.append({"hash": fhash, "path": os.path.relpath(dest, common.ARCHIVE_ROOT)})
                rel = os.path.relpath(dest, common.ARCHIVE_ROOT)
                rels.append(rel)
                continue
            rel = os.path.relpath(dest, common.ARCHIVE_ROOT)
            common.mark_ingested(rel, fhash, size, task_name)
            uploaded.append(rel)
            rels.append(rel)
            continue
        dest = os.path.join(dest_root, os.path.basename(f))
        try:
            if dup:
                existed.append({"hash": fhash, "path": os.path.relpath(dest, common.ARCHIVE_ROOT)})
                rel = os.path.relpath(dest, common.ARCHIVE_ROOT)
                rels.append(rel)
                continue
            shutil.copy2(f, dest)
            rel = os.path.relpath(dest, common.ARCHIVE_ROOT)
            common.mark_ingested(rel, fhash, size, task_name)
            uploaded.append(rel)
            rels.append(rel)
        except Exception as e:
            failed.append({"file": f, "reason": str(e)})

    # 更新 manifest（首页入库索引）
    manifest = common.load_manifest()
    entry = manifest.setdefault(date, {}).setdefault(platform, {}).setdefault(file_type, [])
    new_items = [r for r in rels if r not in entry]
    entry.extend(new_items)
    common.save_manifest(manifest)

    # 写任务记录
    common.record_task({
        "task_name": task_name, "date": date, "project": project, "platform": platform,
        "type": file_type, "source": source,
        "uploaded": len(uploaded), "existed": len(existed), "failed": len(failed),
        "files": rels, "failed_detail": failed,
        "ts": common.now_china().isoformat(),
    })

    summary = {"uploaded": len(uploaded), "existed": len(existed), "failed": len(failed),
               "uploaded_files": uploaded, "existed_files": existed, "failed_files": failed}
    logger.info(f"[入库] {platform}/{file_type}: 新增{len(uploaded)} 已存在{len(existed)} 失败{len(failed)}")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-name", required=True)
    ap.add_argument("--date", default=common.today_str())
    ap.add_argument("--platform", required=True)
    ap.add_argument("--type", required=True)
    ap.add_argument("--project", default="")
    ap.add_argument("--source", default="auto")
    ap.add_argument("--files", nargs="*", default=[])
    args = ap.parse_args()

    logger = common.setup_logger("ingest")
    summary = ingest(args.files, args.task_name, args.date, args.platform,
                     args.type, args.project, args.source, logger)
    import json
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()