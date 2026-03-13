import unittest

from vaultvoice_service.logging_utils import assert_safe_log_fields


class LoggingUtilsTests(unittest.TestCase):
    def test_safe_fields_allowed(self) -> None:
        assert_safe_log_fields({"event": "health_check", "latency_ms": 120})

    def test_forbidden_fields_blocked(self) -> None:
        with self.assertRaises(ValueError):
            assert_safe_log_fields({"event": "partial", "transcript": "secret"})


if __name__ == "__main__":
    unittest.main()
