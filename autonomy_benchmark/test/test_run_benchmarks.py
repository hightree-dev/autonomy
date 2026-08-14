import importlib.util
from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
