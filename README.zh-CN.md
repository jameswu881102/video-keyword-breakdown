# video-keyword-breakdown

[English](README.md) · 简体中文

**口播视频关键词识别与剪辑方案生成器。** 给它一个口播视频，它输出一份带精确时间戳的关键词时间轴、字幕方案和素材需求清单——然后停下来等你确认。

它不剪视频。这是刻意的：分析和执行分开，你才能在动刀之前看清它打算怎么处理你的片子。

**适用范围**

- **Agent** —— Claude Code、Codex CLI，以及任何使用 SKILL.md 格式的 agent。安装脚本自动探测你装了哪个，两个都装了就都装。
- **系统** —— macOS、Linux、Windows。macOS/Linux 用 `install.sh`，Windows 用 `install.ps1`，CI 三个平台全覆盖。
- **依赖** —— 只需要 Python 3.9+。**不需要 ffmpeg，不联网，不读任何密钥。**

---

## 它解决什么问题

剪口播视频最耗时的不是剪辑本身，是**判断哪些词该强调、怎么强调、哪里该插素材**。这件事通常靠人一句句听、一帧帧看，做完一条十分钟的片子要花两小时。

这个技能把这段判断结构化了：

| 你要决定的事 | 它给你的 |
|---|---|
| 哪个词该做大字弹出 | tier1 清单，含时间、原文、时长、动效意图 |
| 哪个词该在字幕里加粗变色 | tier2 清单，含样式方案 |
| 哪里需要插录屏/截图/图表 | tier3 清单，含素材类型、规格、检索词或 AI 生成提示词 |
| 字幕多大、放哪、会不会看不清 | 字号/安全区/描边建议，附 `legibility_risk` 标记 |
| 哪些段落可以删 | 结构时间线，标出 Hook / 痛点 / 演示 / CTA |

---

## 三级关键词体系

这是整个工具的核心。关键词不是"重要/不重要"的二分，而是按**呈现方式**分三级：

**第一级 `tier1_standalone_dynamic`** —— 独立跳出的动态大字。数字、结论、品牌名这类需要脱离字幕单独强调的内容。工具只记录意图、时间和规格，不生成动画。

**第二级 `tier2_inline_emphasis`** —— 字幕内的颜色/加粗/字号强调。不脱离字幕流，但需要视觉上跳出来。

**第三级 `tier3_external_insert`** —— 需要额外素材的位置。工具会区分素材来源：`local_required`（你得自己上传）、`library_match`（去你的素材库找）、`ai_generatable`（可以生成，附提示词）。

完整的标签定义、JSON schema 和判断标准见 [`references/keyword-taxonomy.md`](video-keyword-breakdown/references/keyword-taxonomy.md)。

---

## 文字稿从哪来

**这个工具自己不做语音识别，也不下载视频。** 它消费的是已有的文字稿：

1. 你提供的 SRT / 逐字稿 / 剪映字幕
2. 视频内嵌字幕（由你的 agent 或其他工具取出）
3. 烧录字幕（由你的 agent 读画面取出）

拿到 SRT 后用 `srt_to_transcript_json.py` 统一成 `transcript.json`，后续所有分析都基于它。

> 这是刻意的设计。上一版内置过语音识别、平台字幕接口和视频下载，为此引入了云端 API、浏览器 Cookie 读取和平台依赖。现在全部移除——**工具只做它最擅长的那件事：把文字稿变成剪辑方案。**

---

## 安装

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

两个脚本行为一致，都会自动探测本机装了哪些 agent：

| Agent | skills 目录 | 规约文件 |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `~/.claude/CLAUDE.md` |
| Codex CLI | `~/.codex/skills/` | `~/.codex/AGENTS.md` |

两个都装了就都装一份；一个都没探测到会提示你指定。重复运行不会重复追加规约。

装到别处：

```bash
# macOS / Linux
SKILL_DIR=/your/skills/dir AGENTS_MD=/your/AGENTS.md bash install.sh
```

```powershell
# Windows
$env:SKILL_DIR="C:\your\skills"; $env:AGENTS_MD="C:\your\AGENTS.md"; .\install.ps1
```

**手动安装** —— 把 `video-keyword-breakdown/` 目录复制进你 agent 的 skills 目录即可。无需构建，无需装任何包。

---

## 用法

装好后，直接在对话里说：

> 拆解一下这个口播视频，字幕在 /path/to/video.srt

或者「给这段文案的关键词分级」「这段口播该插什么素材」。

### 输出

方案包写到 `<视频所在目录>/edit/`：

| 文件 | 内容 |
|---|---|
| `transcript.json` | 带时间戳文字稿 |
| `keyword_candidates.json` | 机械召回结果（**只是候选，不是结论**） |
| `keywords_timeline.json` | tier1/tier2 关键词与视觉处理意图 |
| `material_inserts.json` | tier3 外部素材需求 |
| `subtitle_plan.json` | 字幕层级、字号、位置、安全区 |
| `edit_plan.json` | 整体方案与待确认事项（**不是 EDL**） |
| `material_requests.md` | 可直接发给你的素材上传清单 |
| `human_review.md` | 人工确认单 |

### 脚本

| 脚本 | 用途 |
|---|---|
| `srt_to_transcript_json.py` | SRT → 统一 transcript.json |
| `keyword_candidates.py` | 机械召回关键词候选 |
| `write_material_requests.py` | 生成素材清单 Markdown |
| `validate_analysis_outputs.py` | 方案包结构校验 |

---

## 工作边界

这个技能**只做分析和交接**：

- ✅ 分析口播结构、关键词分级、素材需求、字幕方案，输出待确认方案包
- ❌ 不剪切/拼接/调色/混音/渲染，不生成 ASS 字幕或花字视频
- ❌ **不下载视频、不读取平台 Cookie、不访问平台字幕接口、不调用任何 API**
- ❌ 不调用资产库，不替你选或下载素材，不伪造真实软件界面
- ❌ 人工确认前不创建 EDL，不进入任何成片阶段

可写入路径限于 `<视频所在目录>/edit/` 或你指定的输出目录，原视频只读。

**下游交接** —— 方案确认后交给你自己的剪辑 skill。那个 skill 不随本仓库分发，路径需要你在本机指定。交接协议见 [`references/analysis-handoff.md`](video-keyword-breakdown/references/analysis-handoff.md)。

---

## 已知限制

**它读不出你没说的东西。** 分析基于文字稿，不是画面理解。画面里的信息如果台词没提，它看不到。

**机械召回只是候选。** 规则命中不等于该词重要，也不等于分级正确。最终定级必须由 agent 结合完整上下文复核——这一点在 `keyword_candidates.py` 的输出里会反复提醒。

**字幕建议值是针对 1080×1920 竖屏的。** 其他画幅需要自己换算。

---

## 开发

改动任何脚本后跑：

```bash
python3 tests/test_scripts.py
```

80 项检查，包含：脚本集合一致性、**零网络调用/零密钥/零个人路径的仓库卫生扫描**、Windows 编码回归、SRT 转换 schema、召回规则命中，以及方案包校验器的 1 个正例 + 10 个负例。

新增检查项时同步加 fixture 和断言——测试套件靠 fixture 驱动。

CI 覆盖 Ubuntu / macOS / Windows × Python 3.9 / 3.12，并在每个平台上实跑对应的安装脚本。

---

## License

MIT
