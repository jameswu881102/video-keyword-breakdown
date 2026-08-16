#!/usr/bin/env python3
"""Test suite for video-keyword-breakdown.

Fixture-driven: tests/fixtures/ holds one valid handoff package. Each negative
test mutates a copy with a single deliberate defect and asserts the validator
catches exactly that. The valid package guards the other direction — a
validator that rejects everything is as useless as one that accepts everything.

Runs identically on macOS, Linux and Windows: no ffmpeg, no network, no
optional dependencies. Every subprocess is decoded as UTF-8 explicitly so the
Windows locale codepage cannot corrupt the Chinese output.

Run:  python3 tests/test_scripts.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "video-keyword-breakdown"
SCRIPTS = SKILL / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

EXPECTED_SCRIPTS = {
    "keyword_candidates.py",
    "srt_to_transcript_json.py",
    "validate_analysis_outputs.py",
    "write_material_requests.py",
}

failures = []
checks = 0


def run(args, **kw):
    return subprocess.run([sys.executable, *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", **kw)


def check(label, condition, detail=""):
    global checks
    checks += 1
    if not condition:
        failures.append(f"{label}: {detail}" if detail else label)


def validate(pkg: Path, duration="13.2", **override):
    args = {
        "--transcript": pkg / "transcript.json",
        "--keywords": pkg / "keywords_timeline.json",
        "--materials": pkg / "material_inserts.json",
        "--subtitle-plan": pkg / "subtitle_plan.json",
        "--edit-plan": pkg / "edit_plan.json",
    }
    args.update(override)
    flat = [x for kv in args.items() for x in kv]
    return run([SCRIPTS / "validate_analysis_outputs.py", *flat, "--duration", duration])


# --- 1. package shape ------------------------------------------------------

found = {p.name for p in SCRIPTS.glob("*.py")}
check("脚本集合与预期一致", found == EXPECTED_SCRIPTS,
      f"多出 {found - EXPECTED_SCRIPTS}，缺少 {EXPECTED_SCRIPTS - found}")

for ref in ("keyword-taxonomy", "analysis-frameworks", "analysis-handoff"):
    check(f"references/{ref}.md 存在", (SKILL / "references" / f"{ref}.md").is_file())

check("SKILL.md 存在", (SKILL / "SKILL.md").is_file())


# --- 2. no network, no secrets, no personal paths --------------------------

NETWORK = re.compile(r"\bimport\s+(requests|httpx|urllib\.request|socket)\b|https?://(?!schema|www\.w3)")
PERSONAL = re.compile(r"/Users/(?!xxx|YOUR|<)[A-Za-z0-9._-]+|C:\\\\Users\\\\(?!xxx)")
SECRET = re.compile(r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|api[_-]?key\s*=\s*[\"'][A-Za-z0-9]{8,})",
                    re.IGNORECASE)
BANNED = re.compile(r"elevenlabs|bilibili|api\.douyin|browser_cookie3|yt_dlp", re.IGNORECASE)

for path in sorted(SKILL.rglob("*")):
    if not path.is_file() or "__pycache__" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    rel = path.relative_to(ROOT)
    if path.suffix == ".py":
        m = NETWORK.search(text)
        check(f"{rel} 无网络调用", not m, m.group(0) if m else "")
    m = PERSONAL.search(text)
    check(f"{rel} 无个人绝对路径", not m, m.group(0) if m else "")
    m = SECRET.search(text)
    check(f"{rel} 无硬编码密钥", not m, m.group(0)[:24] if m else "")
    if path.suffix == ".py":
        m = BANNED.search(text)
        check(f"{rel} 无已移除的平台集成残留", not m, m.group(0) if m else "")


# --- 3. every script is self-documenting and UTF-8 safe --------------------

for script in sorted(SCRIPTS.glob("*.py")):
    r = run([script, "--help"])
    check(f"{script.name} --help 退出码 0", r.returncode == 0, r.stderr[:160])
    check(f"{script.name} 打印用法", "usage" in (r.stdout + r.stderr).lower())

    # The Windows failure mode: ANSI codepage cannot encode the Chinese output.
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    r = run([script, "--help"], env=env)
    check(f"{script.name} 在 cp1252 环境下不崩",
          "UnicodeEncodeError" not in r.stderr,
          r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "")


# --- 4. SRT -> transcript.json --------------------------------------------

with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "transcript.json"
    r = run([SCRIPTS / "srt_to_transcript_json.py", FIXTURES / "sample.srt", out,
             "--source", "provided"])
    check("srt_to_transcript_json 退出码 0", r.returncode == 0, r.stderr[:200])

    if out.is_file():
        d = json.loads(out.read_text(encoding="utf-8"))
        check("source 字段正确", d.get("source") == "provided", repr(d.get("source")))
        check("解析出 4 段", len(d.get("segments", [])) == 4, str(len(d.get("segments", []))))
        check("duration 约 13.2", abs(float(d.get("duration", 0)) - 13.2) < 0.5,
              repr(d.get("duration")))
        segs = d.get("segments", [])
        if segs:
            check("首段 start=0.32", abs(segs[0]["start"] - 0.32) < 0.01, repr(segs[0]["start"]))
            check("时间轴单调递增",
                  all(segs[i]["end"] <= segs[i + 1]["start"] + 1e-3 for i in range(len(segs) - 1)))
            check("中文文本无损", "百分之80" in segs[1]["text"], segs[1]["text"])
        # 写出的文件必须是纯 LF，避免 Windows 上 CRLF 污染
        check("输出为纯 LF", b"\r\n" not in out.read_bytes())
    else:
        check("srt_to_transcript_json 产出文件", False, "输出文件不存在")


# --- 5. mechanical keyword recall -----------------------------------------

with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "candidates.json"
    r = run([SCRIPTS / "keyword_candidates.py", FIXTURES / "transcript.json", out])
    check("keyword_candidates 退出码 0", r.returncode == 0, r.stderr[:200])

    if out.is_file():
        blob = json.dumps(json.loads(out.read_text(encoding="utf-8")), ensure_ascii=False)
        check("召回结果非空", len(blob) > 20)
        check("数字/统计规则命中", "NUMBER_STAT" in blob, blob[:200])
        check("CTA 区规则命中", "CTA" in blob, blob[:200])


# --- 6. handoff validator: positive case ----------------------------------

with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    good = tmp / "good"
    good.mkdir()
    for f in FIXTURES.glob("*.json"):
        shutil.copy(f, good / f.name)

    r = validate(good)
    check("完整方案包校验通过", r.returncode == 0, (r.stdout + r.stderr)[:400])

    # --- negative cases: one deliberate defect each -----------------------

    def mutate(name, filename, fn, expect):
        bad = tmp / f"bad_{abs(hash(name))}"
        if bad.exists():
            shutil.rmtree(bad)
        bad.mkdir()
        for f in FIXTURES.glob("*.json"):
            shutil.copy(f, bad / f.name)
        target = bad / filename
        data = json.loads(target.read_text(encoding="utf-8"))
        fn(data)
        target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        res = validate(bad)
        out = res.stdout + res.stderr
        check(f"拒绝：{name}", res.returncode != 0, "校验器放行了坏数据")
        check(f"理由提到 {expect}：{name}", expect in out, out[:300])

    mutate("tier3 混入 keywords_timeline", "keywords_timeline.json",
           lambda d: d["keywords"][0].__setitem__("visual_tier", "tier3_external_insert"),
           "visual_tier")
    mutate("非法语义标签", "keywords_timeline.json",
           lambda d: d["keywords"][0].__setitem__("tag", "NOT_A_REAL_TAG"), "tag")
    mutate("缺少分级理由", "keywords_timeline.json",
           lambda d: d["keywords"][0].__setitem__("reason", "   "), "reason")
    mutate("关键词不在文稿中", "keywords_timeline.json",
           lambda d: d["keywords"][0].__setitem__("text", "这句话文稿里根本没有"), "文稿")
    mutate("非法素材来源", "material_inserts.json",
           lambda d: d["inserts"][0].__setitem__("material_source", "somewhere_else"),
           "material_source")
    mutate("local_required 却允许 AI 顶替", "material_inserts.json",
           lambda d: d["inserts"][0].__setitem__("ai_generation_allowed", True), "AI")
    mutate("字幕缺可读性风险标记", "subtitle_plan.json",
           lambda d: d["subtitles"][0].pop("legibility_risk", None), "legibility_risk")
    mutate("绕过人工闸门", "edit_plan.json",
           lambda d: d.__setitem__("analysis_status", "completed"), "analysis_status")
    mutate("混入 EDL 执行字段", "edit_plan.json",
           lambda d: d.__setitem__("ranges", [{"start": 0, "end": 5}]), "ranges")
    mutate("确认清单为空", "edit_plan.json",
           lambda d: d.__setitem__("required_confirmation", []), "required_confirmation")

    # --duration is optional; omitting it must still validate structure
    flat = [x for kv in {
        "--transcript": good / "transcript.json",
        "--keywords": good / "keywords_timeline.json",
        "--materials": good / "material_inserts.json",
        "--subtitle-plan": good / "subtitle_plan.json",
        "--edit-plan": good / "edit_plan.json",
    }.items() for x in kv]
    r = run([SCRIPTS / "validate_analysis_outputs.py", *flat])
    check("省略 --duration 仍可校验", r.returncode == 0, (r.stdout + r.stderr)[:300])


# --- 7. material request markdown -----------------------------------------

with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "material_requests.md"
    r = run([SCRIPTS / "write_material_requests.py", FIXTURES / "material_inserts.json", out])
    check("write_material_requests 退出码 0", r.returncode == 0, r.stderr[:200])
    if out.is_file():
        md = out.read_text(encoding="utf-8")
        check("清单含台词原文", "压到20分钟" in md, md[:200])
        check("清单含素材类型", "screen_recording" in md or "录屏" in md, md[:200])
        check("清单非空", len(md.strip()) > 50)
        check("输出为纯 LF", b"\r\n" not in out.read_bytes())


# --- report ---------------------------------------------------------------

print("running video-keyword-breakdown test suite\n")
print(f"{checks} checks")
if failures:
    print(f"{len(failures)} failed\n")
    for f in failures:
        print(f"  FAIL {f}")
    sys.exit(1)
print("all passed")
