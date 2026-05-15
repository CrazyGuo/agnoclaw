# UV 虚拟环境搭建指南

## 前置要求

- 已安装 UV (若未安装，可通过 `pip install uv` 或 `curl -LsSf https://astral.sh/uv/install.sh | sh` 安装)

## 操作步骤

### 1. 创建虚拟环境

在项目根目录执行以下命令创建 `.venv` 虚拟环境：

```bash
uv venv .venv
```

### 2. 激活虚拟环境

**Windows (PowerShell):**
```bash
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```bash
.venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### 3. 安装项目依赖

使用 `uv sync` 安装所有依赖（从 `uv.lock` 读取精确版本）：

```bash
uv sync
uv add anthropic
uv add openai
uv sync --extra tui
```

若需要安装开发依赖：

```bash
uv sync --dev
```

### 4. 验证安装

查看已安装的包：

```bash
uv pip list
```

### 5. 不同模型测试

#### 5.1 azure openai模型配置

```bash
$env:FLEX_AZURE_OPENAI_API_KEY="51XXX"
$env:FLEX_AZURE_OPENAI_BASE_URL="https://flexapimanager.flex.com/wuz-ops-platform/openai/deployments/gpt-5"
$env:AGNOCLAW_MODEL_FACTORY_MODULES="agnoclaw.custom_models.flex_azure"
```

在.agnoclaw.toml中定义模型：

```bash
default_model = "gpt-5"
default_provider = "flex-azure-openai"
```

#### 5.2 Minimax模型配置

```bash
$env:MINIMAX_API_KEY="sk-XXX"
$env:AGNOCLAW_MODEL_FACTORY_MODULES="agnoclaw.custom_models.minimax"
```

在.agnoclaw.toml中定义模型：

```bash
default_model = "MiniMax-M2.5"
default_provider = "minimax"
```

### 6. 运行项目

**使用 uv 运行TUI页面：**

```bash
uv run agnoclaw tui
```

## 常用命令参考

| 命令 | 说明 |
|------|------|
| `uv venv .venv` | 创建虚拟环境 |
| `uv sync` | 同步依赖（安装/更新） |
| `uv sync --dev` | 同步包括开发依赖 |
| `uv add <package>` | 添加新依赖 |
| `uv add --dev <package>` | 添加开发依赖 |
| `uv update` | 更新锁文件中的包 |
| `uv pip list` | 列出已安装的包 |
| `uv run <command>` | 在虚拟环境中运行命令 |
