"""生成失败原因说明-日期.md。记录失败步骤、商品、缺什么、为什么、试过什么、最终状态。"""

import os

import common


def build_failure_report(all_failures, task_date, logger):
    fail_dir = common.archive_paths_for(task_date, "失败记录", "")
    path = os.path.join(fail_dir, f"失败原因说明-{task_date}.md")

    lines = [f"# 失败原因说明 · {task_date}", "", "自动生成的失败记录。", ""]
    lines.append(f"共 {len(all_failures)} 条失败记录。")
    lines.append("")

    for i, f in enumerate(all_failures, 1):
        lines.append(f"## {i}. {f.get('step', '未知步骤')}")
        lines.append(f"- 步骤：{f.get('step','')}")
        lines.append(f"- 关键词/商品：{f.get('keyword','') or f.get('product','') or '-'}")
        lines.append(f"- 缺少的数据：{f.get('field','') or '未知'}")
        lines.append(f"- 为什么失败：{f.get('reason','')}")
        lines.append(f"- 尝试过：{f.get('tried','-')}")
        lines.append(f"- 最终状态：{f.get('status','失败')}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path