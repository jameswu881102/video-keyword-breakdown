# Changelog

## [0.2.0] - 2026-08-19

### Added
- **`references/visual-treatment-spec.md`** — the presentation spec that tier1/tier3 entries hand
  downstream. Previously a tier1 entry said only "standalone animated text", which downstream had to
  interpret freshly every time. It now picks from six named forms (`holo_title`, `signal_rows`,
  `icon_dock`, `mini_panel`, `data_strip`, `source_shot`) and carries required fields.
- **Row-level reveal timing.** A container may enter early, but each row inside it is an independently
  timed asset revealed at its own spoken cue. Handing the whole block one timestamp puts the answer
  on screen before the sentence is finished.
- **Spoken-unit matching for numbers.** Numeric tier1 entries now record both the value and the unit
  as spoken (monthly / annual / one-time / MRR / ARR). Swapping them is the one on-screen error that
  costs the whole video its credibility.
- Layout spec for the split-screen case: left carries the argument, right carries the proof, at most
  two vertical bands, subtitle band unavailable when the source already has captions.

### Changed
- Write path: inside a `talking-head-editing-workflow` project, output goes to `01_识别分析/关键词/`
  rather than creating `edit/`. That project layout has seven fixed entries and validates against
  them, so an extra directory fails the check.


## 0.1.0

Initial public release.

- 三级关键词体系：tier1 独立跳出大字 / tier2 字幕内强调 / tier3 外部素材插入
- 机械召回 + 语义复核两段式识别，规则命中只作候选，不直接定级
- 字幕可读性方案：字号、安全区、描边阴影建议，含 `legibility_risk` 标记
- 素材需求清单：区分 `local_required` / `library_match` / `ai_generatable`
- 方案包结构校验器，强制人工确认闸门，拒绝混入 EDL 执行字段
- 零外部依赖：纯 Python 标准库，不需要 ffmpeg，不联网，不读任何密钥
- 跨平台：macOS / Linux 用 `install.sh`，Windows 用 `install.ps1`
- 双 agent：自动探测 Claude Code 与 Codex CLI，两者都装则都安装
- 测试套件 80 项检查，CI 覆盖三平台 × 双 Python 版本
