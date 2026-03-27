import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 1. 获取底盘包路径
    base_pkg_path = get_package_share_directory('scout_mini_base')

    # 2. 包含底盘启动文件 (负责底盘运动控制)
    base_driver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(base_pkg_path, 'launch', 'base_launch.py')
        )
    )

    # 3. 定义雷达节点 (RPLIDAR A2M8 配置)
    lidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        parameters=[{
            'channel_type': 'serial',
            'serial_port': '/dev/ttyUSB0',
            'serial_baudrate': 115200,
            'frame_id': 'laser_link',
            'inverted': False,
            'angle_compensate': True,
            'scan_mode': 'Standard',
            'use_sim_time': False,
        }],
        output='screen'
    )

    # 延迟5秒启动雷达，等待TF树（odom->base_link->laser_link）完全就绪
    lidar_delayed = TimerAction(period=5.0, actions=[lidar_node])

    return LaunchDescription([
        base_driver,
        lidar_delayed,
    ])

