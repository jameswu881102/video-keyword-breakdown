<#
video-keyword-breakdown 安装脚本（Windows / PowerShell）
macOS 和 Linux 请改用 install.sh

用法：在仓库根目录执行
    powershell -ExecutionPolicy Bypass -File install.ps1

自动探测本机装了哪些 agent（Claude Code / Codex CLI），装进对应的 skills 目录。
两个都有就都装。想装到别处：
    $env:SKILL_DIR="C:\your\skills"; $env:AGENTS_MD="C:\your\AGENTS.md"; .\install.ps1

本技能纯 Python 标准库实现，不需要 ffmpeg，不联网，不读任何密钥。
#>

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$SkillName = 'video-keyword-breakdown'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Say  { param($m) Write-Host "`n$m" -ForegroundColor White }
function Ok   { param($m) Write-Host "  [OK] $m" -ForegroundColor Green }
function Warn { param($m) Write-Host "  [!] $m"  -ForegroundColor Yellow }
function Die  { param($m) Write-Host "`n[FAIL] $m`n" -ForegroundColor Red; exit 1 }

# ---------- Python ----------
$Py = $null
foreach ($c in @('python3', 'python', 'py')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) {
        $v = & $c -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) { $Py = $c; $PyVer = $v; break }
    }
}
if (-not $Py) { Die "找不到 Python。请从 https://www.python.org 安装 Python 3.9 或更高版本，并勾选 Add to PATH。" }

& $Py -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)"
if ($LASTEXITCODE -ne 0) { Die "需要 Python 3.9 或更高版本，当前 $PyVer" }

# ---------- 0. 探测目标 ----------
Say '[0/3] 探测安装目标'
Ok "Python $PyVer"

$Targets = @()   # 每项 @{ Skills = ...; Agents = ... }

if ($env:SKILL_DIR) {
    $agents = if ($env:AGENTS_MD) { $env:AGENTS_MD } else { Join-Path (Split-Path -Parent $env:SKILL_DIR) 'AGENTS.md' }
    $Targets += @{ Skills = $env:SKILL_DIR; Agents = $agents }
    Ok "使用环境变量指定的目录：$($env:SKILL_DIR)"
} else {
    $claude = Join-Path $HOME '.claude'
    $codex  = Join-Path $HOME '.codex'
    if (Test-Path $claude) {
        $Targets += @{ Skills = (Join-Path $claude 'skills'); Agents = (Join-Path $claude 'CLAUDE.md') }
        Ok '探测到 Claude Code'
    }
    if (Test-Path $codex) {
        $Targets += @{ Skills = (Join-Path $codex 'skills'); Agents = (Join-Path $codex 'AGENTS.md') }
        Ok '探测到 Codex CLI'
    }
    if ($Targets.Count -eq 0) {
        Warn '没探测到 Claude Code（~\.claude）或 Codex CLI（~\.codex）'
        Write-Host '  请用环境变量指定安装位置，例如：'
        Write-Host '      $env:SKILL_DIR="$HOME\.claude\skills"; $env:AGENTS_MD="$HOME\.claude\CLAUDE.md"; .\install.ps1'
        Die '无法确定安装目录'
    }
}

# ---------- 1. 安装 ----------
Say '[1/3] 安装技能'

$Src = Join-Path $Here $SkillName
if (-not (Test-Path (Join-Path $Src 'SKILL.md'))) {
    Die "找不到 $SkillName\SKILL.md，请在仓库根目录运行本脚本"
}
Ok '找到技能目录'

$Installed = @()
foreach ($t in $Targets) {
    New-Item -ItemType Directory -Force -Path $t.Skills | Out-Null
    $dest = Join-Path $t.Skills $SkillName
    if (Test-Path $dest) {
        Warn '检测到旧版本，将覆盖更新'
        Remove-Item -Recurse -Force $dest
    }
    Copy-Item -Recurse -Force $Src $dest
    Ok "已安装到 $dest"
    $Installed += $dest
}

# ---------- 2. 规约 ----------
Say '[2/3] 写入使用规约'

$Mark = '## 口播视频拆解规约'
foreach ($t in $Targets) {
    $agentsFile = $t.Agents
    $dest = Join-Path $t.Skills $SkillName
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $agentsFile) | Out-Null
    if (-not (Test-Path $agentsFile)) { New-Item -ItemType File -Path $agentsFile | Out-Null }

    $existing = Get-Content -Raw -Encoding UTF8 $agentsFile -ErrorAction SilentlyContinue
    if ($existing -and $existing.Contains($Mark)) {
        Ok "规约已存在，跳过：$agentsFile"
    } else {
        $validator = Join-Path (Join-Path $dest 'scripts') 'validate_analysis_outputs.py'
        $taxonomy  = Join-Path (Join-Path $dest 'references') 'keyword-taxonomy.md'
        $block = @"

$Mark

拆解口播视频、给关键词分级、或规划剪辑素材时，使用 $SkillName。

该技能只做分析和交接：输出方案包后必须停下等人工确认，
不得自行剪切、渲染或生成 EDL，也不下载视频、不访问任何平台接口。

判断 tier 前先读 $taxonomy，
不要把机械召回的候选直接当成最终分级结果。

交付前校验方案包结构：
    python $validator --help

"@
        # 用 UTF8 无 BOM 追加，避免 agent 读取时出现 BOM 干扰
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::AppendAllText($agentsFile, $block, $utf8NoBom)
        Ok "已追加到 $agentsFile"
    }
}

# ---------- 3. 验证 ----------
Say '[3/3] 验证安装'

$First = $Installed[0]
if (-not (Test-Path (Join-Path $First 'SKILL.md'))) { Die 'SKILL.md 未就位' }

$n = 0
foreach ($s in Get-ChildItem (Join-Path $First 'scripts') -Filter *.py) {
    & $Py -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" $s.FullName
    if ($LASTEXITCODE -ne 0) { Die "语法检查失败：$($s.Name)" }
    $n++
}
Ok "$n 个脚本语法检查通过"

& $Py (Join-Path (Join-Path $First 'scripts') 'validate_analysis_outputs.py') --help | Out-Null
if ($LASTEXITCODE -ne 0) { Die '校验器无法运行，请检查 Python 环境' }
Ok '校验器可运行'

foreach ($r in @('keyword-taxonomy', 'analysis-frameworks', 'analysis-handoff')) {
    if (-not (Test-Path (Join-Path (Join-Path $First 'references') "$r.md"))) {
        Die "缺少 references\$r.md"
    }
}
Ok '3 个参考文件就位'

Say '安装完成'
Write-Host @'

  对话里直接说：

    「拆解一下这个口播视频 D:\path\to\video.mp4」
    「给这个视频的关键词分级」
    「这段口播该插什么素材」

  技能只输出方案包到 <视频目录>\edit\，不会自动剪辑，
  也不会下载视频或访问任何外部接口。

'@
