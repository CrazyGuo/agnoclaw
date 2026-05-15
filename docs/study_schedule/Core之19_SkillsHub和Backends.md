# Core 系列 19： Skills Hub & Backends —— 技能生态

> 目标：小朋友也能看懂！用一个"网上应用商店"的比喻来讲清楚，ClawHub 技能市场是如何工作的，以及技能运行时后端是如何执行安装命令的。

---

## 一、"网上应用商店"比喻

想象你要给手机安装一个 App：
- 去**应用商店**（ClawHub）搜索
- 看看 App 的介绍和评分
- **下载安装**到手机上

agnoclaw 的**技能生态**就是这样工作的：
- **ClawHub** = 应用商店（社区技能市场）
- **HubSkillInfo** = App 的简要信息
- **HubSkillDetail** = App 的详细信息
- **download()** = 下载安装

---

## 二、ClawHubClient —— 应用商店客户端

文件：`src/agnoclaw/skills/hub.py`

### 2.1 主要方法

```python
class ClawHubClient:
    def search(self, query: str, category: str = "", limit: int = 20) -> list[HubSkillInfo]:
        """搜索技能"""

    def inspect(self, name: str) -> Optional[HubSkillDetail]:
        """查看技能详情"""

    def download(self, name: str, dest_dir: str | Path, version: str = "") -> Optional[Path]:
        """下载技能到本地"""

    def categories(self) -> list[str]:
        """列出所有分类"""
```

### 2.2 HubSkillInfo —— App 简要信息

```python
@dataclass
class HubSkillInfo:
    name: str              # 技能名字（如 "code-review"）
    description: str      # 简短描述
    author: str          # 作者
    version: str         # 版本
    downloads: int       # 下载次数
    categories: list[str]  # 分类
    emoji: str           # 表情图标
```

### 2.3 HubSkillDetail —— App 详细信息

```python
@dataclass
class HubSkillDetail(HubSkillInfo):
    homepage: str              # 主页
    repository: str           # 代码仓库
    readme: str              # 说明文档
    skill_md_preview: str   # SKILL.md 预览
    dependencies: list[str]  # 依赖
    created_at: str         # 创建时间
    updated_at: str         # 更新时间
```

---

## 三、search() —— 搜索技能

```python
def search(self, query: str, category: str = "", limit: int = 20) -> list[HubSkillInfo]:
    """搜索技能"""
    params = {"q": query, "limit": limit}
    if category:
        params["category"] = category

    data = self._get("/api/search", params=params)
    if not data:
        return []

    results = data if isinstance(data, list) else data.get("results", data.get("items", []))
    return [self._parse_skill_info(item) for item in results]
```

### 使用示例

```python
client = ClawHubClient()
results = client.search("code review")
for skill in results:
    print(f"{skill.emoji} {skill.name} - {skill.description}")
```

输出：
```
🔍 code-review - Code review skill for finding bugs
🐛 debug-assistant - Debugging helper for Python
📝 documenter - Auto-generate documentation
```

---

## 四、inspect() —— 查看详情

```python
def inspect(self, name: str) -> Optional[HubSkillDetail]:
    """查看技能详情"""
    data = self._get(f"/api/v1/skills/{name}")
    if not data:
        return None
    return self._parse_skill_detail(data)
```

### 使用示例

```python
detail = client.inspect("code-review")
if detail:
    print(f"Name: {detail.name}")
    print(f"Author: {detail.author}")
    print(f"Downloads: {detail.downloads}")
    print(f"Dependencies: {', '.join(detail.dependencies)}")
```

---

## 五、download() —— 下载安装

```python
def download(self, name: str, dest_dir: str | Path, version: str = "") -> Optional[Path]:
    """下载技能 ZIP 并解压到 dest_dir/name/"""
    dest = Path(dest_dir).expanduser().resolve()

    url = f"{self._base_url}/api/download"
    response = self._client.get(url, params={"slug": name, "version": version})

    # 解压 ZIP
    skill_dir = dest / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        for file_info in zf.infolist():
            if file_info.is_dir() or file_info.filename.startswith("."):
                continue
            target = skill_dir / file_info.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(file_info.filename))

    return skill_dir
```

### 使用示例

```python
path = client.download(
    "code-review",
    dest_dir="~/.agnoclaw/workspace/skills"
)
print(f"Installed to: {path}")
```

---

## 六、缓存机制

为了减少网络请求，ClawHubClient 会缓存 API 响应：

```python
CACHE_TTL_SECONDS = 3600  # 1小时

def _read_cache(self, path: str, params: dict | None) -> dict | None:
    cache_file = self._cache_dir / f"{self._cache_key(path, params)}.json"
    if not cache_file.exists():
        return None

    raw = json.loads(cache_file.read_text())
    if time.time() - raw.get("_ts", 0) > CACHE_TTL_SECONDS:
        return None  # 过期

    return raw.get("data")
```

缓存目录：`~/.agnoclaw/cache/hub/`

---

## 七、SkillRuntimeBackend —— 技能运行时后端

文件：`src/agnoclaw/skills/backends.py`

### 7.1 协议定义

```python
class SkillRuntimeBackend(Protocol):
    """Runtime backend for skill inline commands, probes, and installs."""

    def run_inline_command(self, *, command: str, timeout_seconds: int = 10, working_dir: str | None = None) -> str:
        ...

    def has_binary(self, name: str) -> bool:
        """检查命令是否存在"""
        ...

    def has_env_var(self, name: str) -> bool:
        """检查环境变量是否存在"""
        ...

    def has_python_distribution(self, name: str) -> bool:
        """检查 Python 包是否安装"""
        ...

    def run_install(self, *, installer_type: str, package_spec: str, timeout_seconds: int = 120) -> SkillInstallResult:
        """运行安装命令"""
        ...
```

### 7.2 LocalSkillRuntimeBackend —— 本地实现

```python
class LocalSkillRuntimeBackend:
    """Host-local backend for skill execution."""

    def has_binary(self, name: str) -> bool:
        return shutil.which(name) is not None

    def has_env_var(self, name: str) -> bool:
        return bool(os.environ.get(name))

    def has_python_distribution(self, name: str) -> bool:
        from importlib.metadata import distribution
        distribution(name)
        return True

    def run_install(self, *, installer_type: str, package_spec: str, timeout_seconds: int = 120) -> SkillInstallResult:
        command = build_install_command(installer_type, package_spec)
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
        return SkillInstallResult(
            success=result.returncode == 0,
            exit_code=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )
```

### 7.3 CommandExecutorSkillRuntimeBackend —— 通过命令执行器

```python
class CommandExecutorSkillRuntimeBackend:
    """Skill runtime that probes and installs through a CommandExecutor."""

    def has_binary(self, name: str) -> bool:
        quoted = shlex.quote(name)
        return self._run_probe(f"command -v {quoted} >/dev/null 2>&1")

    def has_python_distribution(self, name: str) -> bool:
        python_bin = self._resolve_python_command()
        command = f"{python_bin} -c \"import importlib.metadata; import sys; sys.exit(0)\""
        return self._run_probe(command)
```

---

## 八、build_install_command() —— 构建安装命令

```python
def build_install_command(
    installer_type: str,
    package_spec: str,
    *,
    python_command: str | None = None,
) -> list[str] | None:
    """构建安装命令"""
    if installer_type == "uv":
        python_bin = python_command or sys.executable
        return [python_bin, "-m", "uv", "pip", "install", package_spec]

    if installer_type == "pip":
        python_bin = python_command or sys.executable
        return [python_bin, "-m", "pip", "install", "--quiet", package_spec]

    if installer_type == "brew":
        return ["brew", "install", package_spec]

    if installer_type == "npm":
        return ["npm", "install", "-g", package_spec]

    if installer_type == "go":
        return ["go", "install", package_spec]

    return None
```

| 安装类型 | 命令 |
|----------|------|
| `uv` | `python -m uv pip install <package>` |
| `pip` | `python -m pip install <package>` |
| `brew` | `brew install <package>` |
| `npm` | `npm install -g <package>` |
| `go` | `go install <package>` |

---

## 九、SkillInstallApprover —— 安装审批

```python
class SkillInstallApprover(Protocol):
    """Approval backend for skill dependency installs."""
    def approve(self, skill: Skill, pending: list[tuple[SkillInstaller, str]]) -> bool:
        ...
```

### AutoApproveSkillInstallApprover —— 自动批准

```python
class AutoApproveSkillInstallApprover:
    """Install approver that always returns True."""
    def approve(self, skill: Skill, pending: list) -> bool:
        return True
```

### InteractiveSkillInstallApprover —— 交互式批准

```python
class InteractiveSkillInstallApprover:
    """Interactive terminal approver for skill installs."""
    def approve(self, skill: Skill, pending: list[tuple[SkillInstaller, str]]) -> bool:
        print(f"\nSkill '{skill.name}' requires installations:")
        for installer, package_spec in pending:
            print(f"  {installer.type}: {package_spec}")

        answer = input("Proceed? [y/N] ").strip().lower()
        return answer in ("y", "yes")
```

---

## 十、完整使用流程

```python
# 1. 搜索技能
client = ClawHubClient()
results = client.search("code review")
skill = results[0]

# 2. 查看详情
detail = client.inspect(skill.name)
print(f"安装 {detail.name}?")
print(f"依赖: {detail.dependencies}")

# 3. 下载安装
path = client.download(skill.name, dest_dir="~/.agnoclaw/workspace/skills")
print(f"已安装到: {path}")

client.close()
```

---

## 十一、思考题

1. ClawHubClient 为什么需要缓存？缓存的好处是什么？
2. 如果安装一个技能需要安装 `pip` 包，但用户没有 `pip`，会发生什么？
3. `AutoApproveSkillInstallApprover` 和 `InteractiveSkillInstallApprover` 分别适合什么场景？

---

> 下一篇：《Core 系列 20： AsyncREPL —— 异步交互式命令行》——深入解析异步 REPL 和 Heartbeat 集成