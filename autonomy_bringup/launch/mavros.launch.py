"""Launch mavros connected to the SITL mavproxy udp output (14551)."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_mavros = get_package_share_directory("mavros")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "fcu_url",
                default_value="udp://:14551@",
                description="FCU connection URL.",
            ),
            DeclareLaunchArgument(
                "namespace",
                default_value="mavros",
                description="mavros node namespace.",
            ),
            Node(
                package="mavros",
                executable="mavros_node",
                namespace=LaunchConfiguration("namespace"),
                parameters=[
                    os.path.join(pkg_mavros, "launch", "apm_config.yaml"),
                    os.path.join(pkg_mavros, "launch", "apm_pluginlists.yaml"),
                    {"fcu_url": LaunchConfiguration("fcu_url")},
                ],
                output="screen",
            ),
        ]
    )
