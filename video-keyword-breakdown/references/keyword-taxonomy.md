# 关键词标签体系（Keyword Taxonomy）

这是阶段 4「关键词自动识别与标注」的核心判断标准。`keyword_candidates.py`
只负责用正则和位置规则做**机械召回**；下面的判断标准，是给 Claude 做
**语义复核**时用的——决定一个候选到底该不该保留、该怎么分级、该打哪个
语义标签、该建议什么剪辑处理。

每个关键词要回答两个独立的问题：

1. **它有多重要、该用什么强度的画面处理？**（`visual_tier`，三级体系，本文件的核心）
2. **它在文案里承担什么功能？**（`tag`，8 个语义标签，用来解释"为什么重要"）

这两个维度是正交的：同一个 `tag`（比如 BRAND_KEYWORD）在不同视频里可能是
第一级也可能是第二级，取决于它在这条视频里到底有多关键。**不要把 tag 和
tier 划等号**——tag 说的是"这段话是什么类型的内容"，tier 说的是"这段话
在画面上应该被多用力地强调"。

## 一、三级视觉处理体系（visual_tier）—— 决定"怎么呈现"

这是关键词标注真正要交给剪辑用的核心产出。三级按提出顺序编号，不是按
"重要性从低到高"排的——判断标准各自独立，不要把编号误读成分数。

### 第一级 `tier1_standalone_dynamic`——独立动态强调

关键词从字幕里"跳出来"，变成一个**独立于字幕行之外**的动态图形元素：
放大、动画入场、可能占据屏幕的专属位置（屏幕正中大字冲入、右上角信息卡、
左侧标题条等）。这是最重的处理，一条视频里数量要克制（通常个位数），
用在全片记忆点上：开场钩子、核心论点句、首次出现的重磅品牌词、和开场
形成呼应的结尾句。

判断标准：**这句话如果只做字幕里的加粗变色，会不会太亏？** 如果这句话
本身就是观众会截图/复述的那句"金句"，选第一级。

需要的字段：
- `screen_position`：建议出现的位置——`screen_center`（正中大字）/
  `top_left_bar`（左上角标题条，参考本片开场的"开场 / 认知反差"式小标签）/
  `top_right_card`（右上角信息卡）/ `full_takeover`（短暂占满全屏）
- `suggested_treatment`：`title_card` / `kinetic_type` / `counter_card`（大字数字）

### 第二级 `tier2_inline_emphasis`——字幕内嵌强调

不脱离原有字幕框架，只在字幕行内做**颜色 + 字号/加粗**的增强。这是最
轻量、密度可以最高的处理，覆盖"值得注意但不到独立跳出程度"的关键词——
普通的数据点、次要的品牌提及、CTA 里的动作词等。

判断标准：**这句话需要被看到，但没有重到需要打断字幕的连续性。**

### 第三级 `tier3_external_insert`——外部素材插入

这一级和前两级性质完全不同：**它不是给文字加效果，而是标记"这个时间点
画面需要额外的视觉素材"**。台词里提到了一个外部的东西——工具/插件、
参考视频、截图、录屏、图表——但当前画面里没有把它实际展示出来（或者
需要单独准备一份更清晰的素材），这类关键词标注出来是为了给口播剪辑
"增加画面丰富度"：插入录屏、插图、表格，甚至蒙版叠加。

判断标准：**台词提到的这个东西，观众现在其实"看不到"或者应该被更清楚
地看到——需要额外找一段素材塞进画面里吗？** 素材可以是静态的（插图/截图/
图表），也可以是动态的（录屏/视频）——不要预设只有图片，凡是"这里需要一段
额外的视觉内容"都算。

### 三种典型场景，分别对应不同的素材来源判断

这三种场景决定了 `insert_type` 和 `material_source` 该怎么组合，不要混淆：

1. **提到具体品牌/工具名 → 品牌 logo 动态弹出**（`insert_type: brand_logo`）。
   例如口播说到"Codex"，画面应该弹出 Codex 的 logo。**这类素材默认
   `material_source: local_required`**——真实品牌的 logo 是确定的图形
   （颜色、字体、比例都固定），AI 生成模型画不准一个真实存在的商标，生成
   出来的"山寨 logo"反而会显得不专业甚至引起误会。只有当明确是要一个
   *原创的、不冒充任何真实品牌*的风格化图形标识时，才能标 `ai_generatable`。
2. **提到具体的录屏/演示画面 → 插入真实录屏**（`insert_type: screen_recording`
   或 `screenshot`）。例如口播说"你看它在剪辑的时候会怎么样"，这是在描述
   一个具体软件的真实操作过程，**默认 `material_source: local_required`**——
   真实软件界面同样是 AI 编不出来的，编出来的假界面会显得不真实。
3. **描述一个通用场景/概念，不涉及具体真实产品 → 交给下游先查素材库，库里没有再
   AI 生成**（`insert_type: illustration` / `diagram_table` / `mask_overlay`）。
   例如口播说"就像在一个杂乱的工作环境里找东西"这种泛化场景描述，没有指向
   任何具体真实产品或画面——**这类候选不要想都不想就直接去写生成提示词**。
   如果用户配置了动态字幕库/插图库，这类素材很可能已经有现成的可以复用，
   但本识别 skill 不访问资产库，只记录后续检索需求：
   - 从这句台词提炼检索关键词，写进 `library_query`；下游资产流程再检索，
     并由人工核对候选是否真的贴合台词内容
   - **库里能找到内容贴切的素材** → `material_source: library_match`，
     把匹配到的文件路径写进 `matched_asset_path`，不需要再生成，
     `generation_prompt` 留空
   - **下游确认库里没有贴切素材** → 退回
     `material_source: ai_generatable`，这时候才写 `generation_prompt`，
     可以生成静态插图，也可以生成一段动态视频——由内容本身的动态需求决定，
     见下面 `generation_media_type` 字段

一句话判断：**能对应到一个具体、真实、可识别的东西（品牌/软件/录屏）就是
`local_required`；是在描述一个不指向任何具体真实事物的通用场景/概念，就
先查素材库——库里有贴切的就是 `library_match`，库里没有才轮到
`ai_generatable`。本识别阶段不假装已经查库。拿不准素材来源时默认 `local_required`，宁可麻烦用户
确认，也不要让一个假冒的品牌/界面出现在成片里；拿不准库里的素材是否真的
贴切时默认当作"库里没有"，直接进 `ai_generatable`，不要为了省一次生成而
硬凑一个不太对的旧素材。

需要的字段：
- `insert_type`：`brand_logo`（品牌/产品 logo）/ `screen_recording`（录屏）/
  `screenshot`（截图）/ `illustration`（插图）/ `diagram_table`（图表/表格）/
  `mask_overlay`（蒙版叠加）/ `other`
- `material_source`：`local_required`（需要用户提供真实素材）/
  `library_match`（在用户的素材库里找到了贴切的现成素材）/
  `ai_generatable`（库里没有，需要现生成），判断标准见上面三种场景
- `library_query`：**场景 3（通用场景/概念）的候选都要填**，即使最终结果是
  `ai_generatable` 也要保留——写下用来检索素材库的关键词（例如"办公室
  效率 忙碌 电脑"），这样即便这次判定为库里没有，也留了记录，方便以后库
  更新了回头补充，也方便用户自己去库里再确认一遍
- `matched_asset_path`：**仅当 `material_source` 为 `library_match` 时必填**，
  匹配到的库内素材的绝对路径（或库内相对路径），供剪辑环节直接取用
- `generation_media_type`：**仅当 `material_source` 为 `ai_generatable` 时必填**。
  `image`（静态插图/图表）或 `video`（动态短片）——由内容需不需要动态表现
  决定，不要默认都是图片。比如"生成素材的过程"这种带动作感的描述，视频比
  静态插图更贴切。
- `generation_prompt`：**仅当 `material_source` 为 `ai_generatable` 时必填**。
  写一段可以直接喂给图像/视频生成大模型的详细提示词，具体怎么写、`image`
  和 `video` 各自要注意什么，见「三、生成提示词怎么写」——**核心要求只有
  一条：提示词描述的画面必须能对应到台词这一句实际在说什么，不能是一段
  和内容无关、随便找的插图/视频**。
  `material_source` 为 `local_required` 或 `library_match` 时
  `generation_media_type`/`generation_prompt` 都留空；`local_required` 要在
  `reason` 里说明具体需要用户提供什么（是哪个品牌的 logo、哪个软件的录屏等）。

**BRAND_KEYWORD 常常同时需要 tier1（或 tier2）+ tier3 两条记录**：品牌名
本身在字幕里的强调是 tier1/tier2 的事（比如把"Codex"这个词做成跳出的大字），
但"把 Codex 真实的 logo 图形放进画面里"是另一条独立的 tier3 记录
（`insert_type: brand_logo`），两者用同一个 `start`/`end` 时间窗口，分别
写成 `keywords_timeline.json` 和 `material_inserts.json` 里的两条——这正是
用户举的例子："谈到 Codex，就要弹出一个 Codex 的 logo 出来"，字面强调和
logo 素材是配套的两件事，不要只做其中一件。

## 二、语义标签体系（tag）—— 决定"为什么重要"

| 标签 | 中文名 | 判断标准 | 常见对应 tier |
|------|--------|----------|----------------|
| `HOOK` | 钩子 | 开场 8% 时间区内、或痛点/反常识/悬念句式，能在 3 秒内让人想继续看 | 通常 tier1 |
| `EMOTION_PEAK` | 情绪爆点 | 强语气标点、情绪词、语调明显上扬处 | tier1 或 tier2，视强度而定 |
| `CTA` | 行动号召 | 明确要求观众做某个动作（点赞/关注/购买/扫码） | 通常 tier2，全片唯一/最强的 CTA 可升 tier1 |
| `SOCIAL_CURRENCY` | 社交货币 | 值得转发/讨论/@朋友的传播型表达 | tier2 |
| `NUMBER_STAT` | 数据金句 | 具体数字、百分比、排名、"第一/最高级"表达 | tier2，全片最关键的数字可升 tier1 |
| `BRAND_KEYWORD` | 品牌/专名 | 引号/书名号内的专有名词、产品名、人名 | tier1/tier2（文字强调）+ 常配一条 tier3（界面素材） |
| `RHETORIC` | 修辞亮点 | 排比、重复、对偶等修辞结构 | tier1（核心论点句）或 tier2（普通排比） |
| `TRANSITION` | 转场/卡点 | 静音间隔 ≥ 阈值（默认 1.2s），是天然的镜头切换点 | 不适用 tier 体系，写入 edit_plan.json 的 suggested_cuts |

## 三、生成提示词怎么写（tier3 + ai_generatable 专用）

`generation_prompt` 是要直接喂给图像/视频生成大模型执行的，写得越具体，
生成结果越可控。建议按这个顺序组织一句话到几句话的提示词：

1. **主体内容**：画面里必须出现什么（例如"一个简洁的软件界面，顶部是
   工具 logo，中间是时间线轨道"）
2. **风格**：写实截图风 / 扁平插画风 / 等距 3D 插画 / 极简线框图 / UI
   mockup 风格等，尽量指定一种
3. **色彩基调**：跟随视频原本的视觉风格（如果能观察到，比如本片是深色
   背景+黄绿高亮，就在提示词里带上）
4. **关键细节**：字号、图标数量、是否要有具体文字标签（文字标签建议
   用视频的实际语言，如中文）
5. **画幅**：与视频保持一致的宽高比（如 16:9 或 9:16）

**示例**（针对"这个插件负责呈现可视化的时间线"这类台词）：

```
"极简科技风格的视频剪辑软件界面截图，深色背景，顶部有绿色高亮的工具
名称标签，中间是一条彩色分段的时间线轨道（蓝色、粉色、绿色色块代表
不同素材类型），右侧有一个小的预览窗口显示人物口播画面，整体风格
参考现代视频剪辑软件UI，简洁不杂乱，16:9横版画幅"
```

## 四、复核关键词候选时要问的问题

1. **这条该分几级？** 先定 tier，再定 tag——不要反过来。同一句话，
   在信息密度很高的视频里可能只值 tier2，在克制的视频里可能值 tier1。
2. **规则命中是否真的成立？** 例如 `EMOTION_RE` 命中了感叹号，但这句
   可能只是陈述句加了语气词，并没有真实的情绪爆发——读一遍上下文再决定。
3. **候选之间是否重复？** 同一句话可能同时命中 HOOK（区位）和 EMOTION_PEAK
   （用词），此时看哪个标签更贴切文案功能，通常只保留主标签，次标签写进
   `reason` 里作为补充说明。
4. **规则漏掉的语义型候选要不要补？** 比喻、反转、埋伏笔这类没有固定
   句式的修辞，规则抓不到；提到工具/插件/参考视频但没被规则捕捉到的
   tier3 候选也需要手动补，需要 Claude 通读全文（和看画面，如果有视觉
   证据的话）后手动补充。
5. **时间戳是否落在词边界上？** 本流程的硬规则是：绝不能把一个词
   从中间切断。如果关键词片段的 `text` 是从整句里截出来的短语，起止时间
   要能在字幕/ASR 时间戳里找到对应的词边界，找不到就退回整句时间戳，
   不要臆造时间点。
6. **tier3 的素材来源判断准确吗？** 不要把"AI生成不了/生成出来会失真的
   真实素材"（比如具体软件的真实界面、用户自己的产品实拍）标成
   `ai_generatable`——那样会误导剪辑环节，最后拿到一张不能用的假素材。
   拿不准就标 `local_required`，让人来判断。
7. **场景 3 的候选是否留下了检索需求？** 通用场景/概念类的 tier3 候选，
   本识别阶段必须填写 `library_query`，但不得调用资产库、填写未经确认的
   `matched_asset_path` 或直接生成素材；下游查库并经人工核对后，再决定是
   `library_match` 还是 `ai_generatable`。

## 五、keywords_timeline.json 最终 schema

复核完成后，把最终结果写成这个结构，供下游字幕资产流程读取：

```json
{
  "video_id": "xxx",
  "keywords": [
    {
      "start": 3.6,
      "end": 7.0,
      "text": "90%的人都不知道",
      "tag": "NUMBER_STAT",
      "visual_tier": "tier2_inline_emphasis",
      "reason": "用反常识数据制造悬念，是本段的记忆点，但不是全片最核心的论点，字幕内强调即可",
      "suggested_treatment": "counter_card"
    },
    {
      "start": 20.0,
      "end": 22.0,
      "text": "codex",
      "tag": "BRAND_KEYWORD",
      "visual_tier": "tier1_standalone_dynamic",
      "screen_position": "top_left_bar",
      "reason": "核心工具首次出现，值得单独强调",
      "suggested_treatment": "logo_badge"
    }
  ]
}
```

字段说明：
- `start` / `end`：秒，来自 ASR/字幕时间戳（不要自己估算）
- `text`：关键词/短语原文，必须能在对应字幕行中找到，供 validate_analysis_outputs.py 做一致性校验并交给下游字幕流程
- `tag`：第二节里的 8 个语义标签之一
- `visual_tier`：`tier1_standalone_dynamic` / `tier2_inline_emphasis` /
  `tier3_external_insert` 之一。**`tier3` 的条目不要写进 `keywords_timeline.json`
  ——它属于 `material_inserts.json`**（见下），因为它不是文字处理，是素材处理。
- `screen_position`：仅 tier1 使用，见第一节
- `reason`：一句话说明为什么这样分级、打这个标签，供人工复核
- `suggested_treatment`（可选）：给剪辑阶段的处理建议，如 `counter_card`
  / `title_card` / `arrow_cta` / `logo_badge` / `kinetic_type` / `cut_point`

## 六、material_inserts.json schema（tier3 专用，新文件）

tier3 的产出**不写进** `keywords_timeline.json`，因为它描述的不是"给文字
加效果"，而是"这里需要一段额外素材"，性质不同，单独存一份：

```json
{
  "video_id": "xxx",
  "inserts": [
    {
      "start": 20.0,
      "end": 22.0,
      "spoken_text": "这类视频我们主要用codex",
      "insert_type": "brand_logo",
      "material_source": "local_required",
      "reason": "台词提到具体工具 codex，需要它真实的 logo 图形，AI 画不准真实商标",
      "library_query": null,
      "matched_asset_path": null,
      "generation_media_type": null,
      "generation_prompt": null
    },
    {
      "start": 58.0,
      "end": 60.0,
      "spoken_text": "就像在一个杂乱的工作环境里找东西",
      "insert_type": "illustration",
      "material_source": "library_match",
      "reason": "通用办公场景描述，不涉及具体真实产品；在用户的插图库里检索到一张贴切的现成插图，直接复用，不需要再生成",
      "library_query": "办公室 效率 忙碌 杂乱 找东西",
      "matched_asset_path": "/Users/xxx/素材库/插图库/office_chaos_search_01.png",
      "generation_media_type": null,
      "generation_prompt": null
    },
    {
      "start": 92.0,
      "end": 94.0,
      "spoken_text": "这个插件负责呈现可视化的时间线",
      "insert_type": "illustration",
      "material_source": "ai_generatable",
      "reason": "描述的是抽象概念（可视化时间线），查了插图库没有贴切的现成素材，用生成插图传达",
      "library_query": "可视化时间线 剪辑软件 时间轴",
      "matched_asset_path": null,
      "generation_media_type": "image",
      "generation_prompt": "极简科技风格的视频剪辑软件界面截图，深色背景，顶部有绿色高亮的工具名称标签，中间是一条彩色分段的时间线轨道（蓝色、粉色、绿色色块代表不同素材类型），整体风格参考现代视频剪辑软件UI，简洁不杂乱，16:9横版画幅"
    }
  ]
}
```

字段说明（除上面第一节列过的以外）：
- `library_query`：非场景 3 的候选（品牌 logo、真实录屏这类 `local_required`）
  留 `null` 即可，不需要查库——查库只针对"通用场景/概念"这一类
- `matched_asset_path`：只有 `library_match` 才填，其余情况留 `null`

## 七、每类标签/分级的时长与落点建议

- **tier1**：3-5 秒的强调窗口，不要拖长；核心论点句可以到 8-10 秒但要配合
  语速。按照本流程的动画落点规则：动画提前
  `reveal_duration` 秒开始，让最终画面正好卡在关键词被念出的那一刻。
- **tier2**：跟随字幕行本身的时长，不需要额外停留。
- **tier3**：跟随台词提到该素材的时长；如果是需要"消化"的图表/插图，
  可以比台词时长多留 0.5-1s 让观众看清。
- **TRANSITION**：不是视觉元素，是剪辑决策点，直接进 `edit_plan.json` 的
  `suggested_cuts`，不需要独立动画时长。

识别方案交给下游的字段和人工确认闸门见 `analysis-handoff.md`。
