"""Tests for Prometheus metrics module."""

import importlib
import pytest

import nadirclaw.metrics as metrics_mod


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset all metric state between tests."""
    # Re-create fresh metric instances
    metrics_mod.requests_total = metrics_mod._Counter()
    metrics_mod.tokens_prompt_total = metrics_mod._Counter()
    metrics_mod.tokens_completion_total = metrics_mod._Counter()
    metrics_mod.cost_total = metrics_mod._Counter()
    metrics_mod.cache_hits_total = metrics_mod._Counter()
    metrics_mod.fallbacks_total = metrics_mod._Counter()
    metrics_mod.errors_total = metrics_mod._Counter()
    metrics_mod.latency_ms = metrics_mod._Histogram(metrics_mod.LATENCY_BUCKETS)
    yield


def test_record_basic_request():
    """record_request increments counters for a normal completion."""
    entry = {
        "type": "completion",
        "selected_model": "gpt-4o-mini",
        "tier": "simple",
        "status": "ok",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "cost": 0.0012,
        "total_latency_ms": 350,
    }
    metrics_mod.record_request(entry)

    # Check request counter
    items = dict(metrics_mod.requests_total.items())
    assert items[("gpt-4o-mini", "simple", "ok")] == 1.0

    # Check tokens
    pt_items = dict(metrics_mod.tokens_prompt_total.items())
    assert pt_items[("gpt-4o-mini",)] == 100

    ct_items = dict(metrics_mod.tokens_completion_total.items())
    assert ct_items[("gpt-4o-mini",)] == 50

    # Check cost
    cost_items = dict(metrics_mod.cost_total.items())
    assert abs(cost_items[("gpt-4o-mini",)] - 0.0012) < 1e-9


def test_record_ignores_non_completion():
    """Non-completion entries (classify, etc.) are skipped."""
    metrics_mod.record_request({"type": "classify", "selected_model": "x"})
    assert len(metrics_mod.requests_total.items()) == 0


def test_record_fallback():
    """Fallback events are counted."""
    entry = {
        "type": "completion",
        "selected_model": "gpt-4o",
        "tier": "complex",
        "status": "ok",
        "fallback_used": "claude-3-opus",
        "total_latency_ms": 500,
    }
    metrics_mod.record_request(entry)
    fb_items = dict(metrics_mod.fallbacks_total.items())
    assert fb_items[("claude-3-opus", "gpt-4o")] == 1


def test_record_error():
    """Error requests are counted in errors_total."""
    entry = {
        "type": "completion",
        "selected_model": "gpt-4o",
        "tier": "complex",
        "status": "error",
        "total_latency_ms": 100,
    }
    metrics_mod.record_request(entry)
    err_items = dict(metrics_mod.errors_total.items())
    assert err_items[("gpt-4o", "error")] == 1

    req_items = dict(metrics_mod.requests_total.items())
    assert req_items[("gpt-4o", "complex", "error")] == 1


def test_record_cache_hit():
    """Cache hits are detected from strategy field."""
    entry = {
        "type": "completion",
        "selected_model": "gpt-4o-mini",
        "tier": "simple",
        "status": "ok",
        "strategy": "eco+cache-hit",
        "total_latency_ms": 5,
    }
    metrics_mod.record_request(entry)
    total = sum(v for _, v in metrics_mod.cache_hits_total.items())
    assert total == 1


def test_latency_histogram():
    """Latency observations populate histogram buckets."""
    entry = {
        "type": "completion",
        "selected_model": "gpt-4o",
        "tier": "complex",
        "status": "ok",
        "total_latency_ms": 150,
    }
    metrics_mod.record_request(entry)

    hist_items = metrics_mod.latency_ms.items()
    assert len(hist_items) == 1
    labels, buckets, s, count = hist_items[0]
    assert labels == ("gpt-4o", "complex")
    assert count == 1
    assert abs(s - 150.0) < 0.01
    # 150ms should fall in the 250 bucket and above
    assert buckets[100] == 0  # 150 > 100
    assert buckets[250] == 1  # 150 <= 250


def test_render_metrics_format():
    """render_metrics produces valid Prometheus text."""
    entry = {
        "type": "completion",
        "selected_model": "gpt-4o-mini",
        "tier": "simple",
        "status": "ok",
        "prompt_tokens": 200,
        "completion_tokens": 100,
        "cost": 0.005,
        "total_latency_ms": 400,
    }
    metrics_mod.record_request(entry)
    output = metrics_mod.render_metrics()

    # Check expected metric families exist
    assert "# TYPE nadirclaw_requests_total counter" in output
    assert 'nadirclaw_requests_total{model="gpt-4o-mini",tier="simple",status="ok"} 1' in output
    assert 'nadirclaw_tokens_prompt_total{model="gpt-4o-mini"} 200' in output
    assert 'nadirclaw_tokens_completion_total{model="gpt-4o-mini"} 100' in output
    assert 'nadirclaw_cost_dollars_total{model="gpt-4o-mini"} 0.005000' in output
    assert "nadirclaw_uptime_seconds" in output
    assert "# TYPE nadirclaw_request_latency_ms histogram" in output
    assert 'le="+Inf"' in output


def test_render_empty_metrics():
    """render_metrics works with no data recorded."""
    output = metrics_mod.render_metrics()
    assert "nadirclaw_uptime_seconds" in output
    assert "nadirclaw_cache_hits_total 0" in output


def test_multiple_requests_accumulate():
    """Multiple requests accumulate correctly."""
    for i in range(5):
        metrics_mod.record_request({
            "type": "completion",
            "selected_model": "gpt-4o-mini",
            "tier": "simple",
            "status": "ok",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "cost": 0.001,
            "total_latency_ms": 100 + i * 50,
        })
    items = dict(metrics_mod.requests_total.items())
    assert items[("gpt-4o-mini", "simple", "ok")] == 5

    pt = dict(metrics_mod.tokens_prompt_total.items())
    assert pt[("gpt-4o-mini",)] == 50

    cost = dict(metrics_mod.cost_total.items())
    assert abs(cost[("gpt-4o-mini",)] - 0.005) < 1e-9
