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
    def test_parameter_values_waits_for_valid_types(self):
        invalid = [Mock(type=MODULE.ParameterType.PARAMETER_NOT_SET)] * 4
        self.assertIsNone(MODULE.parameter_values(invalid))
        valid = [
            Mock(type=MODULE.ParameterType.PARAMETER_DOUBLE, double_value=value)
            for value in MODULE.EXPECTED_PARAMS.values()
        ]
        self.assertEqual(MODULE.parameter_values(valid), MODULE.EXPECTED_PARAMS)

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
        with patch.object(
            MODULE.subprocess, "Popen", return_value=process
        ) as popen, patch.object(
            MODULE, "read_fcu_params", return_value=MODULE.EXPECTED_PARAMS
        ) as read_params, patch.object(MODULE.os, "killpg") as killpg:
            self.assertEqual(MODULE.run([], 1), MODULE.EXPECTED_PARAMS)
        popen.assert_called_once_with(MODULE.command([], 1), start_new_session=True)
        read_params.assert_called_once_with(process)
        killpg.assert_called_once_with(42, signal.SIGINT)

    def test_rate_order_is_balanced(self):
        self.assertEqual(MODULE.RATE_ORDER.count(20), 5)
        self.assertEqual(MODULE.RATE_ORDER.count(100), 5)


if __name__ == "__main__":
    unittest.main()
