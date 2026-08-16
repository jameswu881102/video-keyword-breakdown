#!/usr/bin/env python3
"""Write a user-facing upload/library request list from material_inserts.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows 控制台默认走 ANSI 代码页（如 cp1252/cp936），无法编码本脚本输出的
# 中文与状态图标，直接打印会抛 UnicodeEncodeError 且不产生任何输出。
# 显式把两个流切到 UTF-8，保证 macOS / Linux / Windows 行为一致。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:  # Python < 3.7 或不可重配置的流
        pass



TYPE_LABELS = {
    "screen_recording": "真实录屏",
    "screenshot": "截图",
    "illustration": "插图",
    "video": "补充视频",
    "diagram_table": "图表/表格",
    "mask_overlay": "蒙版素材",
    "other": "其他素材",
}


def fmt_time(value: float) -> str:
    minutes = int(value // 60)
    seconds = value - minutes * 60
    return f"{minutes:02d}:{seconds:05.2f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Write upload and asset-library requests")
    ap.add_argument("materials_json", type=Path)
    ap.add_argument("output_md", type=Path)
    args = ap.parse_args()
    if not args.materials_json.exists():
        print(f"未找到素材需求文件: {args.materials_json}", file=sys.stderr)
        return 1
    data = json.loads(args.materials_json.read_text(encoding="utf-8"))
    inserts = data.get("inserts", [])
    lines = [
        "# 后续需要上传/调用的素材清单",
        "",
        "这是一份识别阶段的需求清单，不代表素材已经准备，也不会在本阶段调用素材库或生成素材。",
        "",
    ]
    if not inserts:
        lines.append("当前没有识别到必须插入的外部素材。")
    for i, item in enumerate(inserts, 1):
        kind = TYPE_LABELS.get(item.get("insert_type"), item.get("insert_type", "未指定"))
        source = item.get("material_source", "未指定")
        status = item.get("asset_status", "missing")
        lines.extend([
            f"## {i}. [{fmt_time(float(item['start']))}–{fmt_time(float(item['end']))}] {kind}",
            "",
            f"- 对应口播：{item.get('spoken_text', '')}",
            f"- 当前来源决策：`{source}`",
            f"- 素材状态：`{status}`",
            f"- 内容要求：{item.get('content_requirements', '')}",
            f"- 建议时长：{item.get('suggested_duration', item['end'] - item['start'])} 秒",
            f"- 建议画幅：{item.get('required_aspect', '根据成片画幅适配')}",
            f"- 建议文件类型：{', '.join(item.get('required_file_types', [])) or '由下游执行流程确认'}",
        ])
        if item.get("library_query"):
            lines.append(f"- 后续资产库检索词：{item['library_query']}")
        if item.get("generation_prompt"):
            lines.append(f"- 可选生成提示词：{item['generation_prompt']}")
        if item.get("human_review"):
            lines.append("- 人工确认：是")
        lines.append("")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    with args.output_md.open("w", encoding="utf-8", newline="\n") as _f:
        _f.write("\n".join(lines))
    print(f"✅ 素材上传/调用清单: {args.output_md}")
    print(f"   共 {len(inserts)} 个素材需求；未执行任何资产调用")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
