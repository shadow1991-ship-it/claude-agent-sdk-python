# Workflow

```bash
# Lint and style (fix automatically)
python -m ruff check src/ tests/ --fix
python -m ruff format src/ tests/

# Typecheck (src/ only — strict mypy, Python 3.10 target)
python -m mypy src/

# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_client.py

# Install with all dev dependencies
pip install -e ".[dev]"

# Install example dependencies (Redis, S3, Postgres session store tests)
pip install -e ".[dev,examples]"
```

# Codebase Structure

```
src/claude_agent_sdk/
├── __init__.py              # Public API surface + tool()/create_sdk_mcp_server() + __all__
├── client.py                # ClaudeSDKClient — bidirectional streaming sessions
├── query.py                 # query() — one-shot async generator
├── types.py                 # All public type definitions (dataclasses + TypedDicts)
├── _errors.py               # Exception hierarchy
├── _version.py              # Package version
├── _cli_version.py          # Minimum required Claude Code CLI version
├── py.typed                 # PEP 561 marker
├── _bundled/                # Bundled CLI assets (gitignored contents)
├── testing/
│   ├── __init__.py          # Testing utilities public API
│   └── session_store_conformance.py  # Shared conformance tests for SessionStore adapters
└── _internal/
    ├── client.py            # InternalClient — wires query() to transport
    ├── query.py             # Query — control protocol, hooks, MCP, permission callbacks
    ├── message_parser.py    # parse_message() — CLI JSON → typed Message objects
    ├── session_mutations.py # rename/tag/delete/fork session helpers
    ├── session_resume.py    # Session store materialization for resume
    ├── session_store.py     # InMemorySessionStore + project_key_for_directory
    ├── session_store_validation.py  # Validates SessionStore option combinations
    ├── sessions.py          # list_sessions/get_session_messages/list_subagents etc.
    ├── transcript_mirror_batcher.py # Batches transcript lines → SessionStore.append()
    └── transport/
        ├── __init__.py      # Transport abstract base class
        └── subprocess_cli.py  # SubprocessCLITransport — spawns claude CLI subprocess
```

# Key APIs

## `query()` — one-shot async generator
```python
async for message in query(prompt="...", options=ClaudeAgentOptions(...)):
    ...
```
Use for stateless, fire-and-forget automation. Cannot send follow-ups or interrupts.

## `ClaudeSDKClient` — interactive bidirectional client
```python
async with ClaudeSDKClient(options) as client:
    await client.query("...")
    async for msg in client.receive_response():   # stops at ResultMessage
        ...
    await client.interrupt()
    await client.set_permission_mode("acceptEdits")
    await client.set_model("claude-sonnet-4-6")
    status = await client.get_mcp_status()
    usage = await client.get_context_usage()
    await client.reconnect_mcp_server("my-server")
    await client.toggle_mcp_server("my-server", enabled=False)
    await client.stop_task(task_id)
    await client.rewind_files(user_message_id)    # requires enable_file_checkpointing=True
```

## `ClaudeAgentOptions` — main configuration dataclass
Key fields:
- `permission_mode`: `"default" | "acceptEdits" | "plan" | "bypassPermissions" | "dontAsk" | "auto"`
- `allowed_tools` / `disallowed_tools`: tool filter lists
- `mcp_servers`: `dict[str, McpServerConfig]` (stdio, sse, http, or sdk types)
- `can_use_tool`: `CanUseTool` async callback for programmatic permission control
- `hooks`: `dict[HookEvent, list[HookMatcher]]` — intercept tool use, prompts, etc.
- `session_store`: `SessionStore` — mirror transcripts to external storage
- `resume` / `continue_conversation` / `fork_session`: session continuity
- `thinking`: `ThinkingConfig` — extended thinking control
- `output_format`: structured output schema
- `agents`: `dict[str, AgentDefinition]` — custom sub-agent definitions
- `skills`: `list[str] | "all" | None` — skill filter
- `sandbox`: `SandboxSettings` — bash command isolation

## In-process MCP servers
```python
@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": f"{args['a'] + args['b']}"}]}

server = create_sdk_mcp_server("calc", tools=[add])
options = ClaudeAgentOptions(mcp_servers={"calc": server})
```

## Session management
```python
from claude_agent_sdk import (
    list_sessions, get_session_info, get_session_messages,
    list_subagents, get_subagent_messages,
    rename_session, tag_session, delete_session, fork_session,
    # SessionStore-backed async variants:
    list_sessions_from_store, rename_session_via_store, ...
)
```

## `SessionStore` protocol
Implement `append(key, entries)` and `load(key)` to mirror transcripts externally.
Optional: `list_sessions`, `delete`, `list_subkeys`.
Reference: `InMemorySessionStore` in `_internal/session_store.py`.
Conformance tests: `claude_agent_sdk.testing.SessionStoreConformanceTests`.
Examples: `examples/session_stores/{redis,postgres}_session_store.py`.

# Message Types
`Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent | RateLimitEvent`

- `AssistantMessage.content`: `list[ContentBlock]` where `ContentBlock = TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock`
- `SystemMessage` subclasses: `TaskStartedMessage`, `TaskProgressMessage`, `TaskNotificationMessage`, `MirrorErrorMessage`
- `ResultMessage`: final message with cost, usage, `is_error`, `session_id`

# Error Hierarchy
```
ClaudeSDKError
├── CLIConnectionError
│   └── CLINotFoundError
├── ProcessError          (exit_code, stderr attributes)
└── CLIJSONDecodeError    (line, original_error attributes)
```

# Hook System
Hooks intercept Claude lifecycle events. Register via `ClaudeAgentOptions.hooks`:
```python
hooks={
    "PreToolUse": [HookMatcher(matcher="Bash", hooks=[my_callback])],
}
```
Hook events: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`, `SubagentStart`, `PermissionRequest`.

Callback signature: `async (input: HookInput, tool_use_id: str | None, ctx: HookContext) -> HookJSONOutput`

**Python keyword escaping**: use `continue_` and `async_` in `SyncHookJSONOutput` / `AsyncHookJSONOutput` — the SDK converts them to `continue` / `async` when sending to the CLI.

# Conventions

## Code style
- Python 3.10+ target; use `X | Y` unions, `match` statements where appropriate
- `from __future__ import annotations` in files with forward references
- `typing_extensions` used for `TypedDict`, `NotRequired`, `Required` on 3.10
- `anyio` for async I/O (supports both asyncio and trio)
- No comments unless the WHY is non-obvious

## Type annotations
- Strict mypy (`strict = true`, `warn_return_any`, etc.) enforced on `src/` only
- Public API uses `@dataclass` for mutable config objects and `TypedDict` for wire-format/protocol types
- Wire-format TypedDicts use camelCase field names (matching CLI JSON); Python dataclasses use `snake_case`

## Testing
- `pytest-asyncio` with `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio`
- Tests under `tests/`; test files mirror source module names
- Live external-service tests (`test_example_*_live.py`) skip automatically without credentials
- `tests/conftest.py` contains shared fixtures

## Ruff lint rules
`E, W, F, I, N, UP, B, C4, PTH, SIM` — isort via ruff, line length 88, `E501` ignored (formatter handles it)

# CI / GitHub Actions
- `.github/workflows/test.yml` — runs pytest
- `.github/workflows/lint.yml` — ruff + mypy
- `.github/workflows/build-wheel-check.yml` — validates wheel builds
- `.github/workflows/publish.yml` / `build-and-publish.yml` — PyPI publishing
- `.github/workflows/auto-release.yml` — automated releases
- `.github/workflows/claude.yml` / `claude-code-review.yml` / `claude-issue-triage.yml` — AI-assisted workflows

# Dependencies
- **Runtime**: `anyio>=4.0.0`, `mcp>=0.1.0`, `typing_extensions>=4.0.0` (Python <3.11 only)
- **Optional `[otel]`**: `opentelemetry-api>=1.20.0` (guarded by `try/except ImportError` in transport)
- **Optional `[examples]`**: boto3, moto, redis, fakeredis, asyncpg (for session store examples/tests)
- **Dev**: pytest, pytest-asyncio, anyio[trio], pytest-cov, mypy, ruff

# Development Branch
Active development branch: `claude/add-claude-documentation-MS0Xg`
