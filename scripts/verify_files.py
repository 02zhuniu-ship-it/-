"""校验当天所有文件是否生成成功。输出成功/失败/新增文件数。"""

import os

import common


def collect_expected_files(task_date, logger):
    """返回期望的文件路径列表（数据2 + 图片若干 + PPT + 卡片 + 失败说明）。"""
    expected = []
    root = common.ARCHIVE_ROOT

    for plat, prefix in {"taobao": "data_taobao_search_v2", "xianyu": "data_xianyu_detail"}.items():
        data_dir = os.path.join(root, task_date, plat, "数据")
        # 数据文件：当天版 + 最新版
        for name in [f"{prefix}.json", f"{prefix}.latest.json"]:
            if os.path.exists(os.path.join(data_dir, name)):
                expected.append(os.path.join(data_dir, name))
        # 商品图片
        img_dir = os.path.join(root, task_date, plat, "商品图片")
        if os.path.isdir(img_dir):
            for f in sorted(os.listdir(img_dir)):
                expected.append(os.path.join(img_dir, f))
        # PPT
        ppt_dir = os.path.join(root, task_date, plat, "PPT报告")
        if os.path.isdir(ppt_dir):
            for f in sorted(os.listdir(ppt_dir)):
                if f.endswith(".pptx"):
                    expected.append(os.path.join(ppt_dir, f))
        # 闲鱼详情卡片
        card_dir = os.path.join(root, task_date, plat, "详情卡片")
        if os.path.isdir(card_dir):
            for f in sorted(os.listdir(card_dir)):
                expected.append(os.path.join(card_dir, f))

    # 失败说明
    fail_dir = os.path.join(root, task_date, "失败记录")
    if os.path.isdir(fail_dir):
        for f in sorted(os.listdir(fail_dir)):
            expected.append(os.path.join(fail_dir, f))

    return expected


def verify_files(task_date, logger):
    expected = collect_expected_files(task_date, logger)
    ok = [f for f in expected if os.path.exists(f) and os.path.getsize(f) > 0]
    bad = [f for f in expected if not os.path.exists(f)]
    return {"total": len(expected), "ok": len(ok), "failed": len(bad),
            "files": expected, "bad_files": bad}