import asyncio
import time
import unittest

from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.core.errors import CircuitBreakerOpenError


class TestCircuitBreaker(unittest.IsolatedAsyncioTestCase):
    """Test suite covering async CircuitBreaker lifecycle, metrics, and state transitions."""

    async def test_initial_state_is_closed(self):
        cb = CircuitBreaker(name="test_provider", failure_threshold=3, recovery_timeout=0.2)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())
        self.assertEqual(cb.get_remaining_cooldown(), 0.0)

    async def test_trips_to_open_after_reaching_threshold(self):
        cb = CircuitBreaker(name="test_provider", failure_threshold=3, recovery_timeout=0.2)

        cb.record_failure(ValueError("timeout 1"))
        self.assertEqual(cb.state, CircuitState.CLOSED)

        cb.record_failure(ValueError("timeout 2"))
        self.assertEqual(cb.state, CircuitState.CLOSED)

        # 3rd failure reaches threshold
        cb.record_failure(ValueError("timeout 3"))
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())
        self.assertGreater(cb.get_remaining_cooldown(), 0.0)

    async def test_execute_raises_open_error_when_tripped(self):
        cb = CircuitBreaker(name="test_provider", failure_threshold=2, recovery_timeout=0.5)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

        async def dummy_coro():
            return "ok"

        with self.assertRaises(CircuitBreakerOpenError) as ctx:
            await cb.execute(dummy_coro)

        self.assertEqual(ctx.exception.code, "CIRCUIT_BREAKER_OPEN")
        self.assertIn("OPEN", str(ctx.exception))

    async def test_transitions_to_half_open_after_cooldown_and_recovers(self):
        cb = CircuitBreaker(name="test_provider", failure_threshold=2, recovery_timeout=0.1)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

        # Wait for cooldown to elapse
        await asyncio.sleep(0.12)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.can_execute())

        # Successful trial closes circuit
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

    async def test_half_open_failure_re_trips_to_open(self):
        cb = CircuitBreaker(name="test_provider", failure_threshold=2, recovery_timeout=0.1)

        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

        await asyncio.sleep(0.12)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Failure during canary probe immediately re-opens circuit
        cb.record_failure(RuntimeError("still failing"))
        self.assertEqual(cb.state, CircuitState.OPEN)

    async def test_metrics_telemetry(self):
        cb = CircuitBreaker(name="test_metrics", failure_threshold=3, recovery_timeout=10.0)

        async def success_task():
            return 42

        val = await cb.execute(success_task)
        self.assertEqual(val, 42)

        cb.record_failure(Exception("simulated"))
        metrics = cb.get_metrics()

        self.assertEqual(metrics["name"], "test_metrics")
        self.assertEqual(metrics["state"], "CLOSED")
        self.assertEqual(metrics["total_calls"], 1)
        self.assertEqual(metrics["total_successes"], 1)
        self.assertEqual(metrics["total_failures"], 1)
        self.assertEqual(metrics["consecutive_failures"], 1)
        self.assertIsNotNone(metrics["last_failure_time"])

    async def test_manual_reset(self):
        cb = CircuitBreaker(name="test_reset", failure_threshold=1, recovery_timeout=10.0)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

        cb.reset()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())


if __name__ == "__main__":
    unittest.main()
