# Changelog

All notable changes to NadirClaw will be documented in this file.

## [0.7.0] - 2026-03-02

### Added
- **`nadirclaw test` command** — probes each configured model tier with a short live request and reports latency, response, and pass/fail. Exits with code 1 on failure so it works in CI. Supports `--simple-model`, `--complex-model`, and `--timeout` overrides.
- **`classify --format json`** — new `--format text|json` flag on `nadirclaw classify`. JSON output includes `tier`, `is_complex`, `confidence`, `score`, `model`, and `prompt`. Composable with `jq`.
- **Multi-word prompt support for `classify`** — `nadirclaw classify What is 2+2?` now works without quoting. Previously only the first word was captured.

### Changed
- **`nadirclaw savings` now prefers SQLite** — mirrors `nadirclaw report`: reads from `requests.db` when available, falls back to `requests.jsonl`. Previously only JSONL was read, giving empty or stale results for users without a JSONL file.
- **`nadirclaw dashboard` now prefers SQLite** — same fix as savings; dashboard no longer shows empty data when only `requests.db` exists.
- **`SessionCache` LRU eviction is now O(1)** — replaced `List[str]` + `list.remove()` (O(n) per cache hit) with `collections.OrderedDict` + `move_to_end()` / `popitem(last=False)`, both O(1). Affects `routing.py`.
- **`ModelRateLimiter.get_status` is now thread-safe** — all reads of `_limits`, `_hits`, and `_default_rpm` are now taken inside the lock, eliminating a potential data race under concurrent requests.

### Fixed
- **`auth status` indentation** — the "no credentials" help block was over-indented (12 spaces) and the provider hint strings were misaligned. Fixed to consistent 4-space indentation.
- **Removed redundant `load_dotenv()` in `serve`** — `settings.py` already loads `~/.nadirclaw/.env` at import time; the extra bare `load_dotenv()` call in the `serve` command was a no-op that could cause confusion when debugging env resolution.

## [0.6.1] - 2026-02-28

### Fixed
- OpenClaw onboard: register nadirclaw provider without overriding the agent's primary model

## [0.6.0] - 2026-02-26

### Added
- **Configurable fallback chains** — when a model fails (429, 5xx, timeout), cascade through a configurable list of fallback models. Set `NADIRCLAW_FALLBACK_CHAIN` to customize the order.
- **Real-time spend tracking and budget alerts** — every request's cost is tracked by model, daily, and monthly. Set `NADIRCLAW_DAILY_BUDGET` and `NADIRCLAW_MONTHLY_BUDGET` for alerts at configurable thresholds. New `nadirclaw budget` CLI command and `/v1/budget` API endpoint.
- **Prompt caching** — LRU cache for identical prompts. Configurable TTL (`NADIRCLAW_CACHE_TTL`, default 5min) and max size (`NADIRCLAW_CACHE_MAX_SIZE`, default 1000). New `nadirclaw cache` CLI command and `/v1/cache` API endpoint. Toggle with `NADIRCLAW_CACHE_ENABLED`.
- **Web dashboard** — browser-based dashboard at `/dashboard` with auto-refresh. Shows routing distribution, per-model stats, cost tracking, budget status, and recent requests. Dark theme, zero dependencies.
- **Docker support** — official Dockerfile and docker-compose.yml. `docker compose up` gives you NadirClaw + Ollama for a fully local zero-cost setup.

### Changed
- Fallback logic upgraded from simple tier-swap to full chain cascade
- Request logs now include per-request cost and daily spend
- Budget state persists across restarts via `budget_state.json`

## [0.3.0] - 2025-02-14

### Added
- OAuth login for all major providers: OpenAI, Anthropic, Google Gemini, Google Antigravity
- Interactive Anthropic login — choose between setup token or API key
- Gemini OAuth PKCE flow with browser-based authorization
- Antigravity OAuth with hardcoded public client credentials (matching OpenClaw)
- Provider-specific token refresh (OpenAI, Anthropic, Gemini, Antigravity)
- Atomic credential file writes to prevent corruption
- Port-in-use error handling for OAuth callback server
- Test suite with pytest (credentials, OAuth, classifier, server)
- CONTRIBUTING.md and CHANGELOG.md

### Changed
- Version is now single source of truth in `nadirclaw/__init__.py`
- Credential file writes use atomic temp-file-and-rename pattern
- Token refresh failures return `None` instead of silently returning stale tokens
- OAuth callback server binds to `localhost` (was `127.0.0.1`)

### Fixed
- Version mismatch between `__init__.py`, `cli.py`, `server.py`, and `pyproject.toml`
- README references to `nadirclaw auth gemini-cli` (now `nadirclaw auth gemini`)
- OAuth callback server getting stuck (now uses `serve_forever()`)

## [0.2.0] - 2025-01-20

### Added
- OpenAI OAuth login via Codex CLI
- Credential storage in `~/.nadirclaw/credentials.json`
- Environment variable fallback for API keys
- `nadirclaw auth` command group

## [0.1.0] - 2025-01-10

### Added
- Initial release
- Binary complexity classifier with sentence embeddings
- Smart routing between simple and complex models
- OpenAI-compatible API (`/v1/chat/completions`)
- SSE streaming support
- Rate limit fallback between tiers
- Gemini native SDK integration
- LiteLLM support for 100+ providers
- CLI: `serve`, `classify`, `status`, `build-centroids`
- OpenClaw and Codex onboarding commands
