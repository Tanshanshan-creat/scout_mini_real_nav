#!/usr/bin/env python3

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time", default="false")
    # 哪怕用不到，保留这个参数声明也不会报错，防止 launch 调用出错
    use_gui = LaunchConfiguration("use_gui", default="true") 

    urdf_file_path = os.path.join(
        get_package_share_directory("scout_mini_description"), "urdf", "scout_mini.urdf.xacro"
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value=use_sim_time,
                description="Use simulation (Gazebo) clock if true",
            ),
            DeclareLaunchArgument(
                "use_gui",
                default_value=use_gui,
                description="Use joint_state_publisher_gui if true",
            ),
            DeclareLaunchArgument(
                name="urdf_file_path",
                default_value=urdf_file_path,
                description="Absolute path to robot urdf file",
            ),
            
            # 1. 机器人状态发布器 (必须保留)
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                name="robot_state_publisher",
                output="screen",
                parameters=[
                    {
                        "robot_description": Command(
                            [
                                "xacro ",
                                LaunchConfiguration("urdf_file_path"),
                            ]
                        ),
                        "use_sim_time": use_sim_time,
                    }
                ],
            ),

            # 2. 关节状态发布器已被彻底移除
            # 注意看下面：这里必须有闭合的方括号和圆括号
        ]
    )
