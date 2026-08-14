# Copyright 2023 ArduPilot.org.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Launch the iris_super quadcopter in Gazebo with RViz."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def launch_gz_sim_server(context: LaunchContext):
    pkg_autonomy_bringup = get_package_share_directory("autonomy_bringup")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")

    world = LaunchConfiguration("world").perform(context)
    world_file = Path(pkg_autonomy_bringup) / "worlds" / f"{world}.sdf"

    gz_sim_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f'{Path(pkg_ros_gz_sim) / "launch" / "gz_sim.launch.py"}'
        ),
        launch_arguments={"gz_args": f"-v4 -s -r {world_file}"}.items(),
        condition=IfCondition(LaunchConfiguration("use_gz_sim_server")),
    )
    return [gz_sim_server]


def generate_launch_description():
    """Generate a launch description for the iris_super quadcopter."""
    pkg_autonomy_bringup = get_package_share_directory("autonomy_bringup")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")

    robot = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                PathJoinSubstitution(
                    [
                        pkg_autonomy_bringup,
                        "launch",
                        "robots",
                        "iris_super.launch.py",
                    ]
                ),
            ]
        ),
        launch_arguments={
            "namespace": LaunchConfiguration("namespace"),
            "world_name": LaunchConfiguration("world"),
            "z": LaunchConfiguration("spawn_z"),
        }.items(),
        condition=IfCondition(LaunchConfiguration("spawn_robot")),
    )

    gz_sim_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f'{Path(pkg_ros_gz_sim) / "launch" / "gz_sim.launch.py"}'
        ),
        launch_arguments={"gz_args": "-v4 -g"}.items(),
        condition=IfCondition(LaunchConfiguration("use_gz_sim_gui")),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        namespace=LaunchConfiguration("namespace"),
        arguments=[
            "-d",
            f'{Path(pkg_autonomy_bringup) / "rviz" / "iris_super.rviz"}',
        ],
        condition=IfCondition(LaunchConfiguration("rviz")),
        remappings=[
            ("/tf", "tf"),
            ("/tf_static", "tf_static"),
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "namespace",
                default_value="",
                description="Robot namespace.",
            ),
            DeclareLaunchArgument(
                "world",
                default_value="maze",
                description="World name (worlds/<world>.sdf).",
            ),
            DeclareLaunchArgument("spawn_z", default_value="0.2"),
            DeclareLaunchArgument(
                "use_gz_sim_server",
                default_value="true",
                description="Run the Gazebo server.",
            ),
            DeclareLaunchArgument(
                "use_gz_sim_gui",
                default_value="true",
                description="Run the Gazebo GUI.",
            ),
            DeclareLaunchArgument(
                "spawn_robot",
                default_value="true",
                description="Spawn the robot and start SITL+ROS.",
            ),
            DeclareLaunchArgument(
                "rviz", default_value="true", description="Open RViz."
            ),
            OpaqueFunction(function=launch_gz_sim_server),
            gz_sim_gui,
            robot,
            rviz,
        ]
    )
