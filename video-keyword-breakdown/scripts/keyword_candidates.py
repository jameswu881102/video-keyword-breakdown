#!/usr/bin/env python3
"""关键词候选检测（机械启发式初筛）。

这是"关键词自动识别与标注"流程中的机械前置步骤：用规则和位置特征
（数字、强语气标点、时间区位、重复结构、静音间隔等）从 transcript.json
中挑出**候选**关键词片段，连同触发规则一并输出为 keyword_candidates.json。

⚠️ 这一步只做召回，不做语义判断，也不做分级——规则命中不代表标签/级别
一定正确。真正的语义分类（这段话到底是不是 Hook？该分 tier1 独立跳出还是
tier2 字幕内强调？还是 tier3 需要额外插入素材？）需要由使用本 skill 的
Claude 结合完整文稿、上文语境（以及画面证据，如果有的话）和
references/keyword-taxonomy.md 里的判断标准来复核、增删、定级、定档，
最终分别写出 keywords_timeline.json（tier1/tier2）和
material_inserts.json（tier3，`EXTERNAL_INSERT_CANDIDATE` 命中的候选）。

用法:
    python keyword_candidates.py <transcript.json> <输出candidates.json>
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


# ---------------------------------------------------------------------------
# 规则定义：每条规则产出一个建议标签 + 命中原因，供 Claude 复核
# ---------------------------------------------------------------------------

NUMBER_STAT_RE = re.compile(
    r"(\d+(\.\d+)?\s*%|百分之\d+|\d+\s*(个|种|条|步|天|年|万|亿|倍)|第[一二三四五六七八九十\d]+|"
    r"最[强大快多好高低]|首个|唯一)"
)

CTA_RE = re.compile(
    r"(点赞|关注|收藏|评论区|评论|转发|分享|扫码|私信|链接|下方|置顶|主页|购买|下单|抢购|"
    r"限时|优惠券|立即|马上|现在就|戳|点击|订阅|subscribe|link in bio)"
)

SOCIAL_CURRENCY_RE = re.compile(
    r"(扩散|告诉朋友|谁懂|挑战|@|艾特|求扩散|转给|安利|种草|回复|抱团|一起)"
)

EMOTION_RE = re.compile(
    r"([!！]{1,3}|太.{0,3}了|绝了|哭了|破防|真实|离谱|谁懂|爽|泪目|感动|气死|笑死|吓死|震惊)"
)

HOOK_PHRASE_RE = re.compile(
    r"(你是不是|你有没有|为什么|没想到|万万没想到|居然|竟然|谁能想到|90%的人|大部分人不知道|"
    r"很多人不知道|反常识|你绝对想不到|从来没告诉过你|第一次听说)"
)

BRAND_QUOTE_RE = re.compile(r"[《「\"']([^》」\"']{1,20})[》」\"']")

REPEAT_WORD_RE = re.compile(r"(.{2,6})\1")  # 简单重复结构（排比/强调）近似检测

# tier3（外部素材插入）候选：台词提到一个"外部的东西"——工具/参考视频/
# 截图/录屏/图表——但画面里未必已经清楚展示，值得考虑插入额外素材。
# 命中这里的候选只是"要不要考虑加素材"的信号，具体 insert_type /
# material_source / generation_prompt 都需要 Claude 结合画面判断，
# 见 references/keyword-taxonomy.md 第一节 tier3 部分。
EXTERNAL_INSERT_RE = re.compile(
    r"(这个插件|这款工具|这个工具|这个软件|这个网站|这个APP|这个应用|"
    r"对标视频|参考视频|参考案例|这段视频|这条视频|这张图|这个案例|"
    r"截图|录屏|截屏|效果图|流程图|示意图|这个功能|这个界面)"
)


def classify_segment(text: str) -> list[dict]:
    """对单条字幕文本跑全部规则，返回命中的候选标签列表。"""
    hits = []

    if NUMBER_STAT_RE.search(text):
        hits.append({"tag": "NUMBER_STAT", "rule": "数字/排名/最高级表达"})

    if CTA_RE.search(text):
        hits.append({"tag": "CTA", "rule": "行动号召关键词"})

    if SOCIAL_CURRENCY_RE.search(text):
        hits.append({"tag": "SOCIAL_CURRENCY", "rule": "传播/扩散型表达"})

    if EMOTION_RE.search(text):
        hits.append({"tag": "EMOTION_PEAK", "rule": "强语气标点或情绪词"})

    if HOOK_PHRASE_RE.search(text):
        hits.append({"tag": "HOOK", "rule": "痛点/反常识/悬念句式"})

    quote_match = BRAND_QUOTE_RE.search(text)
    if quote_match:
        hits.append({"tag": "BRAND_KEYWORD", "rule": f"引号/书名号内专名: {quote_match.group(1)}"})

    if REPEAT_WORD_RE.search(text) and len(text) > 6:
        hits.append({"tag": "RHETORIC", "rule": "重复/排比结构"})

    ext_match = EXTERNAL_INSERT_RE.search(text)
    if ext_match:
        hits.append({
            "tag": "EXTERNAL_INSERT_CANDIDATE",
            "rule": f"提到外部指代物「{ext_match.group(1)}」，考虑是否需要 tier3 素材插入（录屏/截图/插图/图表）",
        })

    return hits


def detect_transitions(segments: list[dict], gap_threshold: float = 1.2) -> list[dict]:
    """相邻字幕间隔 >= gap_threshold 秒的位置标记为 TRANSITION 候选（天然剪辑卡点）。"""
    transitions = []
    for i in range(1, len(segments)):
        prev_end = segments[i - 1]["end"]
        cur_start = segments[i]["start"]
        gap = cur_start - prev_end
        if gap >= gap_threshold:
            transitions.append({
                "index": segments[i]["index"],
                "start": prev_end,
                "end": cur_start,
                "text": "(静音间隔)",
                "candidates": [{
                    "tag": "TRANSITION",
                    "rule": f"静音间隔 {gap:.2f}s ≥ {gap_threshold}s，适合作转场/卡点",
                }],
            })
    return transitions


def main() -> None:
    ap = argparse.ArgumentParser(description="Detect candidate keyword spans from transcript.json")
    ap.add_argument("transcript_json", type=Path)
    ap.add_argument("out_json", type=Path)
    ap.add_argument("--hook-zone-pct", type=float, default=0.08, help="开头多少比例的时长算 Hook 区（默认前8%%）")
    ap.add_argument("--cta-zone-pct", type=float, default=0.10, help="结尾多少比例的时长算 CTA 区（默认后10%%）")
    ap.add_argument("--gap-threshold", type=float, default=1.2, help="判定为 TRANSITION 的静音间隔秒数")
    args = ap.parse_args()

    if not args.transcript_json.exists():
        sys.exit(f"未找到 transcript.json: {args.transcript_json}")

    data = json.loads(args.transcript_json.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    duration = data.get("duration") or (segments[-1]["end"] if segments else 0.0)

    hook_cutoff = duration * args.hook_zone_pct
    cta_cutoff = duration * (1 - args.cta_zone_pct)

    candidates = []
    for seg in segments:
        hits = classify_segment(seg["text"])

        # 区位加成：开头/结尾区域即使没命中关键词规则，也标记为区位候选，
        # 交给 Claude 判断是否真的承担 Hook / CTA 功能。
        if seg["start"] <= hook_cutoff:
            hits.append({"tag": "HOOK", "rule": f"位于开头 {args.hook_zone_pct:.0%} 时间区（黄金开场位）"})
        if seg["end"] >= cta_cutoff:
            hits.append({"tag": "CTA", "rule": f"位于结尾 {args.cta_zone_pct:.0%} 时间区（收尾行动位）"})

        if hits:
            candidates.append({
                "index": seg["index"],
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "candidates": hits,
            })

    candidates.extend(detect_transitions(segments, args.gap_threshold))
    candidates.sort(key=lambda c: c["start"])

    payload = {
        "duration": duration,
        "hook_zone_end": round(hook_cutoff, 2),
        "cta_zone_start": round(cta_cutoff, 2),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    with args.out_json.open("w", encoding="utf-8", newline="\n") as _f:
        _f.write(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"✅ 检测到 {len(candidates)} 个候选片段 → {args.out_json}")
    print("   下一步：结合完整文稿（和画面，如果有的话）与 references/keyword-taxonomy.md")
    print("   复核、去重、定级（tier1/tier2/tier3）、定档标签，分别写出：")
    print("     - keywords_timeline.json  （tier1_standalone_dynamic / tier2_inline_emphasis）")
    print("     - material_inserts.json   （tier3_external_insert，即 EXTERNAL_INSERT_CANDIDATE 复核后的结果）")
    print("   不要直接把候选结果当最终结果使用。")


if __name__ == "__main__":
    main()
