import importlib.util
from pathlib import Path
import unittest


PATH = Path(__file__).parents[1] / "scripts" / "evaluate_bag.py"
SPEC = importlib.util.spec_from_file_location("evaluate_bag", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TestEvaluateBag(unittest.TestCase):
    def test_phase_durations(self):
        self.assertEqual(
            MODULE.phase_durations(
                [(0.0, "wait"), (0.5, "wait"), (1.0, "arm"), (3.0, "done")]
            ),
            [("wait", 1.0), ("arm", 2.0), ("done", 0.0)],
        )


if __name__ == "__main__":
    unittest.main()
