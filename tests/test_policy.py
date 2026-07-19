import unittest

from prometheus_kernel.engine_types import MissionPolicyError
from prometheus_kernel.policy import ExecutionPolicy


class PolicyTests(unittest.TestCase):
    def test_disallowed_executable_is_rejected(self):
        mission = {
            "standard_test": ["curl", "example.invalid"],
            "challenge_test": ["python", "-V"],
            "candidates": [
                {"id": "a", "operations": [], "repair_operations": []},
                {"id": "b", "operations": [], "repair_operations": []},
                {"id": "c", "operations": [], "repair_operations": []}
            ],
            "policy": {"allowed_executables": ["python"]}
        }
        with self.assertRaises(MissionPolicyError):
            ExecutionPolicy.from_mission(mission).validate(mission)


if __name__ == "__main__":
    unittest.main()
