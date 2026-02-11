import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
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
        package='sllidar_ros2',       # 思岚官方驱动包名
        executable='sllidar_node',    # 节点可执行文件名
        name='sllidar_node',
        parameters=[{
            'channel_type': 'serial',
            'serial_port': '/dev/ttyUSB0',  # 请确认你的雷达端口
            'serial_baudrate': 115200,      # 【关键】A2M8 的波特率是 115200
            'frame_id': 'laser_link',       # 必须与 URDF 中的 link 名字一致
            'inverted': False,              # 如果雷达倒装，这里设为 True
            'angle_compensate': True,       # 开启角度补偿
            'scan_mode': 'Sensitivity'      # A2M8 可选 Standard 或 Sensitivity
        }],
        output='screen'
    )

    # 4. 这里的 TF 发布通常在 base_launch.py 里通过 robot_state_publisher 发布了
    # 只要 URDF 里有 laser_link 的 joint 定义，tf 树就是完整的

    return LaunchDescription([
        base_driver,
        lidar_node
    ])
