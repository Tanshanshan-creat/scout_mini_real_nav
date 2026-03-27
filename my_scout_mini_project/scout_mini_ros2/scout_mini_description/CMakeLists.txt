cmake_minimum_required(VERSION 3.5)
project(scout_mini_description)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(urdf REQUIRED)
find_package(rviz2 REQUIRED)
find_package(robot_state_publisher REQUIRED)

# =========================================================
# 【核心修复】必须把 worlds 和 maps 文件夹也安装过去！
# 否则 Gazebo 找不到世界文件，Nav2 找不到地图文件
# =========================================================
install(
  DIRECTORY launch meshes rviz urdf config worlds maps
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
