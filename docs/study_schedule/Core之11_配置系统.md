# Core 系列 11： 配置系统 —— 一切的开端

> 目标：小朋友也能看懂！用一个"游戏设置菜单"的比喻来讲清楚，agnoclaw 是如何通过配置系统来控制整个程序的行为的。

---

## 一、"游戏设置菜单"比喻

想象你在玩一个**视频游戏**：
- 游戏开始前，你要去**设置菜单**调整各种选项
- 画质：高/中/低？
- 音效：开/关？
- 游戏难度：简单/普通/困难？

这些设置决定了你玩游戏的方式。

在 agnoclaw 中，**配置系统（Config）**就像这个设置菜单：
- 它控制用哪个 AI 模型
- 它决定是否启用某些工具（bash、网页搜索等）
- 它设置心跳检查的频率
- 它定义安全规则（哪些能访问，哪些不能）

---

## 二、配置文件的层级

文件：`src/agnoclaw/config.py`

agnoclaw 使用**三层配置**，优先级从高到低：

```
┌─────────────────────────────────────────────┐
│  第一层：环境变量（最高优先级）              │
│  例如：AGNOCLAW_DEFAULT_MODEL=claude-haiku-4│
├─────────────────────────────────────────────┤
│  第二层：用户配置文件                        │
│  ~/.agnoclaw/config.toml                    │
├─────────────────────────────────────────────┤
│  第三层：项目配置文件                        │
│  .agnoclaw.toml（在当前目录）               │
├─────────────────────────────────────────────┤
│  第四层：代码默认值（最低优先级）            │
│  config.py 中写的默认值                     │
└─────────────────────────────────────────────┘
```

**优先级规则：谁更具体，谁说了算！**

```
环境变量 > 项目配置 > 用户配置 > 默认值
```

### 2.1 环境变量示例

```bash
# 设置默认模型
export AGNOCLAW_DEFAULT_MODEL=claude-sonnet-4-6

# 设置工作区目录
export AGNOCLAW_WORKSPACE_DIR=~/my-workspace

# 禁用心跳
export AGNOCLAW_HB_ENABLED=false
```

### 2.2 TOML 配置文件示例

**用户配置** `~/.agnoclaw/config.toml`：
```toml
[default]
default_model = "claude-opus-4-7"
default_provider = "anthropic"

[workspace]
workspace_dir = "~/.agnoclaw/workspace"

[heartbeat]
enabled = true
interval_minutes = 30
active_hours_start = "09:00"
active_hours_end = "21:00"
```

**项目配置** `.agnoclaw.toml`：
```toml
[default]
default_model = "claude-sonnet-4-6"  # 覆盖用户配置

[tools]
enable_bash = false  # 禁用 bash 工具（更安全）
```

---

## 三、核心配置类

### 3.1 HeartbeatConfig（心跳配置）

```python
class HeartbeatConfig(BaseSettings):
    enabled: bool = False                      # 是否启用心跳
    interval_minutes: int = 30               # 检查间隔（分钟）
    active_hours_start: str = "08:00"        # 工作时间开始
    active_hours_end: str = "22:00"          # 工作时间结束
    model: str = "claude-haiku-4-5-20251001" # 心跳检查用的模型（便宜的）
    ok_threshold_chars: int = 300            # HEARTBEAT_OK 回复超过这个长度才显示
    target: str = "last"                     # 通知发给谁
```

### 3.2 StorageConfig（存储配置）

```python
class StorageConfig(BaseSettings):
    backend: str = "sqlite"                   # 用 SQLite 还是 PostgreSQL
    sqlite_path: str = "~/.agnoclaw/sessions.db"
    postgres_url: str | None = None          # PostgreSQL 连接地址
    session_table: str = "agnoclaw_sessions"
    memory_table: str = "agnoclaw_memories"
```

### 3.3 HarnessConfig（主配置）

这是最重要的配置类，包含了所有设置：

```python
class HarnessConfig(BaseSettings):
    # 模型配置
    default_model: str = "claude-sonnet-4-6"      # 默认模型
    default_provider: str = "anthropic"            # 默认提供商

    # 工作区
    workspace_dir: str = "~/.agnoclaw/workspace"

    # 会话历史
    session_history_runs: int = 10               # 保留多少轮对话历史

    # 工具开关
    enable_bash: bool = True                     # 启用 bash 工具
    enable_web_search: bool = True               # 启用网页搜索
    enable_web_fetch: bool = True                # 启用网页获取
    bash_timeout_seconds: int = 120               # bash 命令超时
    enable_background_bash_tools: bool = False    # 启用后台 bash 工具

    # 学习系统
    enable_learning: bool = False                # 启用跨会话学习
    learning_mode: str = "agentic"               # 学习模式

    # 压缩系统
    enable_compression: bool = False             # 启用上下文压缩
    compress_token_limit: int | None = None      # 压缩触发阈值

    # 心跳和存储
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # 浏览器和 MCP
    enable_browser: bool = False                 # 启用浏览器工具
    mcp_servers: list[dict] = Field(default_factory=list)  # MCP 服务器配置

    # 媒体和笔记本
    enable_media_tools: bool = False            # 启用媒体工具
    enable_notebook_tools: bool = False          # 启用笔记本工具

    # 插件系统
    enable_plugins: bool = True                  # 启用插件发现
    plugin_paths: list[str] = Field(default_factory=list)  # 显式插件路径

    # ClawHub
    clawhub_url: str = "https://clawhub.ai"     # ClawHub 地址
    clawhub_cache_dir: str = "~/.agnoclaw/cache/hub"  # 缓存目录

    # 层级工作区
    global_workspace_dir: str = "~/.agnoclaw/global"
    project_workspace_dir: str = ".agnoclaw"

    # TUI 主题
    theme: str = "textual-dark"                # TUI 主题

    # 安全护栏
    event_sink_mode: str = "best_effort"       # 事件处理模式
    policy_fail_open: bool = False              # 策略失败时是否开放
    guardrails_enabled: bool = True             # 是否启用护栏
    path_guardrails_enabled: bool = True        # 路径护栏
    path_allowed_roots: list[str] = []          # 允许的路径根目录
    path_blocked_roots: list[str] = []         # 禁止的路径根目录
    network_enabled: bool = True                # 是否允许网络访问
    network_enforce_https: bool = True          # 是否强制 HTTPS
    network_allowed_hosts: list[str] = []       # 允许的主机
    network_blocked_hosts: list[str] = []       # 禁止的主机
    network_block_private_hosts: bool = True    # 是否阻止私有主机
    network_block_in_bash: bool = True         # bash 中是否阻止网络命令

    # 权限控制
    permission_mode: str = "bypass"            # 权限模式
    permission_require_approver: bool = False   # 是否需要审批者
    permission_preapproved_tools: list[str] = []   # 预批准的工具
    permission_preapproved_categories: list[str] = []  # 预批准的类别
```

---

## 四、配置合并机制

### 4.1 深度合并

当多层配置合并时，使用**深度合并**策略：

```python
def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并嵌套字典，override 优先"""
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            # 如果都是字典，递归合并
            merged[key] = _deep_merge(merged[key], value)
        else:
            # 否则 override 覆盖 base
            merged[key] = value
    return merged
```

### 4.2 合并示例

假设有以下配置：

**用户配置** `~/.agnoclaw/config.toml`：
```toml
[default]
default_model = "claude-opus-4-7"
enable_bash = true

[heartbeat]
enabled = true
interval_minutes = 30
```

**项目配置** `.agnoclaw.toml`：
```toml
[default]
default_model = "claude-sonnet-4-6"  # 覆盖用户配置
enable_bash = false                 # 禁用 bash

[heartbeat]
interval_minutes = 60               # 只覆盖 interval_minutes
```

**合并结果**：
```python
{
    "default": {
        "default_model": "claude-sonnet-4-6",  # 项目覆盖用户
        "enable_bash": false                    # 项目覆盖用户
    },
    "heartbeat": {
        "enabled": true,           # 用户配置保留
        "interval_minutes": 60,    # 项目覆盖用户
    }
}
```

---

## 五、get_config() 单例模式

```python
@lru_cache(maxsize=1)
def get_config() -> HarnessConfig:
    """加载并缓存合并后的配置"""
    # 加载 TOML 文件（项目级覆盖用户级）
    user_toml = _load_toml_config(Path.home() / ".agnoclaw" / "config.toml")
    project_toml = _load_toml_config(Path.cwd() / ".agnoclaw.toml")

    # 合并：用户 → 项目 → 环境变量（环境变量最后加载，自动获胜）
    merged = _deep_merge(user_toml, project_toml)

    # 创建 HarnessConfig（环境变量会在这一步被读取）
    return HarnessConfig(**merged)
```

**单例模式的好处**：
- 配置文件只读取一次，之后都从缓存返回
- 避免重复读取文件，提高性能

---

## 六、环境变量的读取

`HarnessConfig` 使用 `pydantic-settings` 的 `BaseSettings` 自动读取环境变量：

```python
class HarnessConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGNOCLAW_",          # 环境变量前缀
        env_nested_delimiter="__",      # 嵌套分隔符
    )
```

规则：
- `AGNOCLAW_DEFAULT_MODEL` → `default_model`
- `AGNOCLAW_HEARTBEAT__ENABLED` → `heartbeat.enabled`（两层嵌套用 `__`）

```bash
# 示例：设置嵌套配置
export AGNOCLAW_HEARTBEAT__INTERVAL_MINUTES=45
```

---

## 七、关键配置项详解

### 7.1 模型配置

```python
default_model: str = "claude-sonnet-4-6"      # 默认模型
default_provider: str = "anthropic"           # 提供商
```

支持的提供商：
- `anthropic` — Claude 系列
- `openai` — GPT 系列
- `google` — Gemini 系列
- `groq` — Groq 系列
- `ollama` — 本地模型

### 7.2 工具开关

```python
enable_bash: bool = True                     # 允许执行 bash 命令
enable_web_search: bool = True               # 允许搜索网页
enable_web_fetch: bool = True                # 允许获取网页内容
bash_timeout_seconds: int = 120              # bash 命令超过120秒会超时
```

### 7.3 学习模式

```python
enable_learning: bool = False                # 是否启用学习
learning_mode: str = "agentic"              # 学习模式
```

学习模式选项：
- `always` — 每次运行后自动学习
- `agentic` — AI 决定什么时候学习（推荐）
- `propose` — AI 提出学习建议，用户审核
- `hitl` — 用户必须批准每次学习

### 7.4 安全护栏

```python
guardrails_enabled: bool = True             # 是否启用护栏
path_guardrails_enabled: bool = True       # 路径边界检查
network_enabled: bool = True               # 是否允许网络访问
network_block_private_hosts: bool = True   # 是否阻止私有IP
permission_mode: str = "bypass"            # 权限模式
```

---

## 八、配置在代码中的使用

### 8.1 AgentHarness 使用配置

```python
# agent.py 中
def __init__(self, ..., config: HarnessConfig | None = None):
    self.config = config or get_config()

    # 使用配置决定行为
    if self.config.enable_compression:
        self._setup_compression()

    if self.config.enable_learning:
        self._setup_learning()
```

### 8.2 get_default_tools() 使用配置

```python
# tools/__init__.py 中
def get_default_tools(config, ...):
    tools = []

    if config.enable_bash:
        tools.append(BashToolkit(...))

    if config.enable_web_search:
        tools.append(WebToolkit(...))

    return tools
```

### 8.3 HeartbeatDaemon 使用配置

```python
# heartbeat/daemon.py 中
def __init__(self, ..., config: HarnessConfig | None = None):
    self._config = config or get_config()

    interval = self._config.heartbeat.interval_minutes
```

---

## 九、完整的配置流程图

```
启动 agnoclaw
    │
    ▼
get_config() 被调用
    │
    ├── 读取 ~/.agnoclaw/config.toml（用户配置）
    │
    ├── 读取 .agnoclaw.toml（项目配置）
    │
    ├── 合并：用户配置 + 项目配置
    │        （深度合并，项目优先）
    │
    ├── 创建 HarnessConfig(**merged)
    │   （pydantic 自动读取环境变量）
    │
    └── 返回合并后的配置
            │
            ▼
AgentHarness 使用配置
    ├── default_model → 创建 Agno Agent
    ├── enable_bash → 是否添加 BashToolkit
    ├── heartbeat → 启动 HeartbeatDaemon
    ├── guardrails → 启用安全护栏
    └── ...
```

---

## 十、思考题

1. 如果只想在项目中使用某个配置，不影响其他项目，应该怎么设置？
2. `learning_mode = "agentic"` 和 `learning_mode = "hitl"` 有什么区别？
3. 为什么需要 `network_block_private_hosts = True`？阻止私有IP有什么好处？

---

> 下一篇：《Core 系列 12： SystemPromptBuilder —— AI 的大脑培训手册》——深入解析系统提示词的组装过程