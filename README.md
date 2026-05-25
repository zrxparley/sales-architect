# 售前架构师工具箱 (Sales Architect CLI)

面向售前架构师的 AI 工具箱 CLI。整合 8 个专业 skill，覆盖售前全流程：
线索评估 → 行业研究 → 战略分析 → 方案设计 → 风险推演 → 原型开发 → 持续学习。

## 安装

### 方法 1: pip install（推荐）

```bash
# 从 GitHub 安装
pip install git+https://github.com/zrxparley/sales-architect.git

# 或克隆后本地安装
git clone https://github.com/zrxparley/sales-architect.git
cd sales-architect
pip install -e .

# 配置
sa config
```

### 方法 2: 传统安装

```bash
bash ~/.workbuddy/skills/sales-architect/install.sh
source ~/.zshrc
sa config
```

### 启用 Shell 自动补全

```bash
# 复制补全脚本到 zsh 补全目录
mkdir -p ~/.zsh/completions
cp completions/_sa ~/.zsh/completions/

# 添加到 ~/.zshrc
echo 'fpath=(~/.zsh/completions $fpath)' >> ~/.zshrc
echo 'autoload -Uz compinit && compinit' >> ~/.zshrc

# 重新加载
source ~/.zshrc
```

## 快速开始

```bash
sa help                 # 查看所有命令
sa lead-score           # 评估商机质量
sa news                 # AI 行业早报
sa strategy             # 客户战略分析
sa solution             # 方案设计
sa simulate             # 方案风险推演
```

## 命令列表

### 售前命令
| 命令 | 说明 |
|------|------|
| `sa lead-score` | 线索评估 — 8维100分量化 |
| `sa news` | AI行业早报 |
| `sa briefing <行业>` | 行业深度简报 |
| `sa strategy` | KPMG框架战略分析 |
| `sa simulate` | 天道推演 — 多路径风险模拟 |
| `sa solution` | 8步标准化方案设计 |
| `sa decide` | 商业决策分析 |
| `sa build` | 原型/POC开发 |
| `sa learn <主题>` | 技能树学习 |

### 组合工作流
| 命令 | 说明 |
|------|------|
| `sa cycle` | 完整售前周期 |
| `sa rfp <文件>` | RFP快速响应 |
| `sa compete <竞品>` | 竞标对抗分析 |

### 辅助命令
| 命令 | 说明 |
|------|------|
| `sa config` | 配置API/个人信息 |
| `sa status` | 查看skill安装状态 |
| `sa update` | 更新所有skill |
| `sa docs` | 打开输出目录 |
| `sa help` | 帮助文档 |

## 输出控制

```bash
sa lead-score --plain           # 纯文本（可粘贴微信）
sa lead-score --plain | pbcopy  # 一键复制到剪贴板
sa lead-score --tool claude     # 强制用Claude Code执行
sa lead-score --output-only     # 只生成prompt文件
```

## 配置

配置文件: `~/.sa-config`

```bash
sa config --show        # 查看当前配置
sa config               # 交互式修改
```

支持自定义 Base URL、API Key、模型名称，兼容任意 Anthropic 协议端点。

## 架构

- **内置模式**: 直接调 LLM API（线索评估、战略分析、推演等纯文本任务）
- **增强模式**: 路由到 Claude Code / WorkBuddy（方案设计、新闻搜索、POC开发）

## 依赖的 8 个 Skill

1. [lead-scoring](https://github.com/zrxparley/lead-scoring) — 线索打分
2. [ai-daily-news](https://github.com/zrxparley/ai-daily-news) — AI早报
3. [kpmg-strategy-framework](https://github.com/zrxparley/kpmg-strategy-framework) — KPMG战略框架
4. [tian-dao-tui-yan-skill](https://github.com/zrxparley/tian-dao-tui-yan-skill) — 天道推演
5. [solution-architect-expert](https://github.com/zrxparley/solution-architect-expert) — 方案设计
6. [business-decision-tool](https://github.com/zrxparley/business-decision-tool) — 商业决策
7. [fullstack-design-studio](https://github.com/zrxparley/fullstack-design-studio) — 全栈开发
8. [system-awakening](https://github.com/zrxparley/system-awakening) — 技能树学习
