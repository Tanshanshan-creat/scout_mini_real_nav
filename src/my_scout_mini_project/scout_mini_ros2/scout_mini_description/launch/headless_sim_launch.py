import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_path = get_package_share_directory('scout_mini_description')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    
    # 【关键修改】指向我们刚刚创建的“降速版”世界文件
    # 这样才能保证物理引擎是 500Hz，解决雷达漂移
    default_world_path = os.path.join(pkg_path, 'worlds', 'turtlebot3_slow.world')

    world_arg = DeclareLaunchArgument(
        'world',
        default_value=default_world_path,
        description='Path to the Gazebo world file'
    )

    # 1. 启动 Gazebo Server
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'verbose': 'true'
        }.items()
    )

    # 2. 机器人状态发布器 (必须开启 use_sim_time)
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_path, 'launch', 'description_launch.py')
        ),
        launch_arguments={'use_sim_time': 'true', 'use_gui': 'false'}.items()
    )

    # 3. 将机器人“生”到 Gazebo 世界里
    # 注意：TurtleBot3 地图中心有东西，我们把小车生在旁边 (-2.0, -0.5)
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', 
                   '-entity', 'scout_mini',
                   '-x', '-2.0', '-y', '-0.5', '-z', '0.0'],
        output='screen'
    )

    return LaunchDescription([
        world_arg,
        gzserver,
        rsp,
        spawn_entity
    ])
