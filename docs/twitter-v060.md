# Twitter Thread — NadirClaw v0.6.0

## Tweet 1
NadirClaw v0.6.0 is out.

5 features that make it a real LLM router:

- Fallback chains (models fail? cascade to the next one)
- Budget alerts (know before you blow $50/day)
- Prompt caching (stop paying for the same prompt twice)
- Web dashboard (see everything at localhost:8856/dashboard)
- Docker (one command: docker compose up)

Open source. Your keys. No middleman.

github.com/doramirdor/NadirClaw

## Tweet 2
The fallback chain is my favorite.

Before: model gets 429'd, your agent dies mid-task.

After: NadirClaw tries model B, then C, then D. Your agent never notices.

NADIRCLAW_FALLBACK_CHAIN=gpt-4.1,claude-sonnet,gemini-flash

One env var. Zero dead requests.

## Tweet 3
Budget tracking that actually works:

Set NADIRCLAW_DAILY_BUDGET=5.00

Every request logs its cost. At 80% you get a warning. At 100% you know immediately.

`nadirclaw budget` shows spend by model.

No more surprise bills.

## Tweet 4
Docker setup:

docker compose up

That's it. NadirClaw + Ollama. Fully local. Zero API costs.

Point your tools at localhost:8856 and every prompt gets routed for free.

## Tweet 5
If you're using OpenRouter, ClawRouter, or paying per-request for routing:

NadirClaw does the same thing but:
- Runs on your machine
- Uses your own API keys
- No platform risk
- No subscription
- Open source forever

pip install nadirclaw

Stars appreciated: github.com/doramirdor/NadirClaw
