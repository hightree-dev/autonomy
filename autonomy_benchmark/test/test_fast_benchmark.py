import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import Mock, patch


PATH = Path(__file__).parents[1] / "launch" / "fast_benchmark.launch.py"
SPEC = importlib.util.spec_from_file_location("fast_benchmark", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TestFastBenchmark(unittest.TestCase):
    def test_wait_for_port_retries(self):
        sock = Mock()
        sock.bind.side_effect = [OSError(), None]
        with patch.object(MODULE.socket, "socket", return_value=sock), patch.object(
            MODULE.time, "monotonic", side_effect=[0.0, 0.0]
        ), patch.object(MODULE.time, "sleep") as sleep:
            MODULE.wait_for_port(socket.SOCK_DGRAM, 9002)
        self.assertEqual(sock.bind.call_count, 2)
        sleep.assert_called_once_with(0.1)


if __name__ == "__main__":
    unittest.main()
