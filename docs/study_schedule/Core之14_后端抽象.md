# Core 系列 14： 后端抽象 —— 沙盒与本地执行

> 目标：小朋友也能看懂！用一个"工厂流水线"的比喻来讲清楚，后端抽象是如何让 agnoclaw 同时支持本地执行和沙盒隔离执行的。

---

## 一、"工厂流水线"比喻

想象一个**食品加工厂**：
- 有的工厂**在自己家生产**（本地执行）
- 有的工厂**把原料送到别人家生产**（沙盒执行）

无论在哪里生产，工厂都需要：
- **厨房**（CommandExecutor）—— 能执行命令
- **储藏室**（WorkspaceAdapter）—— 能读写文件

agnoclaw 的**后端抽象**就是这套"厨房+储藏室"的接口标准，让同样的代码可以在本地或沙盒环境中运行。

---

## 二、两层协议（Protocol）

文件：`src/agnoclaw/tools/backends.py`

### 2.1 CommandExecutor —— 厨房协议

```python
class CommandExecutor(Protocol):
    """Backend interface for shell execution."""

    def run(
        self,
        *,
        command: str,              # 要执行的命令
        workdir: str | None,        # 工作目录
        timeout_seconds: int | None, # 超时时间
    ) -> CommandResult:              # 返回结果
        ...

    def start(
        self,
        *,
        command: str,
        workdir: str | None,
        description: str | None = None,
    ) -> BackgroundCommandHandle:   # 后台任务句柄
        ...

    def output(
        self,
        *,
        task_id: str,
        max_chars: int = 8000,
        tail: bool = True,
    ) -> BackgroundCommandOutput:  # 后台任务输出
        ...

    def kill(self, *, task_id: str, force: bool = False) -> str:
        ...
```

**比喻：** 厨房需要会做四件事：
- `run` — 做一道菜（同步）
- `start` — 开始一个长时间任务（如熬汤）
- `output` — 检查任务进展
- `kill` — 停止任务

### 2.2 WorkspaceAdapter —— 储藏室协议

```python
class WorkspaceAdapter(Protocol):
    """Backend interface for workspace/file operations."""

    workspace_dir: Path  # 储藏室的位置

    def read_file(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        ...

    def write_file(self, path: str, content: str) -> str:
        ...

    def edit_file(self, path: str, old_string: str, new_string: str) -> str:
        ...

    def multi_edit_file(self, path: str, edits: list[dict[str, str]]) -> str:
        ...

    def glob_files(self, pattern: str, base_dir: str | None = None, path: str | None = None) -> str:
        ...

    def grep_files(self, pattern: str, path: str | None = None, ...) -> str:
        ...

    def list_dir(self, path: str | None = None) -> str:
        ...
```

**比喻：** 储藏室需要会做七件事：
- `read_file` — 取东西
- `write_file` — 放东西
- `edit_file` — 换东西
- `multi_edit_file` — 批量换东西
- `glob_files` — 找东西
- `grep_files` — 搜东西
- `list_dir` — 看清单

---

## 三、本地实现（Local）

文件：`src/agnoclaw/tools/backends.py`

### 3.1 LocalCommandExecutor —— 本地厨房

```python
class LocalCommandExecutor:
    """Host-local subprocess implementation for command execution."""

    def __init__(self, *, workspace_dir: str | Path | None = None, max_background_tasks: int = 16):
        self.workspace_dir = ...
        self.max_background_tasks = max_background_tasks
        self._tasks: dict[str, _BackgroundTask] = {}  # 后台任务表
```

**特点：**
- 用 `subprocess.run()` 执行命令
- 用 `subprocess.Popen()` 启动后台任务
- 任务输出保存到 `~/.agnoclaw/tmp/bash_tasks/`

### 3.2 LocalWorkspaceAdapter —— 本地储藏室

```python
class LocalWorkspaceAdapter:
    """Host-local pathlib implementation for file operations."""

    def __init__(self, workspace_dir: str | Path | None = None) -> None:
        self.workspace_dir = (
            Path(workspace_dir).expanduser().resolve()
            if workspace_dir is not None
            else Path.cwd().resolve()
        )
```

**特点：**
- 用 `pathlib.Path` 读写文件
- 相对路径基于 `workspace_dir` 解析

### 3.3 read_file 的实现细节

```python
def read_file(self, path: str, offset: int = 0, limit: int = 2000) -> str:
    file_path = Path(path).expanduser()

    # 检查文件存在且是文件
    if not file_path.exists():
        return f"[error] File not found: {path}"
    if not file_path.is_file():
        return f"[error] Not a file: {path}"

    # 50MB 大小保护
    file_size = file_path.stat().st_size
    if file_size > _MAX_READ_SIZE:
        return f"[error] File too large ({file_size // (1024 * 1024)}MB)"

    # 读取并添加行号
    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(0, offset - 1) if offset > 0 else 0
    end = start + limit
    selected = lines[start:end]
    numbered = [f"{start + i + 1:6}\t{line}" for i, line in enumerate(selected)]
    result = "\n".join(numbered)

    if len(lines) > end:
        result += f"\n... ({len(lines) - end} more lines)"

    return result
```

### 3.4 edit_file 的实现细节

```python
def edit_file(self, path: str, old_string: str, new_string: str) -> str:
    file_path = Path(path).expanduser()

    content = file_path.read_text(encoding="utf-8")
    count = content.count(old_string)

    if count == 0:
        return f"[error] old_string not found in {path}. Read the file first."
    if count > 1:
        return f"[error] old_string appears {count} times. Provide more context."

    new_content = content.replace(old_string, new_string, 1)  # 只替换第一个
    file_path.write_text(new_content, encoding="utf-8")
    return f"Edited {path}: replaced 1 occurrence."
```

---

## 四、沙盒包装（Sandbox Wrappers）

如果需要**隔离执行**（AI 不能直接访问真实文件系统），可以用沙盒包装。

### 4.1 SessionSandboxCommandExecutor

把本地厨房包装成"只能在沙盒里工作"：

```python
class SessionSandboxCommandExecutor:
    """Wrap a command executor so default/relative work happens in a session sandbox."""

    def __init__(
        self,
        executor: CommandExecutor,  # 被包装的厨房
        *,
        workspace_dir: str | Path,  # 工作区根目录
        sandbox_dir: str | Path,    # 沙盒目录（隔离区）
    ) -> None:
        self._executor = executor
        self._workspace_dir = Path(workspace_dir).expanduser().resolve()
        self._sandbox_dir = Path(sandbox_dir).expanduser().resolve()
        self.workspace_dir = str(self._sandbox_dir)  # 默认工作目录变成沙盒

    def _resolve_workdir(self, workdir: str | None) -> str:
        if workdir is None:
            return str(self._sandbox_dir)  # 默认用沙盒

        candidate = Path(workdir).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
            # 必须是沙盒内或工作区内
            if _is_within(resolved, self._sandbox_dir) or _is_within(resolved, self._workspace_dir):
                return str(resolved)
            raise RuntimeError(f"Path must be inside sandbox or workspace: {workdir}")

        # 相对路径：解析到沙盒内
        resolved = (self._sandbox_dir / candidate).resolve()
        if not _is_within(resolved, self._sandbox_dir):
            raise RuntimeError(f"Relative path must stay inside sandbox: {workdir}")
        return str(resolved)
```

### 4.2 SessionSandboxWorkspaceAdapter

把本地储藏室包装成"只能在沙盒里读写"：

```python
class SessionSandboxWorkspaceAdapter:
    """Wrap a workspace adapter so relative paths resolve inside a session sandbox."""

    def _resolve_path(self, path: str | None) -> Path:
        if path is None:
            return self._sandbox_dir

        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
            # 必须是沙盒内或工作区内
            if _is_within(resolved, self._sandbox_dir) or _is_within(resolved, self._workspace_dir):
                return resolved
            raise ValueError(f"Path must be inside sandbox or workspace: {path}")

        # 相对路径：解析到沙盒内
        resolved = (self._sandbox_dir / candidate).resolve()
        if not _is_within(resolved, self._sandbox_dir):
            raise ValueError(f"Relative paths must stay inside sandbox: {path}")
        return resolved
```

---

## 五、bind_session_sandbox() 工厂函数

```python
def bind_session_sandbox(
    *,
    command_executor: CommandExecutor,
    workspace_adapter: WorkspaceAdapter,
    workspace_dir: str | Path,
    sandbox_dir: str | Path | None,
) -> tuple[CommandExecutor, WorkspaceAdapter]:
    """Wrap backend adapters so relative/default tool operations use `sandbox_dir`."""

    if sandbox_dir is None:
        return command_executor, workspace_adapter  # 不需要沙盒，直接返回

    # 包装成沙盒版本
    return (
        SessionSandboxCommandExecutor(
            command_executor,
            workspace_dir=workspace_dir,
            sandbox_dir=sandbox_dir,
        ),
        SessionSandboxWorkspaceAdapter(
            workspace_adapter,
            workspace_dir=workspace_dir,
            sandbox_dir=sandbox_dir,
        ),
    )
```

---

## 六、RuntimeBackend —— 统一入口

文件：`src/agnoclaw/backends.py`

```python
class RuntimeBackend:
    """
    Single runtime backend override for shell, files, skills, and browser tools.
    """

    def __init__(
        self,
        *,
        command_executor: CommandExecutor | None = None,
        workspace_adapter: WorkspaceAdapter | None = None,
        browser_backend: BrowserBackend | None = None,
    ) -> None:
        # command_executor 和 workspace_adapter 必须同时提供或不提供
        if (command_executor is None) != (workspace_adapter is None):
            raise ValueError("RuntimeBackend requires both or neither.")
        self._command_executor = command_executor
        self._workspace_adapter = workspace_adapter
        self._browser_backend = browser_backend

    def uses_host_runtime(self) -> bool:
        """Return True only for the default host-local backend mode."""
        return (
            type(self) is RuntimeBackend  # 不是子类
            and self._command_executor is None  # 没有提供执行器
            and self._workspace_adapter is None  # 没有提供适配器
            and self._browser_backend is None  # 没有提供浏览器后端
        )

    def resolve(
        self,
        *,
        workspace_dir: str | Path,
    ) -> ResolvedRuntimeBackend:
        """解析出一个完整的运行时后端"""
        workspace_path = Path(workspace_dir).expanduser().resolve()
        command_executor = self.resolve_command_executor(workspace_dir=workspace_path)
        workspace_adapter = self.resolve_workspace_adapter(workspace_dir=workspace_path)
        return ResolvedRuntimeBackend(
            command_executor=command_executor,
            workspace_adapter=workspace_adapter,
            skill_runtime=self.resolve_skill_runtime(...),
            browser_backend=self.resolve_browser_backend(),
        )
```

---

## 七、ResolvedRuntimeBackend —— 解析后的后端

```python
@dataclass(frozen=True)
class ResolvedRuntimeBackend:
    """Resolved runtime capabilities for one concrete workspace."""

    command_executor: CommandExecutor
    workspace_adapter: WorkspaceAdapter
    skill_runtime: SkillRuntimeBackend
    browser_backend: BrowserBackend | None = None
```

---

## 八、完整流程图

```
get_default_tools(config, ...)
    │
    ├── RuntimeBackend() 创建默认后端
    │       │
    │       └── uses_host_runtime() = True（本地模式）
    │
    ├── backend.resolve(workspace_dir=...) 解析后端
    │       │
    │       ├── resolve_command_executor()
    │       │       └── LocalCommandExecutor(workspace_dir)
    │       │
    │       ├── resolve_workspace_adapter()
    │       │       └── LocalWorkspaceAdapter(workspace_dir)
    │       │
    │       └── resolve_skill_runtime()
    │               └── LocalSkillRuntimeBackend(working_dir)
    │
    ├── bind_session_sandbox() 绑定沙盒
    │       │
    │       └── 如果 sandbox_dir=None：
    │           返回 (LocalCommandExecutor, LocalWorkspaceAdapter)
    │           否则：
    │           返回 (SessionSandboxCommandExecutor, SessionSandboxWorkspaceAdapter)
    │
    └── 创建工具包
            │
            ├── FilesToolkit(adapter=workspace_adapter)
            ├── BashToolkit(executor=command_executor)
            ├── WebToolkit(...)
            └── ...
```

---

## 九、沙盒的安全性

**问题：** 如果 AI 想读取 `/etc/passwd`（敏感文件），沙盒能阻止吗？

**答案：** 能！

```python
def _resolve_path(self, path: str | None) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
        # 检查是否在沙盒或工作区内
        if _is_within(resolved, self._sandbox_dir) or _is_within(resolved, self._workspace_dir):
            return resolved
        # 不在内 → 报错
        raise ValueError(f"Path must be inside sandbox or workspace: {path}")
```

所以：
- `/etc/passwd` 不在沙盒内 → **拒绝**
- `~/project/file.txt` 不在工作区内 → **拒绝**
- `./file.txt`（相对路径）→ **解析到沙盒内** → **允许**

---

## 十、思考题

1. 如果同时提供 `command_executor` 和 `workspace_adapter`，`uses_host_runtime()` 返回什么？
2. 如果 AI 执行 `bash("rm -rf /")`，沙盒能阻止吗？
3. 为什么 `LocalCommandExecutor` 用 `shell=True` 执行命令？这安全吗？

---

> 下一篇：《Core 系列 15： Runtime 运行时合约 —— 安全护栏》——深入解析 hooks、policy、events、guardrails、permissions 等运行时合约