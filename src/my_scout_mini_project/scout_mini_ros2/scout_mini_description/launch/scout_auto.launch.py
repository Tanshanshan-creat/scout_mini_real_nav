import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    scout_pkg = get_package_share_directory('scout_mini_description')
    
    # 自动获取安装后的地图路径（现在 CMakeLists 修复了，这个路径才有效）
    map_yaml_path = os.path.join(scout_pkg, 'maps', 'my_scout_map.yaml')
    params_file_path = os.path.join(scout_pkg, 'config', 'scout_nav2.yaml')
    rviz_config_path = os.path.join(scout_pkg, 'rviz', 'scout_mini.rviz')

    # 1. 启动仿真 (加载 headless_sim_launch.py)
    headless_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(scout_pkg, 'launch', 'headless_sim_launch.py')
        ),
        launch_arguments={'use_sim_time': 'True'}.items()
    )

    # 2. 解冻物理引擎 (延迟5秒)
    unpause_physics = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=['ros2', 'service', 'call', '/unpause_physics', 'std_srvs/srv/Empty', '{}'],
                output='screen'
            )
        ]
    )

    # 3. 启动 Nav2 (延迟8秒)
    # 传递 map 路径，解决 'yaml_filename' is not initialized 报错
    navigation_bringup = TimerAction(
        period=8.0, 
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(scout_pkg, 'launch', 'navigation.launch.py')
                ),
                launch_arguments={
                    'use_sim_time': 'True',
                    'map': map_yaml_path,
                    'params_file': params_file_path,
                }.items()
            )
        ]
    )

    # 4. TF 补丁 (修复机器人变白)
    #tf_patch_node = Node(
    #   package='tf2_ros',
    #    executable='static_transform_publisher',
    #     name='base_footprint_to_base_link',
    #   arguments=['0', '0', '0', '0', '0', '0', 'base_footprint', 'base_link'],
    #    parameters=[{'use_sim_time': True}], 
    #    output='screen'
   # )

    # 5. 启动 RViz
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path, 
                   '--ros-args', '-p', 'use_sim_time:=True'],
        output='screen'
    )

    return LaunchDescription([
        headless_sim,
        unpause_physics,
        #tf_patch_node,
        navigation_bringup,
        rviz_node
    ])
    
