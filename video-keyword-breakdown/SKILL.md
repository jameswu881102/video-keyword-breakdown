---
name: video-keyword-breakdown
description: >
  口播视频关键词识别与剪辑方案生成：消费上游提供的带时间戳 SRT、transcript.json 或逐字稿，识别并分级重点关键词，分析口播结构、字幕强调、动态花字意图、画面插入位和素材需求，输出一份等待人工确认的剪辑方案。当用户提出识别口播重点、捕捉关键词、拆解字幕重点、生成口播剪辑方案或列出录屏/截图/插图/动态效果需求时使用；本节点只做文本分析和方案交接，不读取媒体、不转写、不下载、不联网。
---

# 口播视频关键词识别与剪辑方案

本技能只完成“文字稿读取 → 结构分析 → 关键词分级 → 剪辑意图 → 素材需求 → 人工确认方案”。它是后续整体剪辑流程的上游分析模块，不是媒体解析器、转写器或渲染器，也不连接外部服务。

## 工作边界

本技能负责：

- 读取用户或上游流程提供的带时间戳文字稿；
- 分析口播结构、节奏、痛点、卖点、演示段和 CTA；
- 召回并语义复核关键词，分为 tier1 / tier2 / tier3；
- 给出每个关键词的字幕、动态花字、画面位置、时长和动效意图；
- 列出后续需要用户提供或后续资产流程检索的文件，并说明文件用途、时间段和规格；
- 输出等待人工确认的方案包，交给后续总控剪辑流程消费。

本技能不负责：

- 不读取、解码、探测或抽帧 MP4/MOV 等媒体；
- 不从音频转写，不做 OCR，不安装或调用 FunASR、RapidOCR、FFmpeg、ffprobe 等媒体工具；
- 不下载视频、不读取平台 Cookie、不访问平台字幕接口、不调用 API；
- 不调用任何下游剪辑、资产、生成或发布能力；
- 不剪切、拼接、调色、混音或渲染 `preview.mp4` / `final.mp4`；
- 不生成 ASS 字幕、透明花字视频、动态图片、插图、录屏或产品界面；
- 不在人工确认前创建 EDL 或进入成片执行阶段。

本技能没有外部 skill、第三方 Python 包、系统媒体二进制、网络服务或密钥依赖。随附脚本只使用 Python 标准库。

## 输入契约

运行前必须具备以下至少一种带时间戳文字稿：

1. `transcript.json`：包含 `segments` 数组，每项至少有 `start`、`end`、`text`；
2. SRT 文件：通过随附的 `srt_to_transcript_json.py` 转换；
3. 上游流程生成的规范文字稿：直接复制或链接到其 `transcript.json`。

可选输入是用户已经提供的截图、关键帧、接触表或画面观察文字。没有画面证据时，只能把画面部分写成“建议/待确认”，不能声称已经观察到视频画面。

如果用户只给 MP4/MOV，没有文字稿：停止在输入检查，明确要求用户上传 SRT、逐字稿或由上游总控流程先建立规范文字稿；不得自行安装依赖、调用媒体解析器或猜测台词时间。

可写入路径：默认 `<文字稿所在目录>/edit/`，或用户明确指定的输出目录。输入文字稿、原始媒体、资产库和安装目录只读。遇到范围外问题记录并报告；需要删除或覆盖用户文件时先询问。

## 输出清单与人工闸门

开始时建立并持续勾选：

- [ ] 输入文字稿格式、来源、语言和时间粒度已确认；
- [ ] 已区分台词证据与用户提供的画面证据；
- [ ] 完成口播结构分析和机械候选召回；
- [ ] 完成语义复核、关键词分级和动效意图；
- [ ] 完成素材上传/调用需求清单；
- [ ] 生成方案包并通过结构校验；
- [ ] 已把方案、风险和待上传文件交给用户人工确认；
- [ ] 停止，不进入素材调用、剪辑或渲染。

默认输出：

- `<视频ID>_文字稿.md`：连续文字稿；
- `<视频ID>_结构化文字稿.md`：按口播段落和重点词整理；
- `<视频ID>_分析报告.md`：结构、节奏、文字证据和剪辑建议；
- `transcript.json`：带时间戳文字稿；
- `keyword_candidates.json`：机械召回结果，只能作为复核输入；
- `keywords_timeline.json`：tier1/tier2 的重点词和视觉处理意图，不是渲染文件；
- `material_inserts.json`：tier3 外部素材需求，不是已准备好的素材；
- `subtitle_plan.json`：字幕层级、字号建议、位置、安全区和强调方式；
- `edit_plan.json`：整体剪辑方案和待确认事项，不是 EDL；
- `material_requests.md`：需要用户上传或后续从资产库调用的文件清单；
- `human_review.md`：人工确认单，列出必须确认的切点、字幕、动效和素材。

方案包通过验证后，必须把上述文件交给用户确认，并明确写出：

> 当前只完成文字稿识别和方案，不会读取或生成视频。请确认方案，并上传/指定清单中的素材；确认后再进入整体剪辑执行流程。

## 对话框呈现规则

交付方案时，先在当前对话框直接呈现完整摘要表，文件链接只能作为交接附件，不能替代表格。至少呈现：

1. 文字稿基本信息表；
2. 口播结构时间线表；
3. 第一级关键词明细表；
4. 第二级关键词明细表；
5. 第三级外部素材需求表；
6. 字幕字号、位置、可读性风险表；
7. 待人工确认事项表。

每条关键词必须显示编号、层级、时间、原文、标签、建议位置、建议处理、置信度和确认状态。第三级虽然单独写入 `material_inserts.json`，也必须在对话框的第三级表格中逐条列出。不得只回复主要文件列表或要求用户逐个打开 JSON/Markdown。

## 阶段 1：准备文字稿

- 检查输入是否为 SRT 或合法 `transcript.json`；
- SRT 统一转换为 `transcript.json`：

```bash
python3 "$PACKAGE_DIR/scripts/srt_to_transcript_json.py" \
  "/abs/path/source.srt" "/abs/path/edit/transcript.json" --source provided
```

- 记录文字稿来源、语言、时间粒度和识别置信风险；
- 不把没有提供的画面、表情、镜头或字幕写成事实。

## 阶段 2：文案分析和关键词分级

开始语义复核前读取：

- `references/analysis-frameworks.md`：文案结构、节奏和 Viral-5D 分析；
- `references/keyword-taxonomy.md`：tier、标签和 JSON 字段定义。

先运行机械召回：

```bash
python3 "$PACKAGE_DIR/scripts/keyword_candidates.py" \
  "/abs/path/edit/transcript.json" \
  "/abs/path/edit/keyword_candidates.json"
```

再结合完整上下文和用户提供的画面证据人工复核：

- `tier1_standalone_dynamic`：建议后续调用动态资产库生成独立大字、数字卡、标题卡或品牌强调；本技能只记录意图、时间和规格；
- `tier2_inline_emphasis`：建议后续调用静态字幕资产库或字幕模板，在原字幕内做颜色、粗细、字号或局部强调；本技能只记录样式方案；
- `tier3_external_insert`：需要额外录屏、截图、插图、视频或图表；本技能只提出素材需求和占位，不准备或叠加素材。

规则命中只是候选，不得直接当作最终关键词。每个最终条目至少写明：原文、开始/结束时间、标签、tier、选择理由、建议位置、建议时长、动效/字幕意图、是否需要外部文件、人工确认项。所有重点词必须能在文字稿中找到；找不到时标为“需人工复核”。

## 阶段 3：输出方案而非执行素材

### `subtitle_plan.json`

字幕方案必须优先保证可读性。对 1080×1920 竖屏，默认建议：

- 普通口播字幕：字号 64–76 px，单行尽量不超过 14 个汉字；
- 重点词：字号 84–112 px 或使用静态字幕资产库中的大字模板；
- 位置：避开底部平台 UI 区，默认基线距底部至少 260–360 px；
- 描边、阴影和背景条要写出建议值；
- 每条方案写 `legibility_risk`，如果背景复杂或字幕过长，标为 `high` 并要求人工确认。

### `material_inserts.json`

每个外部素材需求至少包含：

- 时间段和对应台词；
- `insert_type`：`screen_recording`、`screenshot`、`illustration`、`video`、`diagram_table` 等；
- `material_source`：`local_required`、`library_match` 或 `ai_generatable`；
- 需要上传的文件类型、画幅、建议时长和内容要求；
- 是否涉及真实品牌/软件界面；真实界面必须标记为用户上传或后续库内查找，不得建议伪造；
- 后续检索关键词或生成提示词（仅作为下游输入，不在此调用）。

执行 `scripts/write_material_requests.py` 生成可直接发给用户的 `material_requests.md`。这只是清单，不代表素材已经存在。

### `edit_plan.json` 和人工确认单

`edit_plan.json` 记录：文字稿来源、关键词时间轴、字幕方案、动态意图、素材插入位、风险和确认状态。它不包含 `ranges`、`overlays`、`subtitles` 渲染路径等 EDL 字段。

`human_review.md` 必须列出：

1. 是否接受文字稿校正；
2. 是否接受每个 tier1/tier2/tier3 判断；
3. 是否接受字幕字号、位置、颜色和安全区；
4. 是否接受建议删减和切点；
5. 用户需要上传哪些视频、截图、录屏、Logo、字体、静态字幕模板或动态效果参考；
6. 用户确认后停止并交付方案包；本技能不自动进入素材调用或渲染阶段。

没有用户确认，本技能不得继续任何生成或渲染动作。

## 阶段 4：校验和停止

使用不读取媒体的结构校验：

```bash
python3 "$PACKAGE_DIR/scripts/validate_analysis_outputs.py" \
  --transcript "/abs/path/edit/transcript.json" \
  --keywords "/abs/path/edit/keywords_timeline.json" \
  --materials "/abs/path/edit/material_inserts.json" \
  --subtitle-plan "/abs/path/edit/subtitle_plan.json" \
  --edit-plan "/abs/path/edit/edit_plan.json"
```

校验失败时保留日志并修正分析文件。校验通过也只能交付方案包，不得生成视频预览、ASS、透明花字、EDL 或最终视频。遇到缺失文字稿、时间码不完整或语义无法判断时，列入 `human_review.md`，不要猜测成已确认结论。

## 参考文件

- `references/keyword-taxonomy.md`：关键词三级体系、标签和字段；语义复核前读取；
- `references/analysis-frameworks.md`：文案结构、节奏和创意分析；报告前读取；
- `references/analysis-handoff.md`：方案包的交接协议；写完输出前读取。
