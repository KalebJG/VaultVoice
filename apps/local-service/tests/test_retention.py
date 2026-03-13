import unittest

from vaultvoice_service.retention import RetentionPolicy, assert_no_persistence_target


class RetentionPolicyTests(unittest.TestCase):
    def test_memory_only_allowed(self) -> None:
        policy = RetentionPolicy(mode="memory_only")
        policy.assert_memory_only()

    def test_non_memory_mode_rejected(self) -> None:
        policy = RetentionPolicy(mode="disk")
        with self.assertRaises(ValueError):
            policy.assert_memory_only()

    def test_persistence_target_always_blocked(self) -> None:
        with self.assertRaises(RuntimeError):
            assert_no_persistence_target("/tmp/transcript.txt")


if __name__ == "__main__":
    unittest.main()
