import os
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory('scout_mini_description')
    
    # 配置文件路径
    cartographer_config_dir = os.path.join(pkg_share, 'config')
    configuration_basename = 'scout_cartographer.lua'

    return LaunchDescription([
        # 1. Cartographer 核心节点
        Node(
            package='cartographer_ros',
            executable='cartographer_node',
            name='cartographer_node',
            output='screen',
            # 实车必须设为 False
            parameters=[{'use_sim_time': False}],
            arguments=[
                '-configuration_directory', cartographer_config_dir,
                '-configuration_basename', configuration_basename
            ],
            remappings=[
                ('/scan', '/scan'),
                ('/odom', '/odom'),
            ]
        ),

        # 2. 栅格地图转换节点 (把子图转成 map topic)
        Node(
            package='cartographer_ros',
            executable='cartographer_occupancy_grid_node',
            name='cartographer_occupancy_grid_node',
            output='screen',
            # 实车设为 False
            parameters=[{'use_sim_time': False}],
            arguments=['-resolution', '0.05', '-publish_period_sec', '1.0']
        ),
    ])
