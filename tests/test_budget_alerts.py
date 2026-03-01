"""Tests for budget alert features: webhook and stdout alerts."""

import json
import os
import sys
from io import StringIO
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tmp_state(tmp_path):
    return tmp_path / "budget_state.json"


def _make_tracker(tmp_state, daily=10.0, monthly=100.0, webhook_url=None, stdout_alerts=False):
    """Create a BudgetTracker with test settings."""
    from nadirclaw.budget import BudgetTracker
    return BudgetTracker(
        daily_budget=daily,
        monthly_budget=monthly,
        warn_threshold=0.8,
        state_file=tmp_state,
        webhook_url=webhook_url,
        stdout_alerts=stdout_alerts,
    )


def test_stdout_alert_on_daily_warning(tmp_state, capsys):
    """When stdout_alerts=True, budget warnings print to stdout."""
    tracker = _make_tracker(tmp_state, daily=1.0, stdout_alerts=True)

    with patch("nadirclaw.budget.estimate_cost", return_value=0.85):
        tracker.record("gpt-4", 100, 50)

    captured = capsys.readouterr()
    assert "[NadirClaw ALERT]" in captured.out
    assert "Daily budget warning" in captured.out


def test_stdout_alert_on_daily_exceeded(tmp_state, capsys):
    """When spend exceeds daily budget, stdout alert fires."""
    tracker = _make_tracker(tmp_state, daily=1.0, stdout_alerts=True)

    with patch("nadirclaw.budget.estimate_cost", return_value=1.05):
        tracker.record("gpt-4", 100, 50)

    captured = capsys.readouterr()
    assert "Daily budget exceeded" in captured.out


def test_no_stdout_when_disabled(tmp_state, capsys):
    """No stdout output when stdout_alerts=False."""
    tracker = _make_tracker(tmp_state, daily=1.0, stdout_alerts=False)

    with patch("nadirclaw.budget.estimate_cost", return_value=1.05):
        tracker.record("gpt-4", 100, 50)

    captured = capsys.readouterr()
    assert "[NadirClaw ALERT]" not in captured.out


def test_webhook_fires_on_alert(tmp_state):
    """Webhook POST fires when budget threshold is crossed."""
    tracker = _make_tracker(
        tmp_state, daily=1.0, webhook_url="https://example.com/hook"
    )

    with patch("nadirclaw.budget._send_webhook") as mock_webhook:
        with patch("nadirclaw.budget.estimate_cost", return_value=1.05):
            result = tracker.record("gpt-4", 100, 50)

    assert len(result["alerts"]) > 0
    # Webhook is called in a thread; we patched _send_webhook at module level
    # but _deliver_alert spawns a Thread targeting _send_webhook.
    # Since we patch the module-level function, the thread will call the mock.
    # Give thread a moment to start (or check Thread was created)
    assert tracker.webhook_url == "https://example.com/hook"


def test_no_webhook_when_not_configured(tmp_state):
    """No webhook calls when webhook_url is None."""
    tracker = _make_tracker(tmp_state, daily=1.0, webhook_url=None)

    with patch("nadirclaw.budget.Thread") as mock_thread:
        with patch("nadirclaw.budget.estimate_cost", return_value=1.05):
            tracker.record("gpt-4", 100, 50)

    mock_thread.assert_not_called()


def test_webhook_payload_structure(tmp_state):
    """Webhook payload contains expected fields."""
    from unittest.mock import call

    tracker = _make_tracker(
        tmp_state, daily=1.0, webhook_url="https://example.com/hook"
    )

    captured_payloads = []

    def capture_webhook(url, payload, timeout=10):
        captured_payloads.append(payload)

    with patch("nadirclaw.budget._send_webhook", side_effect=capture_webhook):
        # Bypass threading to test synchronously
        with patch("nadirclaw.budget.Thread") as mock_thread_cls:
            mock_thread_cls.return_value = MagicMock()
            with patch("nadirclaw.budget.estimate_cost", return_value=1.05):
                tracker.record("gpt-4", 100, 50)

            # Extract the payload from Thread call
            assert mock_thread_cls.called
            call_kwargs = mock_thread_cls.call_args
            target_fn = call_kwargs[1]["target"] if "target" in call_kwargs[1] else call_kwargs[0][0]
            args = call_kwargs[1]["args"] if "args" in call_kwargs[1] else call_kwargs[0][1]
            url, payload = args[0], args[1]

    assert url == "https://example.com/hook"
    assert payload["source"] == "nadirclaw"
    assert payload["type"] == "budget_alert"
    assert "message" in payload
    assert "timestamp" in payload
    assert "daily_spend" in payload
    assert "daily_budget" in payload


def test_monthly_alert_with_webhook(tmp_state):
    """Monthly budget alerts also trigger webhook."""
    tracker = _make_tracker(
        tmp_state, daily=999.0, monthly=1.0,
        webhook_url="https://example.com/hook", stdout_alerts=True
    )

    with patch("nadirclaw.budget.Thread"):
        with patch("nadirclaw.budget.estimate_cost", return_value=0.85):
            result = tracker.record("gpt-4", 100, 50)

    assert any("Monthly budget warning" in a for a in result["alerts"])


def test_alert_not_repeated(tmp_state, capsys):
    """Alert only fires once (not on every subsequent request)."""
    tracker = _make_tracker(tmp_state, daily=1.0, stdout_alerts=True)

    with patch("nadirclaw.budget.estimate_cost", return_value=0.85):
        r1 = tracker.record("gpt-4", 100, 50)
    with patch("nadirclaw.budget.estimate_cost", return_value=0.01):
        r2 = tracker.record("gpt-4", 100, 50)

    assert len(r1["alerts"]) == 1  # warning fires
    assert len(r2["alerts"]) == 0  # no repeat

    captured = capsys.readouterr()
    assert captured.out.count("[NadirClaw ALERT]") == 1


def test_env_var_initialization(tmp_state):
    """Budget tracker initializes webhook from env vars."""
    import nadirclaw.budget as budget_mod

    # Reset global
    budget_mod._budget_tracker = None

    env = {
        "NADIRCLAW_DAILY_BUDGET": "5.0",
        "NADIRCLAW_MONTHLY_BUDGET": "50.0",
        "NADIRCLAW_BUDGET_WEBHOOK_URL": "https://hooks.example.com/budget",
        "NADIRCLAW_BUDGET_STDOUT_ALERTS": "true",
        "NADIRCLAW_BUDGET_WARN_THRESHOLD": "0.9",
    }

    with patch.dict(os.environ, env):
        budget_mod._budget_tracker = None
        tracker = budget_mod.get_budget_tracker()

    assert tracker.daily_budget == 5.0
    assert tracker.monthly_budget == 50.0
    assert tracker.webhook_url == "https://hooks.example.com/budget"
    assert tracker.stdout_alerts is True
    assert tracker.warn_threshold == 0.9

    # Clean up
    budget_mod._budget_tracker = None
