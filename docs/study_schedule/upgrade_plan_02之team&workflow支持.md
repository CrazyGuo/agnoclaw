# TUI Agent Type Configuration — Implementation Plan

## Context

The user has two questions about the TUI command in `src/agnoclaw/cli/main.py`:

1. **Q1**: Can the agent be specified via CLI argument (e.g., `--agent-type research`)?
2. **Q2**: Can the TUI support configurable entity types beyond a single `AgentHarness` — specifically **agent**, **teams**, and potentially **workflow**?

Currently the TUI command (`tui()` at line 321) hard-codes a single `AgentHarness`:

```python
def tui(model, provider, session, workspace, debug, permission_mode):
    agent = _build_agent(model, provider, session, workspace, debug, permission_mode)
    app = AgnoClawApp(agent=agent, debug=debug)
    app.run()
```

---

## Current Architecture Analysis

### 1. AgnoClawApp (`src/agnoclaw/tui/app.py`)
- Constructor takes `agent: AgentHarness` directly
- Internally wraps with `AgentDriver` which bridges Textual event loop to AgentHarness

### 2. AgentDriver (`src/agnoclaw/tui/driver.py`)
- Tightly coupled to `AgentHarness` — calls:
  - `agent.arun()` for async streaming
  - `agent._extract_event_content()`, `agent._map_agno_event_type()`
  - `agent._stream_event_summary()`, `agent._format_tool_invocation_label()`

### 3. Teams (`src/agnoclaw/teams.py`)
- `research_team()`, `code_team()`, `data_team()` return **Agno `Team`** objects
- Team API differs: `team.run()` / `team.run_async()` not `agent.arun()`
- Teams have `show_members_responses=True` which shows multi-agent output

### 4. No Workflow Abstraction
- No `workflow` concept exists in codebase currently

---

## User Decisions

1. **Workflow**: Skip for now, focus on team support
2. **Team TUI UX**: Show all members' outputs (interleaved multi-agent collaboration)

---

## Implementation Plan (Final)

### Phase 1: Team Support for TUI

#### Step 1: Extend CLI `tui` command (`src/agnoclaw/cli/main.py`)

Add `--type` and `--team-type` options:

```python
@cli.command()
@MODEL_OPT
@PROVIDER_OPT
@SESSION_OPT
@WORKSPACE_OPT
@DEBUG_OPT
@PERMISSION_MODE_OPT
@click.option("--type", "-t", default="agent",
              type=click.Choice(["agent", "team"], case_sensitive=False),
              help="Entity type: agent (single) or team (multi-agent)")
@click.option("--team-type", default="research",
              help="Team preset when --type=team: research, code, data")
def tui(model, provider, session, workspace, debug, permission_mode, type, team_type):
```

Add entity factory function:

```python
def _build_entity(
    type: str,
    team_type: str,
    model, provider, session, workspace, debug, permission_mode
):
    if type == "team":
        from agnoclaw.teams import research_team, code_team, data_team
        team_map = {"research": research_team, "code": code_team, "data": data_team}
        team_fn = team_map.get(team_type, research_team)
        return team_fn(model_id=model, provider=provider)
    # Default: return AgentHarness
    return _build_agent(model, provider, session, workspace, debug, permission_mode)
```

Update `tui()` body to use factory and pass `Team` to app:

```python
entity = _build_entity(type, team_type, model, provider, session, workspace, debug, permission_mode)
app = AgnoClawApp(entity=entity, entity_type=type, debug=debug)
```

#### Step 2: Create base protocol for entity drivers (`src/agnoclaw/tui/driver.py`)

```python
from typing import Protocol, AsyncIterator

class EntityDriver(Protocol):
    async def send_message(self, text: str, skill: str | None = None) -> AsyncIterator[StreamEvent]: ...
    def clear_session(self) -> str | None: ...
```

#### Step 3: Add `TeamDriver` class (`src/agnoclaw/tui/driver.py`)

- Similar to `AgentDriver` but wraps Agno `Team` instead of `AgentHarness`
- Calls `team.run_async(user_message=...)` instead of `agent.arun()`
- Maps `TeamMode.coordinate` output events to `StreamChunk` messages
- Shows `show_members_responses=True` — all member outputs streamed

#### Step 4: Update `AgnoClawApp` to accept entity + entity_type (`src/agnoclaw/tui/app.py`)

Modify constructor signature:

```python
def __init__(
    self,
    *,
    entity: AgentHarness | Team,  # Accept either type
    entity_type: str = "agent",  # "agent" or "team"
    debug: bool = False,
) -> None:
    if entity_type == "team":
        self._driver = TeamDriver(app=self, team=entity)
    else:
        self._driver = AgentDriver(app=self, agent=entity)
```

#### Step 5: Handle chat history / session differently

- `AgentHarness` has `session_id` for persistent chat history
- `Team` also supports `session_id` but team sessions store multi-agent history differently
- AgentDriver's `clear_session()` calls `agent.clear_session_context()`
- TeamDriver's `clear_session()` should call `team.clear_history()` or similar Agno API

---

## Files to Modify

| File | Change |
|------|--------|
| `src/agnoclaw/cli/main.py` | Add `--type`/`--team-type` options; add `_build_entity()` factory |
| `src/agnoclaw/tui/driver.py` | Add `TeamDriver` class (mirrors AgentDriver pattern) |
| `src/agnoclaw/tui/app.py` | Update `AgnoClawApp.__init__` to accept `Team` and `entity_type` |

Existing files to reuse:
- `src/agnoclaw/teams.py` — `research_team()`, `code_team()`, `data_team()` already exist
- `src/agnoclaw/tui/events.py` — existing StreamChunk, ToolCallStarted, etc.

---

## Verification

Test scenarios:

```bash
# Single agent (default, backward compatible)
uv run agnoclaw tui

# Team mode - research
uv run agnoclaw tui --type team --team-type research

# Team mode - code
uv run agnoclaw tui --type team --team-type code

# Team mode - data
uv run agnoclaw tui --type team --team-type data

# With model/provider overrides
uv run agnoclaw tui --type team --team-type code --model claude-sonnet-4-6 --provider anthropic
```