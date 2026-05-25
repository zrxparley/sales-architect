#!/bin/bash
# ============================================================
# 售前架构师 CLI 安装脚本
# Sales Architect CLI Installer
# ============================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       售前架构师工具箱 · 安装程序                ║${NC}"
echo -e "${BLUE}║       Sales Architect CLI Installer              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Paths ───
SA_HOME="$HOME/.workbuddy/skills/sales-architect"
SKILLS_DIR="$HOME/.workbuddy/skills"
OUTPUT_DIR="$HOME/sales-architect-outputs"
CONFIG_FILE="$HOME/.sa-config"

# ─── Step 1: Create output directory ───
echo -e "${YELLOW}[1/6]${NC} 创建输出目录..."
mkdir -p "$OUTPUT_DIR"
echo -e "  ${GREEN}✓${NC} $OUTPUT_DIR"

# ─── Step 2: Clone missing repos ───
echo ""
echo -e "${YELLOW}[2/6]${NC} 检查依赖 Skill..."

REPOS=(
  "tian-dao-tui-yan-skill"
  "system-awakening"
  "kpmg-strategy-framework"
)

for repo in "${REPOS[@]}"; do
  dir="${SKILLS_DIR}/${repo}"
  if [ -d "$dir" ]; then
    echo -e "  ${GREEN}✓${NC} $repo (已安装)"
  else
    echo -e "  ${YELLOW}↓${NC} 正在拉取 $repo..."
    git clone --depth 1 "https://github.com/zrxparley/${repo}.git" "$dir" 2>/dev/null
    if [ $? -eq 0 ]; then
      echo -e "  ${GREEN}✓${NC} $repo 安装完成"
    else
      echo -e "  ${RED}✗${NC} $repo 拉取失败，请手动: git clone https://github.com/zrxparley/${repo}.git $dir"
    fi
  fi
done

# Check already-installed skills
ALREADY_INSTALLED=(
  "ai-daily-news"
  "business-decision-tool"
  "lead-scoring"
  "fullstack-design-studio"
  "solution-architect-expert"
)

for skill in "${ALREADY_INSTALLED[@]}"; do
  if [ -d "$SKILLS_DIR/$skill" ]; then
    echo -e "  ${GREEN}✓${NC} $skill (已安装)"
  else
    echo -e "  ${YELLOW}!${NC} $skill 未找到 (部分功能可能受限)"
  fi
done

# ─── Step 3: Install Python dependencies ───
echo ""
echo -e "${YELLOW}[3/6]${NC} 安装 Python 依赖..."

PYTHON=$(command -v python3 2>/dev/null || echo "")
if [ -z "$PYTHON" ]; then
  echo -e "  ${RED}✗${NC} 未找到 python3，请先安装 Python 3.10+"
  echo "    brew install python3"
  exit 1
fi

PY_VERSION=$($PYTHON --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
echo -e "  ${GREEN}✓${NC} Python $PY_VERSION"

$PYTHON -m pip install --quiet httpx questionary rich 2>/dev/null || {
  echo -e "  ${YELLOW}!${NC} pip install 遇到问题，尝试 --user..."
  $PYTHON -m pip install --user --quiet httpx questionary rich 2>/dev/null
}
echo -e "  ${GREEN}✓${NC} 依赖已安装 (httpx, questionary, rich)"

# ─── Step 4: Make bin/sa executable ───
echo ""
echo -e "${YELLOW}[4/6]${NC} 配置 CLI 入口..."

chmod +x "$SA_HOME/bin/sa" 2>/dev/null || true
chmod +x "$SA_HOME/sa.py" 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} sa 脚本已设置为可执行"

# ─── Step 5: Register shell alias ───
echo ""
echo -e "${YELLOW}[5/6]${NC} 注册 shell alias..."

ALIAS_LINE="alias sa='$SA_HOME/bin/sa'"

if [ -f "$HOME/.zshrc" ]; then
  SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bash_profile" ]; then
  SHELL_RC="$HOME/.bash_profile"
elif [ -f "$HOME/.bashrc" ]; then
  SHELL_RC="$HOME/.bashrc"
else
  SHELL_RC="$HOME/.zshrc"
fi

if grep -q "alias sa=" "$SHELL_RC" 2>/dev/null; then
  echo -e "  ${GREEN}✓${NC} alias 已存在 ($SHELL_RC)"
else
  echo "" >> "$SHELL_RC"
  echo "# Sales Architect CLI" >> "$SHELL_RC"
  echo "$ALIAS_LINE" >> "$SHELL_RC"
  echo -e "  ${GREEN}✓${NC} alias 已写入 $SHELL_RC"
fi

# ─── Step 6: Generate config template ───
echo ""
echo -e "${YELLOW}[6/6]${NC} 初始化配置文件..."

if [ -f "$CONFIG_FILE" ]; then
  echo -e "  ${GREEN}✓${NC} $CONFIG_FILE 已存在 (跳过)"
else
  DETECTED_BASE=""
  DETECTED_KEY=""

  if [ -f "$HOME/.claude/settings.json" ]; then
    DETECTED_BASE=$(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(d.get('env',{}).get('ANTHROPIC_BASE_URL',''))" 2>/dev/null || echo "")
    DETECTED_KEY=$(python3 -c "import json; d=json.load(open('$HOME/.claude/settings.json')); print(d.get('env',{}).get('ANTHROPIC_AUTH_TOKEN',''))" 2>/dev/null || echo "")
  fi

  if [ -n "$DETECTED_BASE" ]; then
    echo -e "  ${GREEN}✓${NC} 检测到已有的 API 配置 (来自 Claude Code)"
  fi

  cat > "$CONFIG_FILE" << EOF
{
  "api": {
    "base_url": "${DETECTED_BASE:-https://api.anthropic.com}",
    "api_key": "${DETECTED_KEY:-}",
    "model": "claude-sonnet-4-6"
  },
  "architect": {
    "name": "",
    "title": "售前架构师",
    "company": ""
  },
  "defaults": {
    "industry": "",
    "output_dir": "$OUTPUT_DIR"
  }
}
EOF
  echo -e "  ${GREEN}✓${NC} 配置模板已生成: $CONFIG_FILE"
fi

# ─── Done ───
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       ✓ 安装完成！                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${YELLOW}接下来:${NC}"
echo ""
echo -e "  1. 重新加载终端配置:"
echo -e "     ${BLUE}source $SHELL_RC${NC}"
echo ""
echo -e "  2. 配置 API (如果上面没有自动检测到):"
echo -e "     ${BLUE}sa config${NC}"
echo ""
echo -e "  3. 试试第一个命令:"
echo -e "     ${BLUE}sa help${NC}"
echo ""
