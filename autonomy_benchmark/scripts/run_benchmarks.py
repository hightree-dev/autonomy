#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess

import rclpy
from mavros_msgs.srv import ParamGet


PARAM_NAMES = ("WP_ACC", "WP_SPD", "WP_JERK", "ATC_ANGLE_MAX")
EXPECTED_PARAMS = {"WP_ACC": 8, "WP_SPD": 12, "WP_JERK": 20, "ATC_ANGLE_MAX": 45}
RATE_ORDER = (20, 100, 100, 20, 20, 100, 100, 20, 20, 100)


def command(arguments, run_id):
    return [
        "ros2",
        "launch",
        "autonomy_benchmark",
        "fast_benchmark.launch.py",
        *arguments,
        f"run_id:={run_id}",
    ]


def run(arguments, run_id):
    process = subprocess.Popen(command(arguments, run_id), start_new_session=True)
    try:
        params = read_fcu_params()
        if params != EXPECTED_PARAMS:
            raise RuntimeError(f"unexpected FCU parameters: {params}")
        returncode = process.wait()
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if returncode:
        raise subprocess.CalledProcessError(returncode, process.args)
    return params


def read_fcu_params(timeout=60.0):
    rclpy.init()
    node = rclpy.create_node(f"benchmark_params_{os.getpid()}")
    client = node.create_client(ParamGet, "/mavros/param/get")
    try:
        if not client.wait_for_service(timeout_sec=timeout):
            raise TimeoutError("FCU parameter service unavailable")
        values = {}
        for name in PARAM_NAMES:
            request = ParamGet.Request()
            request.param_id = name
            future = client.call_async(request)
            rclpy.spin_until_future_complete(node, future, timeout_sec=timeout)
            response = future.result()
            if response is None or not response.success:
                raise RuntimeError(f"failed to read FCU parameter {name}")
            values[name] = response.value.real or response.value.integer
        return values
    finally:
        node.destroy_node()
        rclpy.shutdown()


def git_sha(path):
    return subprocess.check_output(
        ["git", "-C", path, "rev-parse", "HEAD"], text=True
    ).strip()


def write_manifest(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def comparison(args):
    bag_root = Path(args.bag_root)
    bag_root.mkdir(parents=True, exist_ok=True)
    manifest_path = bag_root / "rate_comparison.json"
    manifest = {
        "autonomy_sha": git_sha(args.autonomy_repo),
        "ardupilot_sha": git_sha(args.ardupilot_repo),
        "rate_order_hz": list(RATE_ORDER),
        "trajectory": {"type": "circle", "speed_mps": 4, "radius_m": 5, "cycles": 4},
        "expected_fcu_params": EXPECTED_PARAMS,
        "runs": [],
    }
    write_manifest(manifest_path, manifest)
    for index, rate in enumerate(RATE_ORDER, 1):
        print(f"run {index}/{len(RATE_ORDER)}: {rate} Hz", flush=True)
        before = {path.name for path in bag_root.iterdir() if path.is_dir()}
        try:
            params = run(
                [
                    "world:=empty",
                    "speed:=4.0",
                    "size:=5.0",
                    "cycles:=4",
                    "target_z:=2.0",
                    "wipe:=true",
                    f"rate:={rate}",
                    f"bag_root:={bag_root}",
                ],
                index,
            )
        except Exception as exc:
            manifest["runs"].append(
                {
                    "run": index,
                    "rate_hz": rate,
                    "status": "failed",
                    "error": type(exc).__name__,
                }
            )
            write_manifest(manifest_path, manifest)
            continue
        bags = sorted(
            path.name
            for path in bag_root.iterdir()
            if path.is_dir() and path.name not in before
        )
        if len(bags) != 1:
            raise RuntimeError(f"expected one new bag, found {len(bags)}")
        manifest["runs"].append(
            {
                "run": index,
                "rate_hz": rate,
                "status": "completed",
                "bag": bags[0],
                "fcu_params": params,
            }
        )
        write_manifest(manifest_path, manifest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=int, nargs="?")
    parser.add_argument("arguments", nargs="*")
    parser.add_argument("--compare-rates", action="store_true")
    parser.add_argument("--bag-root", default="benchmark_bags")
    parser.add_argument("--autonomy-repo", default=".")
    parser.add_argument("--ardupilot-repo", default="../ardupilot")
    args = parser.parse_args()
    if args.compare_rates:
        comparison(args)
        return
    if args.runs is None:
        parser.error("runs is required")
    if args.runs < 1:
        parser.error("runs must be at least 1")

    for run_id in range(1, args.runs + 1):
        print(f"run {run_id}/{args.runs}", flush=True)
        run(args.arguments, run_id)


if __name__ == "__main__":
    main()
