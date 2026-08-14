#!/usr/bin/env python3
import argparse
import math

from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions

from geometry_msgs.msg import PoseStamped
from ros_gz_interfaces.msg import WorldStatistics
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
    stats = []
    while reader.has_next():
        topic, data, ts = reader.read_next()
        if topic == "/benchmark/reference":
            refs.append((ts * 1e-9, deserialize_message(data, PoseStamped)))
        elif topic == "/mavros/local_position/pose":
            poses.append((ts * 1e-9, deserialize_message(data, PoseStamped)))
        elif topic == "/benchmark/phase":
            phases.append((ts * 1e-9, deserialize_message(data, String).data))
        elif topic == "/benchmark/world_stats":
            stats.append((ts * 1e-9, deserialize_message(data, WorldStatistics)))
    return refs, poses, phases, stats


WINDOW_MARGIN = 0.25


def track_window(phases):
    t_start = None
    t_end = None
    for t, phase in phases:
        if phase == "track":
            if t_start is None:
                t_start = t
        elif t_start is not None:
            t_end = t
            break
    if t_start is None:
        raise SystemExit("no track phase in bag")
    if t_end is None:
        t_end = phases[-1][0]
    return t_start + WINDOW_MARGIN, t_end - WINDOW_MARGIN


def phase_durations(phases):
    durations = []
    start = None
    current = None
    for t, phase in phases:
        if phase == current:
            continue
        if current is not None:
            durations.append((current, t - start))
        current = phase
        start = t
    if current is not None:
        durations.append((current, phases[-1][0] - start))
    return durations


def sample_rate(messages, t_start, t_end):
    times = [t for t, _ in messages if t_start <= t <= t_end]
    if len(times) < 2 or times[-1] == times[0]:
        return 0.0
    return (len(times) - 1) / (times[-1] - times[0])


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
    tx = p1.x - p0.x
    ty = p1.y - p0.y
    tangent_norm = math.hypot(tx, ty)
    if tangent_norm > 0.0:
        tx /= tangent_norm
        ty /= tangent_norm
    return (
        p0.x + a * (p1.x - p0.x),
        p0.y + a * (p1.y - p0.y),
        p0.z + a * (p1.z - p0.z),
        tx,
        ty,
    )


def estimate_time_lag(refs, poses, t_start, t_end):
    best_lag = 0.0
    best_error = math.inf
    for centiseconds in range(-100, 101):
        lag = centiseconds / 100.0
        squared_errors = []
        for t, msg in poses:
            if t_start <= t <= t_end:
                rx, ry, _, _, _ = interp_ref(refs, t - lag)
                dx = msg.pose.position.x - rx
                dy = msg.pose.position.y - ry
                squared_errors.append(dx * dx + dy * dy)
        mean_error = sum(squared_errors) / len(squared_errors)
        if mean_error < best_error:
            best_error = mean_error
            best_lag = lag
    return best_lag


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bag")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    refs, poses, phases, stats = read_bag(args.bag)
    if not refs or not poses:
        raise SystemExit("missing reference or pose topic in bag")
    t_start, t_end = track_window(phases)

    errors = []
    for t, msg in poses:
        if t < t_start or t > t_end:
            continue
        rx, ry, rz, tx, ty = interp_ref(refs, t)
        dx = msg.pose.position.x - rx
        dy = msg.pose.position.y - ry
        dz = msg.pose.position.z - rz
        errors.append(
            (
                math.sqrt(dx * dx + dy * dy + dz * dz),
                math.sqrt(dx * dx + dy * dy),
                abs(dz),
                dx * ty - dy * tx,
                dx * tx + dy * ty,
            )
        )

    if not errors:
        raise SystemExit("no pose samples in track window")

    n = len(errors)
    lines = [
        f"bag: {args.bag}",
        f"benchmark duration: {phases[-1][0] - phases[0][0]:.1f} s",
        "phases: "
        + ", ".join(
            f"{phase} {duration:.2f} s"
            for phase, duration in phase_durations(phases)
        ),
        f"track window: {t_end - t_start:.1f} s, samples: {n}",
        f"reference rate: {sample_rate(refs, t_start, t_end):.1f} Hz",
        f"pose rate: {sample_rate(poses, t_start, t_end):.1f} Hz",
        f"time lag: {estimate_time_lag(refs, poses, t_start, t_end):+.2f} s",
    ]
    rtfs = [msg.real_time_factor for t, msg in stats if t_start <= t <= t_end]
    if rtfs:
        lines.append(f"real time factor: {sum(rtfs) / len(rtfs):.3f}")
    for label, idx in (("3d", 0), ("2d", 1), ("z", 2)):
        vals = [e[idx] for e in errors]
        rmse = math.sqrt(sum(v * v for v in vals) / n)
        p95 = sorted(vals)[math.ceil(0.95 * n) - 1]
        lines.append(
            f"{label}: rmse {rmse:.3f} m, p95 {p95:.3f} m, max {max(vals):.3f} m, "
            f"mean {sum(vals) / n:.3f} m"
        )
    for label, idx in (("radial", 3), ("tangential", 4)):
        vals = [e[idx] for e in errors]
        abs_vals = sorted(abs(v) for v in vals)
        rmse = math.sqrt(sum(v * v for v in vals) / n)
        p95 = abs_vals[math.ceil(0.95 * n) - 1]
        lines.append(
            f"{label}: rmse {rmse:.3f} m, p95 {p95:.3f} m, max {max(abs_vals):.3f} m, "
            f"mean {sum(vals) / n:.3f} m"
        )
    text = "\n".join(lines)
    print(text)
    if args.report:
        with open(args.report, "w") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
