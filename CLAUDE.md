# Workflow

```bash
# Lint and fix automatically
python -m ruff check src/ tests/ --fix
python -m ruff format src/ tests/

# Typecheck (src/ only — strict mypy)
python -m mypy src/

# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_client.py

# Run e2e tests (requires Claude Code CLI installed)
python -m pytest e2e-tests/
```

# Codebase Structure

```
src/claude_agent_sdk/
├── __init__.py              # Public API exports + __all__
├── client.py                # ClaudeSDKClient (bidirectional streaming)
├── query.py                 # query() one-shot async iterator
├── types.py                 # All public type definitions (~1100 lines)
├── _errors.py               # Exception hierarchy
├── _cli_version.py          # CLI version tracking
├── _version.py              # SDK version (currently 0.1.63)
├── _bundled/                # Bundled CLI binary (platform wheels)
├── testing/
│   └── session_store_conformance.py  # Conformance test suite for SessionStore adapters
└── _internal/
    ├── client.py            # InternalClient — orchestrates query processing
    ├── query.py             # Query class — bidirectional control protocol
    ├── message_parser.py    # Raw JSON → typed Message objects
    ├── sessions.py          # Session listing + metadata extraction
    ├── session_mutations.py # Session fork/rename/tag/delete
    ├── session_resume.py    # Session resumption from SessionStore
    ├── session_store.py     # InMemorySessionStore reference implementation
    ├── session_store_validation.py
    ├── transcript_mirror_batcher.py  # Batched SessionStore writes
    └── transport/
        ├── __init__.py      # Transport abstract base class
        └── subprocess_cli.py # CLI subprocess management

tests/                       # Unit tests (pytest-asyncio, auto mode)
e2e-tests/                   # Live tests against actual Claude Code CLI
examples/                    # Working usage examples
scripts/                     # Build and release automation
```

# Architecture

The SDK has three layers:

1. **Public API** (`query.py`, `client.py`) — Two interaction modes:
   - `query()`: async iterator, fire-and-forget or unidirectional streaming
   - `ClaudeSDKClient`: persistent session with `interrupt()`, `get_mcp_status()`, etc.

2. **Internal orchestration** (`_internal/client.py`, `_internal/query.py`) — `InternalClient` drives `Query`, which implements the bidirectional JSON control protocol with the CLI: hook callbacks, tool permission checks, MCP server integration, and message routing.

3. **Transport** (`_internal/transport/`) — `SubprocessCLITransport` manages the Claude Code CLI subprocess (auto-discovery: bundled → PATH → known locations). Custom transports can be injected for testing.

# Key Types (`types.py`)

## ClaudeAgentOptions
The main configuration TypedDict passed to `query()` / `ClaudeSDKClient`:
- `prompt`, `system_prompt`, `allowed_tools`, `disallowed_tools`
- `permission_mode`, `can_use_tool` (tool permission callback)
- `cwd`, `env`
- `mcp_servers`, `hooks`, `agents`, `skills`
- `session_store`, `resume`, `continue_` (note trailing underscore — Python keyword workaround)
- `max_turns`, `task_budget`, `sandbox_settings`, `settings`

## Message Types (dataclasses)
- `UserMessage`, `AssistantMessage`, `SystemMessage`
- `TaskStartedMessage`, `TaskProgressMessage`, `TaskNotificationMessage`
- `ResultMessage` — final result with cost/usage stats
- `MirrorErrorMessage` — SessionStore failure notification
- `StreamEvent` — partial assistant output during streaming

## Content Blocks
`TextBlock`, `ThinkingBlock`, `ToolUseBlock`, `ToolResultBlock`

## Hook Types
- `PreToolUseHookInput`, `PostToolUseHookInput`, `PostToolUseFailureHookInput`
- `HookCallback` — async callable for hook events
- `HookJSONOutput` — discriminated union (async/sync variants)
- `PermissionResult` — union of `Allow` / `Deny`
- `CanUseTool` — tool permission callback type

## SessionStore Protocol
`SessionStore` is a `Protocol` — implement `append`, `load`, `list_sessions`, `delete`, `list_subkeys` to create a custom adapter. Use `testing/session_store_conformance.py` to validate adapters.

# Development Conventions

## Typing
- **Strict mypy** (`strict = true`) — all public and internal code must pass
- TypedDict for wire-format and configuration data
- Protocol classes for extensibility points (`SessionStore`, `Transport`)
- Discriminated unions for hook inputs/outputs
- Python keyword conflicts get trailing underscore: `async_`, `continue_`

## Async
- **anyio** throughout (not asyncio directly) — platform-agnostic, supports asyncio and trio
- `anyio.Lock` for write serialization, `anyio.Event` for signaling
- Streaming via `AsyncIterator` / `AsyncIterable`
- Always clean up resources in `finally` blocks

## Naming
- `_internal/` and `_errors.py` — private, not part of public API
- Public exports controlled via `__all__` in `__init__.py`
- camelCase only in wire-format dicts matching CLI JSON; Python code uses snake_case

## Error Handling
Custom exception hierarchy (all inherit from `ClaudeSDKError`):
- `CLINotFoundError` — CLI binary not found
- `CLIConnectionError` — subprocess communication failure
- `ProcessError` — non-zero exit or crash
- `CLIJSONDecodeError` — malformed JSON from CLI

## Linting (ruff)
Line length 88, target Python 3.10. Active rule sets: `E`, `W`, `F`, `I` (isort), `N` (pep8-naming), `UP` (pyupgrade), `B` (bugbear), `C4`, `PTH` (use pathlib), `SIM`.

# Testing Patterns

- `pytest-asyncio` with `asyncio_mode = "auto"` — all async tests work without decoration
- Mock `SubprocessCLITransport` with `AsyncMock` / custom `Transport` subclass to avoid spawning real CLI processes
- `tmp_path` fixture for filesystem-based tests
- `InMemorySessionStore` for session store tests; validate custom adapters with `SessionStoreConformanceTestSuite`
- Parameterized tests for message parser edge cases

# Dependencies

| Package | Purpose |
|---|---|
| `anyio>=4.0.0` | Async I/O (asyncio + trio support) |
| `mcp>=0.1.0` | Model Context Protocol |
| `typing_extensions` | Python <3.11 TypedDict backport |

Dev extras: `pytest`, `pytest-asyncio`, `anyio[trio]`, `mypy`, `ruff`, `pytest-cov`
Optional extras: `otel` (OpenTelemetry), `examples` (boto3/redis/asyncpg for example adapters)

Python 3.10–3.13 supported.

# Release Process

See `RELEASING.md`. Version is in `src/claude_agent_sdk/_version.py` and `pyproject.toml`. CI builds multi-platform wheels via `.github/workflows/build-and-publish.yml`.
