import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SUPERX = ROOT / "superx.py"


class SuperxResearchTests(unittest.TestCase):
    def make_fake_grok(self, directory: Path, text: str, exit_code: int = 0) -> Path:
        path = directory / "fake-grok"
        path.write_text(f"#!/bin/sh\ncat <<'EOF'\n{text}\nEOF\nexit {exit_code}\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return path

    def run_superx(self, args, fake_grok: Path):
        env = os.environ.copy()
        env["GROK_BIN"] = str(fake_grok)
        return subprocess.run(
            [sys.executable, str(SUPERX), *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def run_superx_with_env(self, args, env):
        return subprocess.run(
            [sys.executable, str(SUPERX), *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_research_writes_markdown_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Smoke\n\n- ok\n")
            output = tmp_path / "report.md"

            proc = self.run_superx(["research", "smoke", "--format", "json", "--output", str(output)], fake)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            metadata = json.loads(proc.stdout)
            self.assertEqual(metadata["markdown_path"], str(output))
            self.assertEqual(metadata["grok_returncode"], 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "# Smoke\n\n- ok")
            self.assertTrue(output.with_suffix(".json").exists())

    def test_research_nonzero_exits_nonzero_and_marks_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Partial\n\n- maybe\n", exit_code=1)
            output = tmp_path / "partial.md"

            proc = self.run_superx(["research", "partial", "--format", "json", "--output", str(output)], fake)

            self.assertEqual(proc.returncode, 1)
            metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["grok_returncode"], 1)
            self.assertIn("partial", metadata["warning"])
            self.assertIn("saved partial research", proc.stderr)

    def test_research_allow_partial_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Partial Allowed\n", exit_code=1)
            output = tmp_path / "allowed.md"

            proc = self.run_superx(
                ["research", "partial ok", "--format", "json", "--allow-partial", "--output", str(output)],
                fake,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            metadata = json.loads(proc.stdout)
            self.assertEqual(metadata["grok_returncode"], 1)
            self.assertIn("partial", metadata["warning"])

    def test_research_strips_preamble_before_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "Here is the report:\n\n# Actual Title\n\nbody\n")
            output = tmp_path / "clean.md"

            proc = self.run_superx(["research", "clean", "--output", str(output)], fake)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "# Actual Title\n\nbody")

    def test_research_unwraps_single_markdown_fence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "```markdown\n# Wrapped\n\n- ok\n```\n")
            output = tmp_path / "wrapped.md"

            proc = self.run_superx(["research", "wrapped", "--output", str(output)], fake)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "# Wrapped\n\n- ok")

    def test_research_preserves_leading_code_block_before_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "```markdown\n# Sample\n```\n\n# Real Heading\n\nbody\n")
            output = tmp_path / "codeblock.md"

            proc = self.run_superx(["research", "codeblock", "--output", str(output)], fake)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "```markdown\n# Sample\n```\n\n# Real Heading\n\nbody")

    def test_research_strips_ansi_before_caching(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "\033[32m# Green Title\033[0m\n\n- ok\n")
            output = tmp_path / "ansi.md"

            proc = self.run_superx(["research", "ansi", "--output", str(output)], fake)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "# Green Title\n\n- ok")

    def test_research_keeps_text_without_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "Plain report without heading\n\n- ok\n")
            output = tmp_path / "plain.md"

            proc = self.run_superx(["research", "plain", "--output", str(output)], fake)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "Plain report without heading\n\n- ok")

    def test_research_rejects_empty_query_before_calling_grok(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Should Not Run\n")

            proc = self.run_superx(["research", "   "], fake)

            self.assertEqual(proc.returncode, 2)
            self.assertIn("query is empty", proc.stderr)

    def test_research_rejects_invalid_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Should Not Run\n")

            proc = self.run_superx(["research", "timeout", "--timeout", "0"], fake)

            self.assertEqual(proc.returncode, 2)
            self.assertIn("--timeout must be > 0", proc.stderr)

    def test_research_rejects_invalid_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Should Not Run\n")

            proc = self.run_superx(["research", "retry", "--retries", "-1"], fake)

            self.assertEqual(proc.returncode, 2)
            self.assertIn("--retries must be >= 0", proc.stderr)

    def test_research_rejects_empty_grok_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "")

            proc = self.run_superx(["research", "empty"], fake)

            self.assertEqual(proc.returncode, 1)
            self.assertIn("returned empty output", proc.stderr)

    def test_research_timeout_preserves_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = tmp_path / "fake-grok-timeout"
            fake.write_text("#!/bin/sh\nprintf '# Timeout Partial\\n'; sleep 2\n", encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            output = tmp_path / "timeout.md"

            proc = self.run_superx(
                ["research", "timeout partial", "--timeout", "1", "--allow-partial", "--format", "json", "--output", str(output)],
                fake,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            metadata = json.loads(proc.stdout)
            self.assertEqual(metadata["grok_returncode"], 124)
            self.assertIn("partial", metadata["warning"])
            self.assertEqual(output.read_text(encoding="utf-8"), "# Timeout Partial")

    def test_research_retries_empty_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            counter = tmp_path / "count"
            fake = tmp_path / "fake-grok-retry"
            fake.write_text(
                f"""#!/bin/sh
count=0
if [ -f "{counter}" ]; then
  count=$(cat "{counter}")
fi
count=$((count + 1))
printf "%s" "$count" > "{counter}"
if [ "$count" -eq 1 ]; then
  exit 0
fi
cat <<'EOF'
# Retry OK

- saved
EOF
""",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            output = tmp_path / "retry.md"

            proc = self.run_superx(
                ["research", "retry ok", "--retries", "1", "--format", "json", "--output", str(output)],
                fake,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            metadata = json.loads(proc.stdout)
            self.assertEqual(metadata["attempts"], 2)
            self.assertEqual(counter.read_text(encoding="utf-8"), "2")
            self.assertEqual(output.read_text(encoding="utf-8"), "# Retry OK\n\n- saved")

    def test_research_reports_missing_grok_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            env["GROK_BIN"] = str(tmp_path / "missing-grok")

            proc = self.run_superx_with_env(["research", "missing", "--retries", "0"], env)

            self.assertEqual(proc.returncode, 127)
            self.assertIn("grok binary not found", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_json_runner_does_not_add_internal_fields_by_default(self):
        import superx

        completed = subprocess.CompletedProcess(
            args=["grok"],
            returncode=0,
            stdout=json.dumps({"text": "{\"ok\": true}"}),
            stderr="",
        )
        with mock.patch("superx.subprocess.run", return_value=completed):
            result = superx.run_grok_headless("prompt")

        self.assertNotIn("_superx_grok_returncode", result)
        self.assertEqual(result["text"], "{\"ok\": true}")

    def test_json_runner_can_include_internal_fields(self):
        import superx

        completed = subprocess.CompletedProcess(
            args=["grok"],
            returncode=2,
            stdout=json.dumps({"text": "{\"ok\": true}"}),
            stderr="stderr details",
        )
        with mock.patch("superx.subprocess.run", return_value=completed):
            result = superx.run_grok_headless("prompt", print_errors=False, include_internal=True)

        self.assertEqual(result["_superx_grok_returncode"], 2)
        self.assertEqual(result["_superx_grok_stderr"], "stderr details")
        self.assertEqual(result["text"], "{\"ok\": true}")


if __name__ == "__main__":
    unittest.main()
