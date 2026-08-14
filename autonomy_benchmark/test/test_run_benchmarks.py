import importlib.util
from pathlib import Path
import signal
import unittest
from unittest.mock import Mock, patch


PATH = Path(__file__).parents[1] / "scripts" / "run_benchmarks.py"
SPEC = importlib.util.spec_from_file_location("run_benchmarks", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TestRunBenchmarks(unittest.TestCase):
    def test_command_appends_run_id(self):
        self.assertEqual(
            MODULE.command(["speed:=4.0"], 3),
            [
                "ros2",
                "launch",
                "autonomy_benchmark",
                "fast_benchmark.launch.py",
                "speed:=4.0",
                "run_id:=3",
            ],
        )

    def test_run_terminates_remaining_process_group(self):
        process = Mock(pid=42, args=["ros2"])
        process.wait.return_value = 0
        with patch.object(MODULE.subprocess, "Popen", return_value=process) as popen, patch.object(
            MODULE.os, "killpg"
        ) as killpg:
            MODULE.run([], 1)
        popen.assert_called_once_with(MODULE.command([], 1), start_new_session=True)
        killpg.assert_called_once_with(42, signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
