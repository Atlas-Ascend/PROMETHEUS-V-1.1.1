import os
import tempfile
import unittest
from pathlib import Path

from prometheus_kernel.codex_provider import (
    CodexProvider,
    build_candidate_prompt,
    scrubbed_environment,
)


class CodexProviderTests(unittest.TestCase):
    def mission(self):
        return {
            "mission_id": "P1",
            "objective": "Build the recursive forge",
            "acceptance_criteria": ["Tests pass", "Proof is emitted"],
            "constraints": ["Do not push"],
            "standard_test": ["python", "-m", "unittest"],
            "challenge_test": ["python", "-m", "unittest", "-v"],
        }

    def test_prompt_binds_strategy_gates_and_no_push_boundary(self):
        prompt = build_candidate_prompt(
            self.mission(),
            {"id": "alpha", "strategy": "reliability", "prompt": "Repair recovery."},
        )
        self.assertIn("Candidate: alpha", prompt)
        self.assertIn("Strategy: reliability", prompt)
        self.assertIn("python -m unittest", prompt)
        self.assertIn("Do not push", prompt)

    def test_command_uses_current_explicit_workspace_write_contract(self):
        provider = CodexProvider(executable="codex", model="test-model")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "final.md"
            command = provider.command(output, "implement")
        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertIn("--sandbox", command)
        self.assertIn("workspace-write", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertIn("--output-last-message", command)
        self.assertNotIn("--full-auto", command)

    def test_discord_and_github_tokens_are_not_inherited(self):
        environment = scrubbed_environment(
            {
                "PATH": os.environ.get("PATH", ""),
                "DISCORD_BOT_TOKEN": "secret",
                "GITHUB_TOKEN": "secret",
                "GH_TOKEN": "secret",
                "OPENAI_API_KEY": "secret",
                "CODEX_API_KEY": "secret",
            }
        )
        self.assertNotIn("DISCORD_BOT_TOKEN", environment)
        self.assertNotIn("GITHUB_TOKEN", environment)
        self.assertNotIn("GH_TOKEN", environment)
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("CODEX_API_KEY", environment)


if __name__ == "__main__":
    unittest.main()
