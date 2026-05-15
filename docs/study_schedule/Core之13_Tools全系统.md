# Core 系列 13： Tools 全系统 —— AI 的双手

> 目标：小朋友也能看懂！用一个"工具箱"的比喻来讲清楚，agnoclaw 是如何给 AI 配备各种工具的，让它能够读写文件、执行命令、搜索网页、管理任务等。

---

## 一、"工具箱"比喻

想象 AI 是一个**刚入职的建筑工人**：
- 他有**脑子**（能思考、能推理）
- 但他**没有手**（不能自己拿起锤子、锯子）

如果不给工人工具，他只能站在原地不动。

在 agnoclaw 中，**Tools（工具）**就是 AI 的**双手**：
- **BashToolkit** → 能执行命令（拿锤子）
- **FilesToolkit** → 能读写文件（拿螺丝刀）
- **WebToolkit** → 能搜索网页（查地图）
- **TodoToolkit** → 能管理任务（记事本）

---

## 二、工具的组装工厂 —— get_default_tools()

文件：`src/agnoclaw/tools/__init__.py`

当 `AgentHarness` 创建时，它调用 `get_default_tools()` 来获取一套工具：

```python
def get_default_tools(
    config: HarnessConfig | None = None,  # 配置决定启用哪些工具
    subagents: dict[str, SubagentDefinition] | None = None,  # 子代理定义
    workspace_dir: str | Path | None = None,  # 工作区目录
    sandbox_dir: str | Path | None = None,  # 沙盒目录
    backend: RuntimeBackend | None = None,  # 后端（本地或沙盒）
) -> list:
    from agnoclaw.config import get_config

    cfg = config or get_config()

    # 1. 创建文件工具
    tools.append(FilesToolkit(
        workspace_dir=tool_sandbox_dir or tool_workspace_dir,
        adapter=resolved_workspace_adapter,
    ))

    # 2. 创建 bash 工具（如果启用）
    if cfg.enable_bash:
        tools.append(BashToolkit(...))

    # 3. 创建网页工具
    tools.append(WebToolkit(...))

    # 4. 创建待办事项工具（总是启用）
    tools.append(TodoToolkit())

    # 5. 创建进度追踪工具（总是启用）
    tools.append(ProgressToolkit(...))

    # 6. 创建子代理工具
    tools.append(make_subagent_tool(...))

    # 7. 可选工具（浏览器、MCP、媒体、笔记本）
    if cfg.enable_browser:
        tools.append(BrowserToolkit(...))

    for server_cfg in cfg.mcp_servers:
        tools.append(MCPToolkit(...))

    if cfg.enable_media_tools:
        tools.append(MediaToolkit())

    if cfg.enable_notebook_tools:
        tools.append(NotebookToolkit())

    return tools
```

---

## 三、BashToolkit —— 执行命令的双手

文件：`src/agnoclaw/tools/bash.py`

### 3.1 四个工具函数

```python
class BashToolkit(Toolkit):
    def __init__(self, timeout=120, workspace_dir=None, executor=None):
        super().__init__(name="bash")
        self.register(self.bash)         # 同步执行命令
        self.register(self.bash_start)   # 开始后台命令
        self.register(self.bash_output) # 获取后台命令输出
        self.register(self.bash_kill)   # 停止后台命令
```

| 工具 | 作用 | 比喻 |
|------|------|------|
| `bash(command)` | 同步执行命令，等待完成 | 直接动手做 |
| `bash_start(command)` | 开始后台命令 | 启动一个持续运行的进程 |
| `bash_output(task_id)` | 获取后台命令的输出 | 检查工作进展 |
| `bash_kill(task_id)` | 停止后台命令 | 叫停工作 |

### 3.2 bash() 详解

```python
@tool(name="bash", description="Execute a shell command synchronously...")
def bash(
    self,
    command: str,                          # 要执行的命令
    description: Optional[str] = None,     # 命令描述（可选）
    working_dir: Optional[str] = None,     # 工作目录
    timeout_seconds: Optional[int] = None, # 超时时间
) -> str:
    """Run a bash command and return its output."""
    timeout = timeout_seconds if timeout_seconds is not None else self.timeout

    try:
        result = self.executor.run(
            command=command,
            workdir=working_dir,
            timeout_seconds=timeout,
        )
        output = result.stdout
        if result.exit_code != 0:
            stderr = result.stderr.strip()
            if stderr:
                output += f"\n[stderr]\n{stderr}"
            output += f"\n[exit code: {result.exit_code}]"
        return output.strip() if output.strip() else "[no output]"
    except Exception as exc:
        raise BashToolError(f"Failed to execute command: {message}") from exc
```

### 3.3 后台命令示例

```python
# 开始一个长时间运行的命令
bash_start("python train_model.py --epochs 100")
# 返回：Started background task abc123, pid: 45678, status: running

# 检查输出
bash_output("abc123")
# 返回：[task abc123] status=running exit_code=n/a pid=45678
# Processing epoch 1/100...
# Processing epoch 2/100...

# 停止命令
bash_kill("abc123")
# 返回：Killed task abc123
```

---

## 四、FilesToolkit —— 读写文件的双手

文件：`src/agnoclaw/tools/files.py`

### 4.1 七个工具函数

```python
class FilesToolkit(Toolkit):
    def __init__(self, workspace_dir=None, adapter=None):
        super().__init__(name="files")
        self.register(self.read_file)        # 读取文件
        self.register(self.write_file)       # 写入文件
        self.register(self.edit_file)        # 编辑文件
        self.register(self.multi_edit_file)  # 批量编辑
        self.register(self.glob_files)        # 文件搜索
        self.register(self.grep_files)        # 内容搜索
        self.register(self.list_dir)         # 列出目录
```

| 工具 | 作用 | 使用场景 |
|------|------|----------|
| `read_file(path, offset=0, limit=2000)` | 读取文件内容 | 看文件内容 |
| `write_file(path, content)` | 写入文件内容 | 创建新文件或覆盖 |
| `edit_file(path, old_string, new_string)` | 替换文件内容 | 修改文件的一部分 |
| `multi_edit_file(path, edits)` | 批量替换 | 同时改多处 |
| `glob_files(pattern, base_dir)` | 搜索文件 | 找所有 `.py` 文件 |
| `grep_files(pattern, path, ...)` | 搜索文件内容 | 在代码里找某个函数 |
| `list_dir(path)` | 列出目录内容 | 看文件夹里有什么 |

### 4.2 read_file() 详解

```python
def read_file(self, path: str, offset: int = 0, limit: int = 2000) -> str:
    return self.adapter.read_file(path=path, offset=offset, limit=limit)
```

- `offset=0`：从第 0 行开始读
- `limit=2000`：最多读 2000 行

### 4.3 edit_file() 详解

```python
def edit_file(self, path: str, old_string: str, new_string: str) -> str:
    return self.adapter.edit_file(path=path, old_string=old_string, new_string=new_string)
```

**重要规则：** `old_string` 必须在文件中是**唯一的**，否则不知道改哪一处。

```
示例：
文件内容：
```
def hello():
    print("Hello")
    print("World")
```

edit_file(path, old_string="print(\"Hello\")", new_string="print(\"Hi\")")
    ↓
结果：
```
def hello():
    print("Hi")
    print("World")
```
```

---

## 五、WebToolkit —— 搜索网页的双手

文件：`src/agnoclaw/tools/web.py`

### 5.1 两个工具函数

```python
class WebToolkit(Toolkit):
    def __init__(self, search_enabled=True, fetch_enabled=True):
        super().__init__(name="web")
        if search_enabled:
            self.register(self.web_search)
        if fetch_enabled:
            self.register(self.web_fetch)
```

| 工具 | 作用 |
|------|------|
| `web_search(query)` | 搜索网页 |
| `web_fetch(url)` | 获取网页内容 |

### 5.2 多后端自动选择

`web_search` 会**自动选择**最好的搜索后端：

```
优先级：Tavily > Exa > Brave > DuckDuckGo（免费备选）
```

```python
def web_search(self, query: str) -> str:
    # 尝试 Tavily
    try:
        return self._search_tavily(query)
    except Exception:
        pass

    # 尝试 Exa
    try:
        return self._search_exa(query)
    except Exception:
        pass

    # ... 以此类推

    # 最后用 DuckDuckGo（免费）
    return self._search_duckduckgo(query)
```

### 5.3 HTML 转文本

网页内容通常是 HTML，需要转成纯文本：

```python
def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # 去掉 script 和 style 标签
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)
```

---

## 六、TodoToolkit —— 管理任务的双手

文件：`src/agnoclaw/tools/tasks.py`

### 6.1 四个工具函数

```python
class TodoToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="todo")
        self._todos: dict[str, dict[str, Any]] = {}
        self._next_id = 1
        self.register(self.create_todo)
        self.register(self.update_todo)
        self.register(self.list_todos)
        self.register(self.delete_todo)
```

| 工具 | 作用 |
|------|------|
| `create_todo(subject, description, priority)` | 创建待办事项 |
| `update_todo(todo_id, status, notes)` | 更新状态 |
| `list_todos()` | 列出所有待办 |
| `delete_todo(todo_id)` | 删除待办 |

### 6.2 使用规则（刻在工具描述里）

```python
def create_todo(self, subject: str, description: str = "", priority: str = "medium") -> str:
    """
    Use this when a task has 3 or more distinct steps.
    Create all todos upfront, then work through them one at a time.
    """
```

```python
def update_todo(self, todo_id: str, status: str, notes: str = "") -> str:
    """
    Mark tasks in_progress BEFORE starting them.
    Mark tasks completed IMMEDIATELY AFTER finishing (not in batches).
    Update status in real-time so the user sees progress.
    """
```

---

## 七、ProgressToolkit —— 进度追踪的双手

文件：`src/agnoclaw/tools/tasks.py`

### 7.1 作用

跨会话追踪项目进度，写入两个文件：
- `progress.md` — 会话连续性（这次做到哪了）
- `features.md` — 需求清单（要做什么）

### 7.2 使用场景

当一个项目跨越多个会话时：

```
Session 1:
- 完成了用户认证模块
- 写入 progress.md："用户认证完成，NEXT: 订单管理"

Session 2:
- 读取 progress.md
- 继续订单管理模块
```

---

## 八、SubagentTool —— 召唤子代理的双手

文件：`src/agnoclaw/tools/tasks.py`

### 8.1 为什么要子代理？

如果一个任务很复杂，全放进主上下文会**撑爆**（context window）。

解决方案：**召唤一个子代理**来处理这个任务，子代理有独立的上下文。

```
主代理（你的助手）
    ↓ 召唤
子代理（专门做代码审查）
    ↓
子代理完成工作，返回结果
    ↓
主代理继续
```

### 8.2 使用方式

```python
spawn_subagent(
    task="Review the code in src/auth.py for security issues",
    agent_type="research",  # 或 "code", "data", "general"
    model="claude-sonnet-4-6"
)
```

### 8.3 内置子代理类型

| 类型 | 用途 |
|------|------|
| `research` | 研究、搜索、分析 |
| `code` | 代码生成、调试 |
| `data` | 数据处理、分析 |
| `general` | 通用任务 |

---

## 九、BrowserToolkit —— 浏览器的双手

文件：`src/agnoclaw/tools/browser.py`

需要安装 `playwright`：

```bash
pip install agnoclaw[browser]
```

### 9.1 工具函数

| 工具 | 作用 |
|------|------|
| `browser_navigate(url)` | 打开网址 |
| `browser_click(selector)` | 点击元素 |
| `browser_type(selector, text)` | 输入文字 |
| `browser_screenshot()` | 截图 |
| `browser_snapshot()` | 获取页面内容 |
| `browser_scroll(direction)` | 滚动 |
| `browser_fill_form(data)` | 填表单 |
| `browser_close()` | 关闭浏览器 |

---

## 十、MCPToolkit —— MCP 服务器连接

文件：`src/agnoclaw/tools/mcp.py`

MCP = Model Context Protocol

### 10.1 配置

在 `config.toml` 中配置：

```toml
[[mcp_servers]]
name = "filesystem"
command = ["npx", "tsx", "path/to/server"]

[[mcp_servers]]
name = "github"
url = "https://api.github.com/mcp"
```

### 10.2 工作原理

```
agnoclaw
    ↓ 连接
MCP 服务器（如 GitHub API）
    ↓
暴露服务器提供的工具给 AI 使用
```

---

## 十一、完整工具列表

| 工具包 | 工具 | 默认启用 |
|--------|------|----------|
| FilesToolkit | read, write, edit, multi_edit, glob, grep, list_dir | ✅ |
| BashToolkit | bash, bash_start, bash_output, bash_kill | ✅（可禁用）|
| WebToolkit | web_search, web_fetch | ✅（可禁用）|
| TodoToolkit | create_todo, update_todo, list_todos, delete_todo | ✅ |
| ProgressToolkit | update_progress, list_progress | ✅ |
| SubagentTool | spawn_subagent | ✅ |
| BrowserToolkit | navigate, click, type, screenshot... | ❌（需要 browser）|
| MCPToolkit | 动态（取决于 MCP 服务器） | ❌（需要配置）|
| MediaToolkit | read_image, read_pdf | ❌（需要 media）|
| NotebookToolkit | notebook_read, notebook_edit_cell... | ❌（需要 notebook）|

---

## 十二、思考题

1. 为什么 `enable_bash = false` 是默认选项之一？（安全考虑）
2. 为什么 `web_search` 需要多个后端？用一个不行吗？
3. 子代理和主代理共享上下文吗？如果不共享，怎么传递结果？

---

> 下一篇：《Core 系列 14： 后端抽象 —— 沙盒与本地执行》——深入解析 CommandExecutor、WorkspaceAdapter 等后端协议