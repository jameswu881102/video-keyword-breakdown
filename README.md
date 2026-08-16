# video-keyword-breakdown

English · [简体中文](README.zh-CN.md)

**A keyword tagger and edit-plan generator for talking-head videos.** Give it a transcript, and it returns a timestamped keyword timeline, a subtitle plan, and a shopping list of B-roll you need to supply — then it stops and waits for you.

It does not cut video. That is deliberate: separating analysis from execution means you see exactly how it intends to treat your footage before anything is rendered.

**Compatibility**

- **Agents** — Claude Code, Codex CLI, and any agent that reads the SKILL.md format. The installer detects which you have and installs to both if you run both.
- **Platforms** — macOS, Linux, Windows. Use `install.sh` on macOS/Linux and `install.ps1` on Windows; CI covers all three.
- **Dependencies** — Python 3.9+ and nothing else. **No ffmpeg, no network access, no API keys.**

---

## The problem it solves

The slow part of editing a talking-head video isn't the cutting — it's deciding **which words to emphasize, how to emphasize them, and where to cut away to something else.** That judgment normally means scrubbing the timeline sentence by sentence, and a ten-minute video can eat two hours before a single cut is made.

This skill turns that pass into structured output:

| Decision you have to make | What it hands you |
|---|---|
| Which words get a full-screen animated callout | tier1 list with timings, source text, duration, motion intent |
| Which words get bolded or colored inline | tier2 list with styling |
| Where to insert a screen recording, screenshot, or chart | tier3 list with asset type, specs, search terms or AI prompts |
| Subtitle size, placement, legibility risk | Size/safe-area/stroke recommendations with a `legibility_risk` flag |
| Which passages can be cut | Structural timeline marking hook, pain point, demo, and CTA |

---

## The three-tier keyword system

This is the core idea. Keywords aren't sorted into "important" and "unimportant" — they're sorted by **how they should be presented**:

**Tier 1 — `tier1_standalone_dynamic`.** Text that breaks out of the subtitle track entirely: numbers, conclusions, brand names. The skill records the intent, timing, and spec; it does not generate the animation.

**Tier 2 — `tier2_inline_emphasis`.** Color, weight, or size emphasis inside the existing subtitle line. Stays in the subtitle flow but needs to pop.

**Tier 3 — `tier3_external_insert`.** Points where footage alone isn't enough. The skill distinguishes where the asset comes from: `local_required` (you must upload it), `library_match` (search your own library), or `ai_generatable` (generate it, prompt included).

Full tag definitions, JSON schemas, and review criteria are in [`references/keyword-taxonomy.md`](video-keyword-breakdown/references/keyword-taxonomy.md).

---

## Where the transcript comes from

**This tool does not transcribe audio and does not download video.** It consumes a transcript you already have:

1. An SRT, script, or CapCut caption file you supply
2. An embedded subtitle track, extracted by your agent or another tool
3. Burned-in subtitles, read off the frames by your agent

Convert the SRT into a unified `transcript.json` with `srt_to_transcript_json.py`; every later stage reads that.

> This is a deliberate narrowing. An earlier version bundled speech recognition, a platform subtitle API, and a video downloader — which dragged in a paid cloud API, browser-cookie reading, and platform coupling. All of it is gone. **The tool does the one thing it is actually good at: turning a transcript into an edit plan.**

---

## Install

### macOS / Linux

```bash
git clone https://github.com/jameswu881102/video-keyword-breakdown.git
cd video-keyword-breakdown
bash install.sh
```

### Windows

```powershell
git clone https://github.com/jameswu881102/video-keyword-breakdown.git
cd video-keyword-breakdown
powershell -ExecutionPolicy Bypass -File install.ps1
```

Both scripts behave identically and detect which agents you have:

| Agent | Skills directory | Convention file |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `~/.claude/CLAUDE.md` |
| Codex CLI | `~/.codex/skills/` | `~/.codex/AGENTS.md` |

If both are present it installs to both. If neither is detected it tells you to name a target. Re-running never duplicates the convention block.

To install elsewhere:

```bash
# macOS / Linux
SKILL_DIR=/your/skills/dir AGENTS_MD=/your/AGENTS.md bash install.sh
```

```powershell
# Windows
$env:SKILL_DIR="C:\your\skills"; $env:AGENTS_MD="C:\your\AGENTS.md"; .\install.ps1
```

**Manual install** — copy the `video-keyword-breakdown/` directory into your agent's skills directory. No build step, no packages to install.

---

## Usage

Once installed, just ask:

> Break down this talking-head video; captions are at /path/to/video.srt

or "tier the keywords in this script", or "what B-roll does this section need".

### Output

The plan package is written to `<video directory>/edit/`:

| File | Contents |
|---|---|
| `transcript.json` | Timestamped transcript |
| `keyword_candidates.json` | Mechanical recall output (**candidates, not conclusions**) |
| `keywords_timeline.json` | Tier 1/2 keywords with visual treatment intent |
| `material_inserts.json` | Tier 3 external asset requirements |
| `subtitle_plan.json` | Subtitle tiers, sizes, positions, safe areas |
| `edit_plan.json` | Overall plan and open questions (**not an EDL**) |
| `material_requests.md` | Upload checklist you can hand straight to a collaborator |
| `human_review.md` | Sign-off sheet |

### Scripts

| Script | Purpose |
|---|---|
| `srt_to_transcript_json.py` | SRT → unified transcript.json |
| `keyword_candidates.py` | Mechanical keyword recall |
| `write_material_requests.py` | Generate the asset request Markdown |
| `validate_analysis_outputs.py` | Structural validation of the plan package |

---

## Scope

This skill **analyzes and hands off. It does not execute.**

- ✅ Analyze structure, tier keywords, spec subtitles, list assets, emit a plan awaiting sign-off
- ❌ No cutting, splicing, grading, mixing, or rendering; no ASS subtitles or motion graphics
- ❌ **No video downloading, no platform cookies, no platform subtitle APIs, no API calls of any kind**
- ❌ No asset-library calls, no picking or downloading assets for you, no fabricating real software UI
- ❌ No EDL and no render stage before a human signs off

Writes are confined to `<video directory>/edit/` or a directory you name. The source video is read-only.

**Handoff** — once the plan is approved, pass it to your own editing skill. That skill is not distributed with this repo; you supply its path. The handoff contract is in [`references/analysis-handoff.md`](video-keyword-breakdown/references/analysis-handoff.md).

---

## Known limits

**It can't see what you didn't say.** Analysis runs on the transcript, not on the picture. On-screen information the narration never mentions is invisible to it.

**Mechanical recall is only a shortlist.** A rule firing does not mean the word matters, nor that the tier is right. Final tiering must be reviewed against full context — `keyword_candidates.py` says so in its own output, repeatedly.

**Subtitle recommendations assume 1080×1920 vertical.** Other aspect ratios need their own math.

---

## Development

After changing any script:

```bash
python3 tests/test_scripts.py
```

80 checks, covering: script-set consistency, **repo hygiene scans for zero network calls / zero secrets / zero personal paths**, Windows encoding regressions, SRT conversion schema, recall rule hits, and the plan validator's 1 positive plus 10 negative cases.

When you add a check, add a fixture and an assertion with it — the suite is fixture-driven.

CI covers Ubuntu / macOS / Windows × Python 3.9 / 3.12, and runs the platform's actual install script on each.

---

## License

MIT
