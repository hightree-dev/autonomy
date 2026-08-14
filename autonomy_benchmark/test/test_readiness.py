import unittest

from autonomy_benchmark.readiness import stable


class ReadinessTest(unittest.TestCase):
    def test_accepts_stable_vehicle(self):
        self.assertTrue(stable(2.04, 0.05, 2.0, 0.1, 0.1))

    def test_rejects_altitude_error(self):
        self.assertFalse(stable(2.11, 0.05, 2.0, 0.1, 0.1))

    def test_rejects_vertical_motion(self):
        self.assertFalse(stable(2.04, 0.11, 2.0, 0.1, 0.1))


if __name__ == "__main__":
    unittest.main()
