#!/usr/bin/env python3
import argparse
import math

from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String


def read_bag(path):
    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=path, storage_id="sqlite3"),
        ConverterOptions(
            input_serialization_format="cdr",
            output_serialization_format="cdr",
        ),
    )
    refs = []
    poses = []
    phases = []
    while reader.has_next():
        topic, data, ts = reader.read_next()
        if topic == "/benchmark/reference":
            refs.append((ts * 1e-9, deserialize_message(data, PoseStamped)))
        elif topic == "/mavros/local_position/pose":
            poses.append((ts * 1e-9, deserialize_message(data, PoseStamped)))
        elif topic == "/benchmark/phase":
            phases.append((ts * 1e-9, deserialize_message(data, String).data))
    return refs, poses, phases


def track_window(phases):
    t_start = None
    for t, phase in phases:
        if phase == "track":
            if t_start is None:
                t_start = t
        elif t_start is not None:
            return t_start, t
    if t_start is None:
        raise SystemExit("no track phase in bag")
    return t_start, phases[-1][0]


def interp_ref(refs, t):
    lo, hi = 0, len(refs) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if refs[mid][0] < t:
            lo = mid + 1
        else:
            hi = mid
    i = min(max(1, lo), len(refs) - 1)
    t0, m0 = refs[i - 1]
    t1, m1 = refs[i]
    a = 0.0 if t1 == t0 else min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    p0 = m0.pose.position
    p1 = m1.pose.position
    return (
        p0.x + a * (p1.x - p0.x),
        p0.y + a * (p1.y - p0.y),
        p0.z + a * (p1.z - p0.z),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bag")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    refs, poses, phases = read_bag(args.bag)
    if not refs or not poses:
        raise SystemExit("missing reference or pose topic in bag")
    t_start, t_end = track_window(phases)

    errors = []
    for t, msg in poses:
        if t < t_start or t > t_end:
            continue
        rx, ry, rz = interp_ref(refs, t)
        dx = msg.pose.position.x - rx
        dy = msg.pose.position.y - ry
        dz = msg.pose.position.z - rz
        errors.append(
            (
                math.sqrt(dx * dx + dy * dy + dz * dz),
                math.sqrt(dx * dx + dy * dy),
                abs(dz),
            )
        )

    if not errors:
        raise SystemExit("no pose samples in track window")

    n = len(errors)
    lines = [
        f"bag: {args.bag}",
        f"track window: {t_end - t_start:.1f} s, samples: {n}",
    ]
    for label, idx in (("3d", 0), ("2d", 1), ("z", 2)):
        vals = [e[idx] for e in errors]
        rmse = math.sqrt(sum(v * v for v in vals) / n)
        lines.append(
            f"{label}: rmse {rmse:.3f} m, max {max(vals):.3f} m, "
            f"mean {sum(vals) / n:.3f} m"
        )
    text = "\n".join(lines)
    print(text)
    if args.report:
        with open(args.report, "w") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
