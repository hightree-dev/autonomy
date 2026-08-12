"""Run a trajectory tracking benchmark: mavros + commander + bag recording."""
import os
from datetime import datetime

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    EmitEvent,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

RECORD_TOPICS = [
    "/benchmark/reference",
    "/benchmark/phase",
    "/mavros/state",
    "/mavros/local_position/pose",
    "/mavros/local_position/velocity_local",
    "/mavros/setpoint_raw/local",
]


def launch_benchmark(context: LaunchContext):
    traj = LaunchConfiguration("traj").perform(context)
    speed = LaunchConfiguration("speed").perform(context)
    size = LaunchConfiguration("size").perform(context)
    z = LaunchConfiguration("z").perform(context)
    duration = LaunchConfiguration("duration").perform(context)
    bag_root = LaunchConfiguration("bag_root").perform(context)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bag_path = os.path.join(bag_root, f"{traj}_v{speed}_{stamp}")

    commander = Node(
        package="autonomy_benchmark",
        executable="traj_commander.py",
        name="traj_commander",
        output="screen",
        parameters=[
            {
                "traj": traj,
                "speed": float(speed),
                "size": float(size),
                "z": float(z),
                "duration": float(duration),
            }
        ],
    )

    record = ExecuteProcess(
        cmd=["ros2", "bag", "record", "-o", bag_path] + RECORD_TOPICS,
        output="screen",
    )

    finish = RegisterEventHandler(
        OnProcessExit(
            target_action=commander,
            on_exit=[EmitEvent(event=Shutdown(reason="benchmark finished"))],
        )
    )

    return [record, commander, finish]


def generate_launch_description():
    pkg_autonomy_bringup = get_package_share_directory("autonomy_bringup")

    mavros = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_autonomy_bringup, "launch", "mavros.launch.py")
        )
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("traj", default_value="circle"),
            DeclareLaunchArgument("speed", default_value="2.0"),
            DeclareLaunchArgument("size", default_value="5.0"),
            DeclareLaunchArgument("z", default_value="5.0"),
            DeclareLaunchArgument("duration", default_value="60.0"),
            DeclareLaunchArgument("bag_root", default_value="benchmark_bags"),
            mavros,
            OpaqueFunction(function=launch_benchmark),
        ]
    )
