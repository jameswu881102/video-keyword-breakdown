#!/usr/bin/env python3
"""将 SRT 字幕文件转换为统一的 transcript.json 结构。

统一 schema 让下游脚本（keyword_candidates.py、validate_analysis_outputs.py）
只消费带时间戳的文字稿，不关心文字稿由用户还是上游流程整理：

{
  "source": "provided",            # provided | user | upstream
  "duration": 812.4,               # 最后一条字幕的结束时间（近似总时长）
  "segments": [
    {"index": 1, "start": 0.32, "end": 2.81, "text": "..."},
    ...
  ]
}

用法:
    python srt_to_transcript_json.py <输入.srt> <输出transcript.json> [--source provided]
"""

from __future__ import annotations

import argparse
import json
import re
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


TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)


def _to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(srt_path: Path) -> list[dict]:
    raw = srt_path.read_text(encoding="utf-8", errors="ignore")
    blocks = re.split(r"\n\s*\n", raw.strip())
    segments = []
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        # first line may be an index number, second the timecode — but be
        # lenient in case the index line is missing.
        time_line = None
        text_lines = []
        for line in lines:
            m = TIME_RE.search(line)
            if m:
                time_line = m
                continue
            if time_line is not None:
                text_lines.append(line.strip())
        if time_line is None or not text_lines:
            continue
        start = _to_seconds(*time_line.group(1, 2, 3, 4))
        end = _to_seconds(*time_line.group(5, 6, 7, 8))
        text = " ".join(text_lines).strip()
        if not text:
            continue
        segments.append({
            "index": len(segments) + 1,
            "start": round(start, 2),
            "end": round(end, 2),
            "text": text,
        })
    return segments


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert SRT to unified transcript.json")
    ap.add_argument("srt_path", type=Path)
    ap.add_argument("out_path", type=Path)
    ap.add_argument("--source", default="provided", choices=["provided", "user", "upstream"])
    args = ap.parse_args()

    if not args.srt_path.exists():
        sys.exit(f"未找到 SRT 文件: {args.srt_path}")

    segments = parse_srt(args.srt_path)
    if not segments:
        sys.exit("SRT 中未解析出任何字幕条目，请检查文件格式")

    duration = segments[-1]["end"] if segments else 0.0
    payload = {"source": args.source, "duration": duration, "segments": segments}
    with args.out_path.open("w", encoding="utf-8", newline="\n") as _f:
        _f.write(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"✅ 已生成 {args.out_path} （{len(segments)} 条片段，时长约 {duration:.1f}s）")


if __name__ == "__main__":
    main()
