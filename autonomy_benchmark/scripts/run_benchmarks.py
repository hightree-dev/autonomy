#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess


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
        returncode = process.wait()
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if returncode:
        raise subprocess.CalledProcessError(returncode, process.args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=int)
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("runs must be at least 1")

    for run_id in range(1, args.runs + 1):
        print(f"run {run_id}/{args.runs}", flush=True)
        run(args.arguments, run_id)


if __name__ == "__main__":
    main()
