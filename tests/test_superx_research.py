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

    def make_fake_grok_script(self, directory: Path, script: str) -> Path:
        path = directory / "fake-grok"
        path.write_text(script, encoding="utf-8")
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

            proc = self.run_superx(["research", "empty", "--cache-dir", str(tmp_path / "cache")], fake)

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

    def test_research_auto_resume_finalizer_after_max_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            counter = tmp_path / "count"
            args_log = tmp_path / "args.log"
            fake = tmp_path / "fake-grok-finalizer"
            fake.write_text(
                f"""#!/bin/sh
count=0
if [ -f "{counter}" ]; then
  count=$(cat "{counter}")
fi
count=$((count + 1))
printf "%s" "$count" > "{counter}"
printf "attempt=$count args=%s\\n" "$*" >> "{args_log}"
if [ "$count" -eq 1 ]; then
  printf "Max turns reached\\n" >&2
  exit 0
fi
case " $* " in
  *" -r "*) ;;
  *) printf "missing resume flag\\n" >&2; exit 1 ;;
esac
case " $* " in
  *" --max-turns 6 "*) ;;
  *) printf "missing finalizer max turns\\n" >&2; exit 1 ;;
esac
case " $* " in
  *" --effort max "*) ;;
  *) printf "finalizer should keep heavy effort\\n" >&2; exit 1 ;;
esac
case " $* " in
  *" --check "*) printf "finalizer should disable check\\n" >&2; exit 1 ;;
esac
cat <<'EOF'
# Finalized OK

- saved
EOF
""",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            output = tmp_path / "finalizer.md"

            proc = self.run_superx(
                ["research", "wide topic", "--format", "json", "--output", str(output)],
                fake,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            metadata = json.loads(proc.stdout)
            self.assertEqual(metadata["attempts"], 2)
            self.assertEqual(metadata["attempt_details"][0]["profile"], "primary")
            self.assertTrue(metadata["attempt_details"][0]["max_turns_reached"])
            self.assertEqual(metadata["attempt_details"][1]["profile"], "resume-finalizer")
            self.assertTrue(metadata["attempt_details"][1]["resume_recent"])
            self.assertEqual(metadata["attempt_details"][1]["effort"], "max")
            self.assertEqual(metadata["attempt_details"][1]["max_turns"], 6)
            self.assertEqual(metadata["attempt_details"][1]["tools"], "")
            self.assertFalse(metadata["attempt_details"][1]["check"])
            self.assertEqual(output.read_text(encoding="utf-8"), "# Finalized OK\n\n- saved")

    def test_research_empty_failure_writes_failed_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok_script(
                tmp_path,
                "#!/bin/sh\nprintf 'Max turns reached\\n' >&2\nexit 0\n",
            )
            cache_dir = tmp_path / "cache"

            proc = self.run_superx(["research", "wide fail", "--cache-dir", str(cache_dir)], fake)

            self.assertEqual(proc.returncode, 1)
            self.assertIn("Saved failed research artifacts", proc.stderr)
            self.assertIn("resume-finalizer already tried", proc.stderr)
            failed_dir = cache_dir / "research" / "_failed"
            metadata_files = list(failed_dir.glob("*.json"))
            stdout_files = list(failed_dir.glob("*.stdout"))
            stderr_files = list(failed_dir.glob("*.stderr"))
            self.assertEqual(len(metadata_files), 1)
            self.assertEqual(len(stdout_files), 1)
            self.assertEqual(len(stderr_files), 1)
            metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
            self.assertEqual(metadata["failure"], "empty_output")
            self.assertEqual(metadata["attempts"], 2)
            self.assertEqual(metadata["attempt_details"][1]["profile"], "resume-finalizer")
            self.assertIn("Max turns reached", stderr_files[0].read_text(encoding="utf-8"))

    def test_research_reports_missing_grok_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            env["GROK_BIN"] = str(tmp_path / "missing-grok")
            env["SUPERX_CACHE_DIR"] = str(tmp_path / "cache")

            proc = self.run_superx_with_env(["research", "missing", "--retries", "0"], env)

            self.assertEqual(proc.returncode, 127)
            self.assertIn("grok binary not found", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_research_metadata_records_expert_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Expert\n\n- ok\n")
            output = tmp_path / "expert.md"

            proc = self.run_superx(
                [
                    "research",
                    "expert",
                    "--format",
                    "json",
                    "--output",
                    str(output),
                    "--model",
                    "fake-model",
                    "--effort",
                    "high",
                    "--reasoning-effort",
                    "high",
                    "--session-id",
                    "019e-session",
                ],
                fake,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            metadata = json.loads(proc.stdout)
            self.assertEqual(metadata["model"], "fake-model")
            self.assertEqual(metadata["effort"], "high")
            self.assertEqual(metadata["reasoning_effort"], "high")
            self.assertEqual(metadata["session_id"], "019e-session")
            self.assertTrue(metadata["check"])

    def test_research_no_check_records_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok(tmp_path, "# Light\n\n- ok\n")
            output = tmp_path / "light.md"

            proc = self.run_superx(
                ["research", "light", "--format", "json", "--no-check", "--output", str(output)],
                fake,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            metadata = json.loads(proc.stdout)
            self.assertFalse(metadata["check"])
            self.assertEqual(metadata["model"], "grok-build")
            self.assertEqual(metadata["effort"], "max")

    def test_research_empty_output_prints_stderr_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fake = self.make_fake_grok_script(
                tmp_path,
                "#!/bin/sh\nprintf 'model does not support parameter reasoningEffort\\n' >&2\nexit 1\n",
            )

            proc = self.run_superx(["research", "empty stderr", "--retries", "0", "--cache-dir", str(tmp_path / "cache")], fake)

            self.assertEqual(proc.returncode, 1)
            self.assertIn("grok stderr tail", proc.stderr)
            self.assertIn("reasoningEffort", proc.stderr)

    def test_plain_runner_passes_expert_flags_with_resume(self):
        import superx

        completed = subprocess.CompletedProcess(
            args=["grok"],
            returncode=0,
            stdout="# OK\n",
            stderr="",
        )
        with mock.patch("superx.subprocess.run", return_value=completed) as run:
            result = superx.run_grok_plain(
                "prompt",
                max_turns=9,
                timeout=123,
                model="grok-build",
                effort="max",
                reasoning_effort="high",
                session_id="019e-session",
                check=True,
            )

        cmd = run.call_args.args[0]
        self.assertIn("-m", cmd)
        self.assertIn("grok-build", cmd)
        self.assertIn("--effort", cmd)
        self.assertIn("max", cmd)
        self.assertIn("--reasoning-effort", cmd)
        self.assertIn("high", cmd)
        self.assertIn("-r", cmd)
        self.assertIn("019e-session", cmd)
        self.assertNotIn("-s", cmd)
        self.assertIn("--check", cmd)
        self.assertEqual(result["text"], "# OK\n")

    def test_plain_runner_can_resume_recent_without_session_id(self):
        import superx

        completed = subprocess.CompletedProcess(
            args=["grok"],
            returncode=0,
            stdout="# OK\n",
            stderr="",
        )
        with mock.patch("superx.subprocess.run", return_value=completed) as run:
            result = superx.run_grok_plain(
                "prompt",
                max_turns=6,
                timeout=123,
                model="grok-build",
                effort="max",
                resume_recent=True,
                check=False,
            )

        cmd = run.call_args.args[0]
        self.assertIn("-r", cmd)
        self.assertNotIn("--check", cmd)
        self.assertEqual(result["text"], "# OK\n")

    def test_plain_runner_can_disable_tools(self):
        import superx

        completed = subprocess.CompletedProcess(
            args=["grok"],
            returncode=0,
            stdout="# OK\n",
            stderr="",
        )
        with mock.patch("superx.subprocess.run", return_value=completed) as run:
            result = superx.run_grok_plain(
                "prompt",
                max_turns=6,
                timeout=123,
                tools="",
                check=False,
            )

        cmd = run.call_args.args[0]
        self.assertIn("--tools", cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertEqual(result["text"], "# OK\n")

    def test_max_turns_reached_accepts_common_variants(self):
        import superx

        self.assertTrue(superx.max_turns_reached("Max turns reached"))
        self.assertTrue(superx.max_turns_reached("maximum turns exceeded"))
        self.assertTrue(superx.max_turns_reached("hit max turns"))
        self.assertFalse(superx.max_turns_reached("rate limit reached"))

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

    def test_json_runner_forces_grok_build_for_native_x_tools(self):
        import superx

        completed = subprocess.CompletedProcess(
            args=["grok"],
            returncode=0,
            stdout=json.dumps({"text": "[]"}),
            stderr="",
        )
        with mock.patch("superx.subprocess.run", return_value=completed) as run:
            superx.run_grok_headless("prompt")

        cmd = run.call_args.args[0]
        self.assertIn("-m", cmd)
        self.assertEqual(cmd[cmd.index("-m") + 1], "grok-build")


if __name__ == "__main__":
    unittest.main()
