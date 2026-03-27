import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('scout_mini_description')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # 默认模型路径
    params_file = os.path.join(pkg_share, 'config', 'scout_nav2.yaml')
    # 默认地图路径 (如果没有指定，会去找 my_scout_map.yaml)
    map_dir = LaunchConfiguration('map', default=os.path.join(pkg_share, 'maps', 'my_scout_map.yaml'))

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_dir,
            'use_sim_time': 'False',
            'params_file': params_file,
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value=map_dir,
            description='Full path to map yaml file to load'),

        # 延迟5秒启动Nav2，等待底盘TF树（odom->base_link->laser_link）就绪
        TimerAction(period=5.0, actions=[nav2_bringup]),
    ])

