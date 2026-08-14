#!/usr/bin/env python3
import argparse
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", type=int)
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("runs must be at least 1")

    for run_id in range(1, args.runs + 1):
        print(f"run {run_id}/{args.runs}", flush=True)
        subprocess.run(command(args.arguments, run_id), check=True)


if __name__ == "__main__":
    main()
