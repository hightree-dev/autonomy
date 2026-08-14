import os
import socket
import time

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetLaunchConfiguration,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def wait_for_port(kind, port, timeout=15.0):
    deadline = time.monotonic() + timeout
    while True:
        sock = socket.socket(socket.AF_INET, kind)
        if kind == socket.SOCK_STREAM:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"port {port} unavailable") from exc
        else:
            return
        finally:
            sock.close()
        time.sleep(0.1)


def check_ports(_context: LaunchContext):
    ports = [
        (socket.SOCK_STREAM, 5760),
        (socket.SOCK_DGRAM, 2019),
        (socket.SOCK_DGRAM, 5501),
        (socket.SOCK_DGRAM, 9002),
        (socket.SOCK_DGRAM, 14550),
        (socket.SOCK_DGRAM, 14551),
    ]
    for kind, port in ports:
        wait_for_port(kind, port)
    return [SetLaunchConfiguration("fcu_url", "udp://:14550@")]


def generate_launch_description():
    bringup = get_package_share_directory("autonomy_bringup")
    benchmark = get_package_share_directory("autonomy_benchmark")

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup, "launch", "sim.launch.py")
        ),
        launch_arguments={
            "world": LaunchConfiguration("world"),
            "spawn_z": LaunchConfiguration("spawn_z"),
            "use_gz_sim_gui": LaunchConfiguration("gui"),
            "rviz": LaunchConfiguration("rviz"),
        }.items(),
    )

    run = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(benchmark, "launch", "benchmark.launch.py")
        ),
        launch_arguments={
            "traj": LaunchConfiguration("traj"),
            "speed": LaunchConfiguration("speed"),
            "size": LaunchConfiguration("size"),
            "z": LaunchConfiguration("target_z"),
            "cycles": LaunchConfiguration("cycles"),
            "settle_time": LaunchConfiguration("settle_time"),
            "altitude_tolerance": LaunchConfiguration("altitude_tolerance"),
            "vertical_speed_tolerance": LaunchConfiguration(
                "vertical_speed_tolerance"
            ),
            "bag_root": LaunchConfiguration("bag_root"),
            "run_id": LaunchConfiguration("run_id"),
            "land_after": "false",
            "fcu_url": LaunchConfiguration("fcu_url"),
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value="empty"),
            DeclareLaunchArgument("spawn_z", default_value="0.2"),
            DeclareLaunchArgument("gui", default_value="false"),
            DeclareLaunchArgument("rviz", default_value="false"),
            DeclareLaunchArgument("traj", default_value="circle"),
            DeclareLaunchArgument("speed", default_value="2.0"),
            DeclareLaunchArgument("size", default_value="5.0"),
            DeclareLaunchArgument("target_z", default_value="2.0"),
            DeclareLaunchArgument("cycles", default_value="4"),
            DeclareLaunchArgument("settle_time", default_value="1.0"),
            DeclareLaunchArgument("altitude_tolerance", default_value="0.1"),
            DeclareLaunchArgument(
                "vertical_speed_tolerance", default_value="0.1"
            ),
            DeclareLaunchArgument("bag_root", default_value="benchmark_bags"),
            DeclareLaunchArgument("run_id", default_value=""),
            OpaqueFunction(function=check_ports),
            sim,
            run,
        ]
    )
