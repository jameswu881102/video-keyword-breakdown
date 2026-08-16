#!/usr/bin/env python3
"""Validate the analysis-only handoff package.

This gate intentionally does not know about EDLs, overlays, ASS files, or
rendered videos. It checks that the recognition outputs are structurally safe
for a later, human-confirmed editing workflow.
"""

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



TIERS = {"tier1_standalone_dynamic", "tier2_inline_emphasis"}
TAGS = {
    "HOOK", "EMOTION_PEAK", "CTA", "SOCIAL_CURRENCY", "NUMBER_STAT",
    "BRAND_KEYWORD", "RHETORIC", "TRANSITION",
}
MATERIAL_SOURCES = {"local_required", "library_match", "ai_generatable"}


def load(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"文件不存在: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 无法解析: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON 根节点必须是对象: {path}")
    return data


def resolve_duration(data: dict, errors: list[str]) -> float:
    """Resolve the validation horizon from transcript data only."""
    segments = data.get("segments") or []
    ends = [
        float(segment["end"])
        for segment in segments
        if isinstance(segment, dict)
        and isinstance(segment.get("end"), (int, float))
        and not isinstance(segment.get("end"), bool)
    ]
    max_end = max(ends, default=0.0)
    declared = data.get("duration")
    if declared is not None:
        if not isinstance(declared, (int, float)) or isinstance(declared, bool) or declared <= 0:
            errors.append("transcript.json: duration 必须是正数")
        elif max_end > float(declared) + 0.25:
            errors.append(
                f"transcript.json: 最后一段结束时间 {max_end:.3f} 超出声明时长 {float(declared):.3f}"
            )
        else:
            return float(declared)
    return max_end


def check_range(item: dict, label: str, duration: float, errors: list[str]) -> None:
    start, end = item.get("start"), item.get("end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        errors.append(f"{label}: start/end 必须是数字")
        return
    if start < 0 or end <= start:
        errors.append(f"{label}: 时间范围无效 {start} → {end}")
    if end > duration + 0.25:
        errors.append(f"{label}: end={end:.3f} 超出视频时长 {duration:.3f}")


def validate_transcript(data: dict, duration: float, errors: list[str]) -> None:
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("transcript.json: segments 必须是非空数组")
        return
    previous = -1.0
    for i, segment in enumerate(segments, 1):
        check_range(segment, f"transcript 第 {i} 段", duration, errors)
        start = segment.get("start")
        if isinstance(start, (int, float)) and start < previous:
            errors.append(f"transcript 第 {i} 段: 时间未按升序排列")
        if isinstance(start, (int, float)):
            previous = start
        if not str(segment.get("text", "")).strip():
            errors.append(f"transcript 第 {i} 段: text 为空")


def validate_keywords(data: dict, transcript: dict, duration: float, errors: list[str]) -> None:
    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        errors.append("keywords_timeline.json: keywords 必须是数组")
        return
    transcript_segments = transcript.get("segments") or []
    for i, item in enumerate(keywords, 1):
        label = f"关键词第 {i} 条"
        check_range(item, label, duration, errors)
        if item.get("visual_tier") not in TIERS:
            errors.append(f"{label}: visual_tier 必须是 tier1 或 tier2")
        if item.get("tag") not in TAGS:
            errors.append(f"{label}: tag 不在允许集合中")
        if not str(item.get("text", "")).strip():
            errors.append(f"{label}: text 为空")
        for required in ("reason", "screen_position", "suggested_treatment", "confidence"):
            if not str(item.get(required, "")).strip():
                errors.append(f"{label}: 缺少 {required}")
        if item.get("confidence") not in {"high", "medium", "low", "needs_human_review"}:
            errors.append(f"{label}: confidence 不合法")
        text = str(item.get("text", "")).strip()
        start, end = item.get("start"), item.get("end")
        if text and isinstance(start, (int, float)) and isinstance(end, (int, float)):
            overlapping = [
                str(seg.get("text", ""))
                for seg in transcript_segments
                if isinstance(seg.get("start"), (int, float))
                and isinstance(seg.get("end"), (int, float))
                and seg["start"] < end
                and seg["end"] > start
            ]
            if text not in "".join(overlapping):
                errors.append(f"{label}: text 未在对应时间段的字幕中找到：{text}")


def validate_materials(data: dict, duration: float, errors: list[str]) -> None:
    inserts = data.get("inserts")
    if not isinstance(inserts, list):
        errors.append("material_inserts.json: inserts 必须是数组")
        return
    for i, item in enumerate(inserts, 1):
        label = f"素材需求第 {i} 条"
        check_range(item, label, duration, errors)
        if item.get("material_source") not in MATERIAL_SOURCES:
            errors.append(f"{label}: material_source 不合法")
        for required in ("spoken_text", "insert_type", "content_requirements", "asset_status"):
            if not str(item.get(required, "")).strip():
                errors.append(f"{label}: 缺少 {required}")
        if item.get("ai_generation_allowed") is True and item.get("material_source") == "local_required":
            errors.append(f"{label}: local_required 不应同时允许 AI 顶替")
        source = item.get("material_source")
        if source == "library_match":
            matched = str(item.get("matched_asset_path", "")).strip()
            if not matched:
                errors.append(f"{label}: library_match 缺少 matched_asset_path")
            elif Path(matched).is_absolute() and not Path(matched).exists():
                errors.append(f"{label}: matched_asset_path 不存在：{matched}")
        if source == "ai_generatable":
            if item.get("generation_media_type") not in {"image", "video"}:
                errors.append(f"{label}: ai_generatable 缺少合法 generation_media_type")
            if not str(item.get("generation_prompt", "")).strip():
                errors.append(f"{label}: ai_generatable 缺少 generation_prompt")
        if source == "local_required" and (item.get("generation_media_type") or item.get("generation_prompt")):
            errors.append(f"{label}: local_required 不应包含生成字段")


def validate_subtitle_plan(data: dict, duration: float, errors: list[str]) -> None:
    items = data.get("subtitles")
    if not isinstance(items, list):
        errors.append("subtitle_plan.json: subtitles 必须是数组")
        return
    for i, item in enumerate(items, 1):
        label = f"字幕方案第 {i} 条"
        check_range(item, label, duration, errors)
        size = item.get("font_size_px")
        if not isinstance(size, (int, float)) or size < 48:
            errors.append(f"{label}: font_size_px 过小或缺失")
        if not str(item.get("screen_position", "")).strip():
            errors.append(f"{label}: 缺少 screen_position")
        if not str(item.get("legibility_risk", "")).strip():
            errors.append(f"{label}: 缺少 legibility_risk")


def validate_edit_plan(data: dict, errors: list[str]) -> None:
    if data.get("analysis_status") != "awaiting_human_confirmation":
        errors.append("edit_plan.json: analysis_status 必须是 awaiting_human_confirmation")
    forbidden = ("ranges", "overlays", "subtitles", "preview", "final")
    for key in forbidden:
        if key in data:
            errors.append(f"edit_plan.json: 不应包含下游执行字段 {key}")
    if not isinstance(data.get("required_confirmation"), list) or not data["required_confirmation"]:
        errors.append("edit_plan.json: required_confirmation 必须是非空数组")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate video keyword analysis handoff outputs")
    ap.add_argument("--transcript", type=Path, required=True)
    ap.add_argument("--keywords", type=Path, required=True)
    ap.add_argument("--materials", type=Path, required=True)
    ap.add_argument("--subtitle-plan", type=Path, required=True)
    ap.add_argument("--edit-plan", type=Path, required=True)
    ap.add_argument("--duration", type=float, help="可选：上游确认的媒体时长（秒）")
    args = ap.parse_args()
    errors: list[str] = []
    try:
        transcript_data = load(args.transcript)
        duration = args.duration if args.duration is not None else resolve_duration(transcript_data, errors)
        if duration <= 0:
            errors.append("无法从文字稿得到正的时间范围")
        validate_transcript(transcript_data, duration, errors)
        validate_keywords(load(args.keywords), transcript_data, duration, errors)
        validate_materials(load(args.materials), duration, errors)
        validate_subtitle_plan(load(args.subtitle_plan), duration, errors)
        validate_edit_plan(load(args.edit_plan), errors)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    if errors:
        print("❌ 分析方案校验失败：")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("✅ 分析方案结构和时间范围校验通过")
    print(f"   文字稿覆盖时长: {duration:.3f}s")
    print("   下游执行未启动：等待人工确认")
    return 0


if __name__ == "__main__":
    sys.exit(main())
