# 识别方案交接协议

本文件定义本技能交给下游整体剪辑流程的只读方案包。下游流程必须先读取并让用户确认，再调用动态资产库、静态字幕资产库或 FFmpeg。

交付给用户时，不能只提供这些文件的路径。对话框中必须先用表格呈现视频信息、口播结构、一级关键词、二级关键词、三级素材需求、字幕可读性和待确认事项；文件链接仅作为附件。

## 交付原则

- `keywords_timeline.json` 是关键词判断和视觉意图，不是花字视频或 ASS 文件。
- `material_inserts.json` 是外部素材需求，不代表素材已存在。
- `subtitle_plan.json` 是可读性和字幕样式建议，不是已烧录字幕。
- `edit_plan.json` 是剪辑决策草案，不是 EDL；不得直接把它当作执行授权。
- 所有 `confidence` 为 `low` 或 `needs_human_review` 的条目必须在下游执行前再次确认。

## `keywords_timeline.json`

```json
{
  "video_id": "xxx",
  "keywords": [
    {
      "start": 3.6,
      "end": 7.0,
      "text": "半夜来询盘",
      "tag": "HOOK",
      "visual_tier": "tier1_standalone_dynamic",
      "screen_position": "upper_left",
      "suggested_duration": 2.4,
      "suggested_treatment": "大字卡片+轻微弹入",
      "reason": "开头痛点记忆点",
      "confidence": "high",
      "human_review": true
    }
  ]
}
```

## `material_inserts.json`

```json
{
  "video_id": "xxx",
  "inserts": [
    {
      "start": 20.0,
      "end": 24.0,
      "spoken_text": "把一封询盘丢进去",
      "insert_type": "screen_recording",
      "material_source": "local_required",
      "asset_status": "missing",
      "required_file_types": ["mp4", "mov"],
      "required_aspect": "9:16 或可裁切录屏",
      "suggested_duration": 4.0,
      "content_requirements": "真实工具操作：打开页面、粘贴询盘、提交",
      "library_query": "外贸询盘AI工具真实操作录屏",
      "ai_generation_allowed": false,
      "human_review": true
    }
  ]
}
```

真实产品、软件或品牌界面只能由用户上传或经用户指定的资产库提供，使用 `local_required` 或已确认的 `library_match`。没有文件时，状态写 `missing`，不能填假路径，也不能用生成图替代。

## `subtitle_plan.json`

每条字幕方案至少写：`start`、`end`、`text`、`screen_position`、`font_size_px`、`max_lines`、`safe_zone`、`emphasis_spans`、`background_treatment`、`legibility_risk`。1080×1920 竖屏默认普通字幕 64–76px、重点词 84–112px；若低于这个范围，必须有明确理由并标为需要人工确认。

## `edit_plan.json`

建议字段：

```json
{
  "video_id": "xxx",
  "source_video": "/abs/path/source.mp4",
  "analysis_status": "awaiting_human_confirmation",
  "keep_ranges": [],
  "suggested_cuts": [],
  "keyword_plan": "keywords_timeline.json",
  "subtitle_plan": "subtitle_plan.json",
  "material_plan": "material_inserts.json",
  "risks": [],
  "required_confirmation": [
    "接受文字稿校正",
    "接受关键词分级",
    "接受字幕字号和位置",
    "确认缺失素材上传清单"
  ],
  "downstream_next_step": "用户确认后再调用整体剪辑流程"
}
```

不得在这个文件中写入 `ranges`、`overlays`、`subtitles`、`preview` 或 `final` 路径；这些属于下游执行阶段。
