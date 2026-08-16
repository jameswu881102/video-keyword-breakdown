#!/usr/bin/env bash
# video-keyword-breakdown 安装脚本（macOS / Linux）
# Windows 请改用 install.ps1
#
# 用法：在仓库根目录执行
#     bash install.sh
#
# 自动探测本机装了哪些 agent（Claude Code / Codex CLI），装进对应的 skills 目录。
# 两个都有就都装。想装到别处，用环境变量覆盖：
#     SKILL_DIR=/your/skills/dir AGENTS_MD=/your/AGENTS.md bash install.sh
#
# 本技能纯 Python 标准库实现，不需要 ffmpeg，不联网，不读任何密钥。

set -uo pipefail

SKILL_NAME="video-keyword-breakdown"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m[OK]\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\n\033[31m[FAIL] %s\033[0m\n\n' "$*"; exit 1; }

PY=$(command -v python3 || command -v python) || die "找不到 python3，请先安装 Python 3.9 或更高版本"

PYVER=$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' \
  || die "需要 Python 3.9 或更高版本，当前 $PYVER"

# ---------- 0. 决定装到哪些目录 ----------
say "[0/3] 探测安装目标"
ok "Python $PYVER"

TARGETS=()   # 每项形如 "skills目录|规约文件"

if [ -n "${SKILL_DIR:-}" ]; then
  TARGETS+=("$SKILL_DIR|${AGENTS_MD:-$(dirname "$SKILL_DIR")/AGENTS.md}")
  ok "使用环境变量指定的目录：$SKILL_DIR"
else
  [ -d "$HOME/.claude" ] && { TARGETS+=("$HOME/.claude/skills|$HOME/.claude/CLAUDE.md"); ok "探测到 Claude Code"; }
  [ -d "$HOME/.codex" ]  && { TARGETS+=("$HOME/.codex/skills|$HOME/.codex/AGENTS.md");  ok "探测到 Codex CLI"; }

  if [ ${#TARGETS[@]} -eq 0 ]; then
    warn "没探测到 Claude Code（~/.claude）或 Codex CLI（~/.codex）"
    echo "  请用环境变量指定安装位置，例如："
    echo "      SKILL_DIR=~/.claude/skills AGENTS_MD=~/.claude/CLAUDE.md bash install.sh"
    die "无法确定安装目录"
  fi
fi

# ---------- 1. 安装 ----------
say "[1/3] 安装技能"

SRC="$HERE/$SKILL_NAME"
[ -f "$SRC/SKILL.md" ] || die "找不到 $SKILL_NAME/SKILL.md，请在仓库根目录运行本脚本"
ok "找到技能目录"

INSTALLED=()
for entry in "${TARGETS[@]}"; do
  TARGET_DIR="${entry%%|*}"
  mkdir -p "$TARGET_DIR" || die "无法创建 $TARGET_DIR"
  DEST="$TARGET_DIR/$SKILL_NAME"
  [ -d "$DEST" ] && warn "检测到旧版本，将覆盖更新"
  rm -rf "$DEST"
  cp -r "$SRC" "$DEST" || die "复制到 $DEST 失败"
  ok "已安装到 $DEST"
  INSTALLED+=("$DEST")
done

# ---------- 2. 规约 ----------
say "[2/3] 写入使用规约"

MARK="## 口播视频拆解规约"
for entry in "${TARGETS[@]}"; do
  AGENTS_FILE="${entry##*|}"
  DEST="${entry%%|*}/$SKILL_NAME"
  mkdir -p "$(dirname "$AGENTS_FILE")"
  touch "$AGENTS_FILE"
  if grep -qF "$MARK" "$AGENTS_FILE" 2>/dev/null; then
    ok "规约已存在，跳过：$AGENTS_FILE"
  else
    cat >> "$AGENTS_FILE" <<EOF

$MARK

拆解口播视频、给关键词分级、或规划剪辑素材时，使用 $SKILL_NAME。

该技能只做分析和交接：输出方案包后必须停下等人工确认，
不得自行剪切、渲染或生成 EDL，也不下载视频、不访问任何平台接口。

判断 tier 前先读 $DEST/references/keyword-taxonomy.md，
不要把机械召回的候选直接当成最终分级结果。

交付前校验方案包结构：
    python3 $DEST/scripts/validate_analysis_outputs.py --help
EOF
    ok "已追加到 $AGENTS_FILE"
  fi
done

# ---------- 3. 验证 ----------
say "[3/3] 验证安装"

FIRST="${INSTALLED[0]}"
[ -f "$FIRST/SKILL.md" ] || die "SKILL.md 未就位"

n=0
for s in "$FIRST"/scripts/*.py; do
  "$PY" -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$s" \
    || die "语法检查失败：$(basename "$s")"
  n=$((n + 1))
done
ok "$n 个脚本语法检查通过"

"$PY" "$FIRST/scripts/validate_analysis_outputs.py" --help >/dev/null 2>&1 \
  && ok "校验器可运行" || die "校验器无法运行，请检查 Python 环境"

for r in keyword-taxonomy analysis-frameworks analysis-handoff; do
  [ -f "$FIRST/references/$r.md" ] || die "缺少 references/$r.md"
done
ok "3 个参考文件就位"

say "安装完成"
cat <<EOF

  对话里直接说：

    「拆解一下这个口播视频 /path/to/video.mp4」
    「给这个视频的关键词分级」
    「这段口播该插什么素材」

  技能只输出方案包到 <视频目录>/edit/，不会自动剪辑，
  也不会下载视频或访问任何外部接口。

EOF
