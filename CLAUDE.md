# CLAUDE.md — Claude Agent SDK (Python)

## Development Workflows

### Lint, Format, Typecheck

```bash
# Check for issues and auto-fix
python -m ruff check src/ tests/ --fix

# Format code
python -m ruff format src/ tests/

# Type checking (src/ only — strict mypy)
python -m mypy src/
```

### Testing

```bash
# Run all unit tests
python -m pytest tests/

# Run a specific test file
python -m pytest tests/test_client.py

# Run with coverage
python -m pytest tests/ --cov=src/claude_agent_sdk

# Run e2e tests (requires ANTHROPIC_API_KEY)
python -m pytest e2e-tests/
```

### Versioning & Release

The version lives in `src/claude_agent_sdk/_version.py`. Bumping it triggers the `auto-release.yml` CI workflow, which creates a release PR. Publishing to PyPI happens via `publish.yml` on merge.

---

## Codebase Structure

```
src/claude_agent_sdk/
├── __init__.py               # Public API, @tool decorator, create_sdk_mcp_server()
├── client.py                 # ClaudeSDKClient — bidirectional interactive sessions
├── query.py                  # query() — one-shot async iterator interface
├── types.py                  # All public type definitions (dataclasses, TypedDicts, Protocols)
├── _errors.py                # Exception hierarchy
├── _version.py               # Package version string
├── _internal/
│   ├── client.py             # InternalClient — orchestrates query pipeline
│   ├── query.py              # Query — control-protocol layer over Transport
│   ├── message_parser.py     # JSON → typed Message objects
│   ├── transport/
│   │   ├── __init__.py       # Transport ABC
│   │   └── subprocess_cli.py # SubprocessCLITransport (anyio-based)
│   ├── sessions.py           # list_sessions(), get_session_info(), get_session_messages()
│   ├── session_resume.py     # Session resume/fork materialisation
│   ├── session_store.py      # InMemorySessionStore reference implementation
│   ├── session_mutations.py  # rename/tag/delete/fork session operations
│   ├── session_store_validation.py
│   └── transcript_mirror_batcher.py  # Batched SessionStore.append() mirroring
└── testing/
    └── session_store_conformance.py  # Reusable conformance test suite for SessionStore
```

---

## Architecture Overview

### Message Flow

```
User code
  └─ query() / ClaudeSDKClient
        └─ InternalClient.process_query()
              └─ Query (control protocol)
                    └─ SubprocessCLITransport
                          └─ Claude Code CLI (JSON-lines over stdin/stdout)
```

### Two Public Interfaces

| | `query()` | `ClaudeSDKClient` |
|---|---|---|
| Direction | Unidirectional (receive only) | Bidirectional (send + receive) |
| Use case | One-shot prompts, scripts | Interactive sessions, multi-turn |
| Returns | `AsyncIterator[Message]` | Stateful client with `.query()` / `.receive_messages()` |

### Control Protocol (`_internal/query.py`)

The `Query` class sits between the `Transport` and user-facing code. It handles:
- Permission request/response routing (via `can_use_tool` callback)
- Hook callbacks (`PreToolUse`, `PostToolUse`, `Stop`, `PermissionRequest`)
- In-process MCP tool dispatch
- Dynamic runtime settings (`set_permission_mode()`, `set_model()`)
- Transcript mirroring to `SessionStore`

### Transport (`_internal/transport/`)

`Transport` is an abstract base class. The only concrete implementation is `SubprocessCLITransport`, which:
- Locates the CLI (bundled → system PATH → ~9 known install paths)
- Requires minimum CLI version `2.0.0`
- Uses `anyio` for cross-platform async subprocess management
- Reads JSON-line messages from stdout; writes JSON-line commands to stdin
- Default max buffer size: 1 MB

### Session Management

Sessions are stored as JSONL transcript files at:
```
~/.claude/projects/<sanitized-cwd>/<session-uuid>.jsonl
```

Path sanitisation uses a djb2 hash suffix when the path exceeds 200 characters (matching CLI behaviour).

The `SessionStore` Protocol allows external backends (Redis, S3, Postgres — see `examples/session_stores/`). Use `testing/session_store_conformance.py` to validate any custom implementation.

---

## Key Types (`types.py`)

- **`ClaudeAgentOptions`** — ~40-field dataclass configuring a session (model, system prompt, tools, hooks, MCP servers, sandbox, thinking budget, etc.)
- **`Message`** — union: `UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent | RateLimitEvent`
- **Content blocks** — `TextBlock`, `ThinkingBlock`, `ToolUseBlock`, `ToolResultBlock`
- **`SessionStore`** — Protocol with `append()`, `load()`, `list_sessions()`, `delete()`, `list_subkeys()`
- **`HookCallback`** / **`HookMatcher`** — typed hook system (discriminated union on event type)
- **`AgentDefinition`** — defines sub-agent skills, memory, and turn limits
- **`McpServerConfig`** / **`McpSdkServerConfig`** — external vs in-process MCP servers

---

## MCP Integration

### External MCP Servers
Configured via `ClaudeAgentOptions.mcp_servers` using `McpServerConfig`.

### In-Process SDK MCP Servers
Use the `@tool` decorator and `create_sdk_mcp_server()`:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions

@tool
def add(x: int, y: int) -> int:
    return x + y

options = ClaudeAgentOptions(
    mcp_servers=[create_sdk_mcp_server([add])]
)
```

Tools defined with `@tool` get JSON-schema generated automatically from type annotations.

---

## Hooks

Hooks intercept tool use events. They are set on `ClaudeAgentOptions.hooks` as a list of `(HookMatcher, HookCallback)` pairs. Event types:
- `PreToolUse` — before a tool runs; can block or modify
- `PostToolUse` — after a tool runs
- `Stop` — when the agent stops
- `PermissionRequest` — custom permission UI/logic

---

## Conventions

- **Async throughout** — all public APIs are `async`; use `anyio` (asyncio or trio compatible)
- **Strict typing** — mypy strict mode; use `TypedDict` for wire formats, dataclasses for config
- **No comments for obvious code** — only comment non-obvious invariants, workarounds, or constraints
- **Internal vs Public** — `_internal/` is private; `Transport` ABC is low-level and subject to change
- **Error types** — raise specific subclasses (`CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`) not bare exceptions
- **Tests** — `pytest-asyncio` with `asyncio_mode="auto"`; mock `SubprocessCLITransport` for unit tests
- **Examples** — `examples/` contains 16 runnable scripts covering all major features; keep them working

---

## CI/CD

| Workflow | Trigger | Purpose |
|---|---|---|
| `test.yml` | push/PR | pytest (ubuntu/macos/windows, Python 3.13) + e2e + example validation |
| `lint.yml` | push/PR | ruff + mypy + format check |
| `auto-release.yml` | version bump | Creates release PR |
| `publish.yml` | release merge | Builds platform wheels + publishes to PyPI |
| `claude-code-review.yml` | PR | Automated Claude code review |

---

## Common Tasks

**Add a new public type** → `types.py`; export from `__init__.py`; add to `__all__`

**Add a new internal module** → `_internal/`; do not expose in `__init__.py`

**Add a new example** → `examples/`; validate it runs in `test.yml`

**Add a new SessionStore backend** → implement `SessionStore` Protocol; run `session_store_conformance.py` suite against it

**Bump the version** → edit `src/claude_agent_sdk/_version.py`; CI handles the rest
