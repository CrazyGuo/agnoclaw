# Core 系列 15： Runtime 运行时合约 —— 安全护栏

> 目标：小朋友也能看懂！用一个"安全检查站"的比喻来讲清楚，agnoclaw 的运行时合约是如何在 AI 执行过程中进行安全检查的。

---

## 一、"安全检查站"比喻

想象 AI 执行过程是一个**机场安检通道**：
- **PolicyEngine** — 安检规则制定者
- **RuntimeGuardrails** — 具体的安检仪器（检查行李、检查网络）
- **PermissionController** — 登机口检票员（检查是否有权限做某事）
- **PreRunHook / PostRunHook** — 登机前/登机后的检查

每次 AI 要做一件事，都要经过安检：
- **before_tool_call** — 安检扫描
- **after_tool_call** — 安检后复核

---

## 二、Runtime 模块概览

文件：`src/agnoclaw/runtime/`

```
runtime/
├── __init__.py     # 导出所有公开接口
├── hooks.py        # 钩子合约（RunInput, ToolCallRequest 等）
├── policy.py       # 策略引擎（PolicyEngine, PolicyDecision）
├── events.py       # 事件系统（EventSink, HarnessEvent）
├── guardrails.py   # 安全护栏（RuntimeGuardrails）
├── permissions.py  # 权限控制（PermissionMode, PermissionController）
├── context.py      # 执行上下文（ExecutionContext）
└── errors.py      # 错误类型（HarnessError）
```

---

## 三、hooks.py —— 数据信封

文件：`src/agnoclaw/runtime/hooks.py`

### 3.1 RunInput —— 运行输入

```python
@dataclass
class RunInput:
    """Normalized run input passed through policy/hooks."""
    run_id: str           # 每次运行的唯一ID
    message: str          # 用户输入的消息
    skill: str | None     # 激活的技能（如果有）
    stream: bool          # 是否流式输出
    stream_events: bool   # 是否发送流事件
    metadata: dict[str, Any] = {}  # 附加数据
```

### 3.2 ToolCallRequest —— 工具调用请求

```python
@dataclass
class ToolCallRequest:
    """Tool invocation request payload."""
    run_id: str
    tool_name: str              # 工具名称（如 "bash", "read_file"）
    arguments: dict[str, Any]   # 工具参数（如 {"command": "ls -la"}）
    metadata: dict[str, Any] = {}
```

### 3.3 ToolCallResult —— 工具调用结果

```python
@dataclass
class ToolCallResult:
    """Tool invocation result payload."""
    run_id: str
    tool_name: str
    arguments: dict[str, Any]
    output: Any = None           # 工具输出
    error: str | None = None      # 错误（如果有）
    metadata: dict[str, Any] = {}
```

### 3.4 钩子协议

```python
@runtime_checkable
class PreRunHook(Protocol):
    """Pre-run hook protocol."""
    def __call__(self, run_input: RunInput, context) -> RunInput | None | Awaitable[RunInput | None]:
        ...

@runtime_checkable
class PostRunHook(Protocol):
    """Post-run hook protocol."""
    def __call__(
        self,
        run_input: RunInput,
        result: RunResultEnvelope,
        context,
    ) -> RunResultEnvelope | None | Awaitable[RunResultEnvelope | None]:
        ...
```

---

## 四、policy.py —— 策略引擎

### 4.1 PolicyAction —— 行动枚举

```python
class PolicyAction(str, Enum):
    ALLOW = "ALLOW"                     # 允许
    DENY = "DENY"                       # 拒绝
    ALLOW_WITH_REDACTION = "ALLOW_WITH_REDACTION"  # 允许但要删除某些内容
    ALLOW_WITH_CONSTRAINTS = "ALLOW_WITH_CONSTRAINTS"  # 允许但有限制
```

### 4.2 PolicyDecision —— 决策结果

```python
@dataclass(frozen=True)
class PolicyDecision:
    action: PolicyAction                    # 行动
    reason_code: str                        # 原因代码
    message: str = ""                       # 消息
    constraints: dict[str, Any] = {}      # 约束
    redactions: tuple[RedactionRule, ...] = ()  # 要删除的内容

    @classmethod
    def allow(cls) -> "PolicyDecision":
        return cls(action=PolicyAction.ALLOW, reason_code="ALLOW_DEFAULT")

    @classmethod
    def deny(cls, *, reason_code: str, message: str) -> "PolicyDecision":
        return cls(action=PolicyAction.DENY, reason_code=reason_code, message=message)
```

### 4.3 PolicyEngine 协议

```python
@runtime_checkable
class PolicyEngine(Protocol):
    """Policy checks over run lifecycle checkpoints."""

    def before_run(self, run_input: RunInput, context) -> PolicyDecision | Awaitable[PolicyDecision]:
        ...

    def before_prompt_send(self, prompt: PromptEnvelope, context) -> PolicyDecision | Awaitable[PolicyDecision]:
        ...

    def before_skill_load(self, request: SkillLoadRequest, context) -> PolicyDecision | Awaitable[PolicyDecision]:
        ...

    def before_tool_call(self, request: ToolCallRequest, context) -> PolicyDecision | Awaitable[PolicyDecision]:
        ...

    def after_tool_call(self, result: ToolCallResult, context) -> PolicyDecision | Awaitable[PolicyDecision]:
        ...
```

### 4.4 AllowAllPolicyEngine —— 默认策略

```python
class AllowAllPolicyEngine:
    """Default policy behavior for local/standalone mode."""

    def before_run(self, run_input: RunInput, context) -> PolicyDecision:
        return PolicyDecision.allow()  # 直接放行

    def before_prompt_send(self, prompt: PromptEnvelope, context) -> PolicyDecision:
        return PolicyDecision.allow()

    def before_skill_load(self, request: SkillLoadRequest, context) -> PolicyDecision:
        return PolicyDecision.allow()

    def before_tool_call(self, request: ToolCallRequest, context) -> PolicyDecision:
        return PolicyDecision.allow()

    def after_tool_call(self, result: ToolCallResult, context) -> PolicyDecision:
        return PolicyDecision.allow()
```

---

## 五、guardrails.py —— 安全护栏

### 5.1 GuardrailViolation —— 违规记录

```python
@dataclass(frozen=True)
class GuardrailViolation:
    """A single guardrail violation."""
    code: str           # 违规代码（如 "PATH_BLOCKED_ROOT"）
    message: str        # 违规消息
    details: dict[str, Any] = {}  # 详细信息
```

### 5.2 RuntimeGuardrails —— 运行时护栏

```python
class RuntimeGuardrails:
    """Path and network guardrail evaluator for tool calls."""

    def __init__(
        self,
        *,
        workspace_dir: str | Path,
        enabled: bool = True,
        path_enabled: bool = True,
        path_allowed_roots: Iterable[str] | None = None,
        path_blocked_roots: Iterable[str] | None = None,
        network_enabled: bool = True,
        network_enforce_https: bool = True,
        network_allowed_hosts: Iterable[str] | None = None,
        network_blocked_hosts: Iterable[str] | None = None,
        network_block_private_hosts: bool = True,
        network_block_in_bash: bool = True,
    ) -> None:
        ...
```

### 5.3 检查流程

```python
def check(self, request: ToolCallRequest) -> tuple[GuardrailViolation, ...]:
    """Evaluate guardrails for a tool call request."""
    if not self.enabled:
        return ()  # 护栏禁用，不检查

    violations: list[GuardrailViolation] = []

    # 1. 路径约束检查
    if self.path_enabled:
        violations.extend(self._check_path_constraints(request))

    # 2. 网络约束检查
    violations.extend(self._check_network_constraints(request))

    return tuple(violations)
```

### 5.4 路径约束检查

```python
def _check_path_constraints(self, request: ToolCallRequest) -> list[GuardrailViolation]:
    violations: list[GuardrailViolation] = []

    # 从参数中提取路径
    for arg_key, raw_path in self._extract_path_candidates(request.arguments):
        resolved = self._resolve_path(raw_path)

        # 检查是否在禁止的根目录下
        blocked_root = self._first_matching_root(resolved, self.path_blocked_roots)
        if blocked_root is not None:
            violations.append(GuardrailViolation(
                code="PATH_BLOCKED_ROOT",
                message=f"Tool '{request.tool_name}' path is under blocked root: {blocked_root}",
                ...
            ))
            continue

        # 检查是否在允许的根目录下
        if self.path_allowed_roots and self._first_matching_root(resolved, self.path_allowed_roots) is None:
            violations.append(GuardrailViolation(
                code="PATH_OUTSIDE_ALLOWED_ROOTS",
                message=f"Tool '{request.tool_name}' path is outside allowed roots",
                ...
            ))

    return violations
```

### 5.5 网络约束检查

```python
def _check_network_constraints(self, request: ToolCallRequest) -> list[GuardrailViolation]:
    violations: list[GuardrailViolation] = []
    tool_name = request.tool_name
    arguments = request.arguments

    # 1. 工具被禁用
    if (tool_name in _NETWORK_TOOL_NAMES or tool_name in _BROWSER_TOOL_NAMES) and not self.network_enabled:
        violations.append(GuardrailViolation(
            code="NETWORK_DISABLED",
            message=f"Tool '{tool_name}' is blocked because network is disabled",
            ...
        ))

    # 2. web_fetch / browser_navigate 的 URL 检查
    if tool_name == "web_fetch":
        url = arguments.get("url")
        if isinstance(url, str):
            violations.extend(self._validate_url(url=url, tool_name=tool_name, arg_key="url"))

    # 3. bash 命令中的网络活动检测
    if tool_name in {"bash", "bash_start"} and self.network_block_in_bash:
        command = arguments.get("command")
        if isinstance(command, str):
            # 检测是否有网络命令或 URL
            command_has_network = bool(
                _BASH_NETWORK_COMMAND_RE.search(command) or _URL_RE.search(command)
            )
            if command_has_network and not self.network_enabled:
                violations.append(...)
            for url in _URL_RE.findall(command):
                violations.extend(self._validate_url(url=url, tool_name=tool_name, arg_key="command"))

    return violations
```

### 5.6 URL 验证

```python
def _validate_url(self, *, url: str, tool_name: str, arg_key: str) -> list[GuardrailViolation]:
    violations: list[GuardrailViolation] = []
    parsed = urlparse(url.strip())
    scheme = parsed.scheme or ""
    host = parsed.hostname or ""

    # 1. HTTPS 强制
    if self.network_enforce_https and scheme and scheme != "https":
        violations.append(GuardrailViolation(
            code="NETWORK_HTTPS_REQUIRED",
            message=f"Only https URLs are allowed, got '{scheme}'",
            ...
        ))

    # 2. 主机名无效
    if not host:
        violations.append(...)

    # 3. 在黑名单中
    if self.network_blocked_hosts and self._host_in_set(host, self.network_blocked_hosts):
        violations.append(...)

    # 4. 不在白名单中
    if self.network_allowed_hosts and not self._host_in_set(host, self.network_allowed_hosts):
        violations.append(...)

    # 5. 私有主机（localhost, 127.0.0.1 等）
    if self.network_block_private_hosts and self._is_private_host(host):
        violations.append(...)

    return violations
```

### 5.7 私有主机检测

```python
@staticmethod
def _is_private_host(host: str) -> bool:
    normalized = host.lower().strip(".")

    # localhost 或 .local 域名
    if normalized in {"localhost"} or normalized.endswith(".local"):
        return True

    try:
        ip = ip_address(normalized)
    except ValueError:
        return False

    return (
        ip.is_private
        or ip.is_loopback      # 127.x.x.x
        or ip.is_link_local    # 169.254.x.x
        or ip.is_reserved
        or ip.is_multicast
    )
```

---

## 六、permissions.py —— 权限控制

### 6.1 PermissionMode —— 权限模式

```python
class PermissionMode(str, Enum):
    """Supported runtime permission modes."""
    BYPASS = "bypass"         # 绕过（不检查）
    DEFAULT = "default"       # 默认（读允许，写需要审批）
    ACCEPT_EDITS = "accept_edits"  # 接受编辑（自动允许文件编辑）
    PLAN = "plan"             # 计划模式（只读）
    DONT_ASK = "dont_ask"     # 不要问（拒绝所有需要审批的操作）
```

### 6.2 工具分类

```python
READ_ONLY_TOOLS = frozenset({
    "read_file", "glob_files", "grep_files", "list_dir",
    "web_search", "web_fetch", "list_todos", "read_progress",
    "read_features", "bash_output",
})

FILE_EDIT_TOOLS = frozenset({"write_file", "edit_file", "multi_edit_file"})
EXEC_TOOLS = frozenset({"bash", "bash_start", "bash_kill"})
SUBAGENT_TOOLS = frozenset({"spawn_subagent"})


def classify_tool(tool_name: str) -> tuple[str, bool]:
    """Return (category, is_read_only) for a tool name."""
    if tool_name in FILE_EDIT_TOOLS:
        return ("file_edit", False)
    if tool_name in EXEC_TOOLS:
        return ("exec", False)
    if tool_name in SUBAGENT_TOOLS:
        return ("subagent", False)
    if tool_name in READ_ONLY_TOOLS:
        return ("read", True)
    ...
```

### 6.3 PermissionController —— 权限控制器

```python
class PermissionController:
    def __init__(
        self,
        *,
        mode: str | PermissionMode = PermissionMode.BYPASS,
        approver: PermissionApprover | None = None,
        require_approver: bool = False,
        preapproved_tools: tuple[str, ...] = (),
        preapproved_categories: tuple[str, ...] = (),
    ) -> None:
        ...

    def check_tool_call(self, request: ToolCallRequest, context, *, resolve_sync_value) -> PolicyDecision:
        """Evaluate tool call permissions based on the active mode."""
        category, is_read_only = classify_tool(request.tool_name)
        mode = self.mode

        # BYPASS：直接放行
        if mode == PermissionMode.BYPASS:
            return PolicyDecision(...)

        # PLAN：只读
        if mode == PermissionMode.PLAN:
            if is_read_only:
                return PolicyDecision(action=PolicyAction.ALLOW, ...)
            return PolicyDecision.deny(...)

        # 预批准工具/类别
        if self._is_preapproved(request, category, context):
            return PolicyDecision(...)

        # DONT_ASK：拒绝
        if mode == PermissionMode.DONT_ASK:
            return PolicyDecision.deny(...)

        # ACCEPT_EDITS：自动允许文件编辑
        if mode == PermissionMode.ACCEPT_EDITS and category == "file_edit":
            return PolicyDecision(...)

        # DEFAULT：读允许
        if mode == PermissionMode.DEFAULT and category == "read":
            return PolicyDecision(...)

        # 需要审批
        if self.approver is None:
            if self.require_approver:
                return PolicyDecision.deny(...)
            return PolicyDecision(action=PolicyAction.ALLOW, ...)

        # 调用审批者
        allowed = resolve_sync_value(self.approver.approve(...))
        if bool(allowed):
            return PolicyDecision(...)
        return PolicyDecision.deny(...)
```

---

## 七、context.py —— 执行上下文

### 7.1 ExecutionContext —— 执行上下文

```python
@dataclass(frozen=True)
class ExecutionContext:
    """Frozen execution context passed through all runtime contracts."""
    user_id: str | None
    session_id: str | None
    workspace_id: str | None
    tenant_id: str | None
    org_id: str | None
    team_id: str | None
    roles: tuple[str, ...] = ()
    scopes: tuple[str, ...] = ()
    request_id: str | None
    trace_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **kwargs) -> "ExecutionContext":
        """Return new context with merged metadata."""
        return replace(self, metadata={**self.metadata, **kwargs})

    @classmethod
    def create(cls, **kwargs) -> "ExecutionContext":
        """Factory with normalized sequences."""
        ...
```

---

## 八、events.py —— 事件系统

### 8.1 EventSink —— 事件接收器

```python
class EventSink(Protocol):
    """Event sink protocol for observability."""
    def emit(self, event: HarnessEvent) -> None:
        ...
```

### 8.2 实现

```python
class NullEventSink:
    """Do-nothing event sink for environments that don't need observability."""
    def emit(self, event: HarnessEvent) -> None:
        pass

class InMemoryEventSink:
    """In-memory event sink for testing and debugging."""
    def __init__(self):
        self._events: list[HarnessEvent] = []

    def emit(self, event: HarnessEvent) -> None:
        self._events.append(event)

    def get_events(self) -> list[HarnessEvent]:
        return list(self._events)
```

---

## 九、完整安全检查流程

```
用户输入 → AgentHarness.run()
    │
    ▼
PolicyEngine.before_run()
    │
    ▼
组装系统提示词（SystemPromptBuilder.build()）
    │
    ▼
PolicyEngine.before_prompt_send()
    │
    ▼
AI 模型处理
    │
    ▼
工具调用前
    │
    ├─ RuntimeGuardrails.check(request)  → 路径/网络检查
    │
    ├─ PermissionController.check_tool_call()  → 权限检查
    │
    └─ PolicyEngine.before_tool_call()
            │
            ▼
        执行工具（bash, read_file, etc.）
            │
            ▼
        PolicyEngine.after_tool_call()
            │
            ▼
        工具结果返回
    │
    ▼
最终回复返回
    │
    ▼
PolicyEngine.after_run()
```

---

## 十、思考题

1. `PolicyEngine` 和 `RuntimeGuardrails` 有什么区别？
2. 如果 `network_block_private_hosts = True`，AI 能访问 `http://localhost:8080` 吗？
3. `PermissionMode.PLAN` 和 `PermissionMode.DONT_ASK` 有什么区别？

---

> 下一篇：《Core 系列 16： Memory 记忆系统 —— 长期学习》——深入解析 LearningMachine 和记忆层级