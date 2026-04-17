import os
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription, DeclareLaunchArgument,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory('scout_mini_description')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    params_file = os.path.join(pkg_share, 'config', 'scout_nav2.yaml')

    cartographer_config_dir = os.path.join(pkg_share, 'config')
    configuration_basename = 'scout_cartographer_localization.lua'
    # 默认地图路径（install 目录，--symlink-install 后与源码目录同步）
    default_map_path = os.path.join(pkg_share, 'maps', 'scout_carto_map.pbstream')

    # --- 1. Cartographer 纯定位节点 (提供 map->odom TF，200Hz 更新) ---
    # --load_state_filename: 加载建图阶段保存的 .pbstream 序列化地图
    # --load_frozen_state true: 冻结地图，只定位不修改地图
    cartographer_node = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': False}],
        arguments=[
            '-configuration_directory', cartographer_config_dir,
            '-configuration_basename', configuration_basename,
            '-load_state_filename', LaunchConfiguration('cartographer_map'),
            '-load_frozen_state', 'true',
        ],
        remappings=[
            ('/scan', '/scan'),
            ('/odom', '/odom'),
        ]
    )

    # --- 2. cartographer_occupancy_grid_node 从已加载的 .pbstream 发布 /map ---
    # 替代独立的 map_server，只需 scout_carto_map.pbstream 一个文件即可
    occupancy_grid_node = Node(
        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='cartographer_occupancy_grid_node',
        output='screen',
        parameters=[{'use_sim_time': False}],
        arguments=['-resolution', '0.05', '-publish_period_sec', '1.0'],
    )

    # --- 3. Nav2 导航栈 (不含定位，只用 navigation_launch.py) ---
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'False',
            'params_file': params_file,
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'cartographer_map',
            default_value=default_map_path,
            description='Path to Cartographer serialized map (.pbstream)'),

        cartographer_node,
        occupancy_grid_node,
        nav2_navigation,
    ])
