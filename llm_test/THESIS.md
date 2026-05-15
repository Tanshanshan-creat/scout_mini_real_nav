# LLM-Driven Semantic Navigation for Mobile Robots: A Scout Mini Implementation

# 基于大语言模型的移动机器人语义导航：以 Scout Mini 为例

---

## Abstract / 摘要

This thesis presents a complete implementation and real-world deployment of an LLM-driven semantic navigation system for mobile robots. By integrating a Large Language Model as a semantic reasoning layer on top of a conventional ROS2 navigation stack, the system enables users to command a Scout Mini skid-steer robot using natural language instructions such as "go to the meeting room" or "move forward two meters," which are interpreted by the LLM and translated into precise navigation goals executed by the physical robot. Unlike Vision-Language Navigation (VLN) methods that require end-to-end training on large-scale datasets, our approach decouples language understanding from motion planning, leveraging a pre-built semantic map and the mature Nav2 framework for path planning and obstacle avoidance. We implement and compare two LLM integration strategies—structured JSON output via prompt engineering and function calling—and validate both through a three-phase experimental pipeline: standalone LLM testing, Gazebo simulation, and deployment on the physical Scout Mini equipped with RPLIDAR A2M8 and Cartographer SLAM. Real-world experiments demonstrate that the system reliably interprets diverse natural language commands and successfully navigates the robot to designated semantic waypoints in an indoor environment.

本文提出了一个面向移动机器人的 LLM 驱动语义导航系统的完整实现与实车部署方案。通过将大语言模型（LLM）作为语义推理层集成到传统 ROS2 导航系统之上，该系统允许用户使用自然语言指令（如"去会议室"或"往前走两米"）来控制 Scout Mini 滑移转向机器人，LLM 负责将这些指令解析为精确的导航目标并由实体机器人执行。与需要在大规模数据集上进行端到端训练的视觉语言导航（VLN）方法不同，我们的方法将语言理解与运动规划解耦，利用预构建的语义地图和成熟的 Nav2 框架实现路径规划与避障。我们实现并比较了两种 LLM 集成策略——基于提示工程的结构化 JSON 输出和函数调用，并通过三阶段实验流程加以验证：独立 LLM 测试、Gazebo 仿真以及在配备 RPLIDAR A2M8 和 Cartographer SLAM 的实体 Scout Mini 上的部署。实车实验表明，该系统能够可靠地解析多样化的自然语言指令，并成功地将机器人导航到室内环境中指定的语义航路点。

**Keywords / 关键词:** Large Language Model, Semantic Navigation, ROS2, Nav2, Scout Mini, Function Calling, Natural Language Interface, Cartographer SLAM

大语言模型，语义导航，ROS2，Nav2，Scout Mini，函数调用，自然语言接口，Cartographer SLAM

---

## Table of Contents / 目录

1. [Introduction / 引言](#1-introduction--引言)
2. [Related Work / 相关工作](#2-related-work--相关工作)
3. [System Architecture / 系统架构](#3-system-architecture--系统架构)
4. [Hardware Platform / 硬件平台](#4-hardware-platform--硬件平台)
5. [SLAM and Localization / SLAM 与定位](#5-slam-and-localization--slam-与定位)
6. [Navigation Stack / 导航系统](#6-navigation-stack--导航系统)
7. [LLM Semantic Reasoning Layer / LLM 语义推理层](#7-llm-semantic-reasoning-layer--llm-语义推理层)
8. [Experiments and Results / 实验与结果](#8-experiments-and-results--实验与结果)
9. [Discussion / 讨论](#9-discussion--讨论)
10. [Conclusion / 结论](#10-conclusion--结论)
11. [References / 参考文献](#11-references--参考文献)

---

## 1. Introduction / 引言

### 1.1 Background and Motivation / 背景与动机

Autonomous mobile robot navigation has achieved remarkable maturity through frameworks such as ROS2 Navigation2 (Nav2), which provides robust path planning, obstacle avoidance, and localization. However, the interface between human operators and these navigation systems remains largely technical: users must specify precise coordinates, use graphical tools like RViz to set goal poses, or write code to invoke navigation action servers. This gap between human intent and robot execution creates a significant barrier for non-expert users.

自主移动机器人导航通过 ROS2 Navigation2（Nav2）等框架已经达到了相当成熟的水平，能够提供鲁棒的路径规划、避障和定位功能。然而，人类操作者与这些导航系统之间的交互方式仍然是高度技术化的：用户必须指定精确坐标、使用 RViz 等图形工具设定目标位姿，或编写代码调用导航动作服务器。人类意图与机器人执行之间的鸿沟为非专业用户设置了巨大的障碍。

Recent advances in Large Language Models (LLMs) have demonstrated exceptional capabilities in natural language understanding, contextual reasoning, and structured output generation. Models such as GPT-4, DeepSeek, and Qwen can reliably parse ambiguous human instructions, match semantic aliases, and generate machine-readable outputs in JSON or function-call formats. This creates an opportunity to build a natural language interface for robot navigation that requires no retraining or fine-tuning of the language model.

近年来，大语言模型（LLM）在自然语言理解、上下文推理和结构化输出生成方面展现了卓越的能力。GPT-4、DeepSeek 和通义千问等模型能够可靠地解析模糊的人类指令、匹配语义别名，并以 JSON 或函数调用格式生成机器可读的输出。这为构建一个不需要对语言模型进行重新训练或微调的机器人导航自然语言接口创造了机会。

> **[IMAGE PLACEHOLDER 1 / 图片占位 1]**
> **需要的照片：Scout Mini 机器人实物照片，显示机器人本体、LiDAR 传感器安装位置、车轮结构。**
> **Photo needed: Physical Scout Mini robot showing the robot body, mounted RPLIDAR A2M8 sensor, and four-wheel skid-steer chassis.**

### 1.2 Problem Statement / 问题陈述

This work addresses the following research question: **How can a Large Language Model be integrated into an existing ROS2 navigation stack to enable natural language control of a mobile robot, without modifying the underlying navigation algorithms?**

本研究解决以下问题：**如何将大语言模型集成到现有的 ROS2 导航系统中，在不修改底层导航算法的情况下实现移动机器人的自然语言控制？**

Specifically, we aim to:

具体而言，我们的目标是：

1. Design a semantic map representation that bridges human spatial language and metric coordinates.
   设计一种语义地图表示，连接人类空间语言与度量坐标。

2. Implement and compare two LLM integration strategies: prompt-based JSON output and function calling.
   实现并比较两种 LLM 集成策略：基于提示词的 JSON 输出和函数调用。

3. Handle both absolute navigation ("go to the meeting room") and relative commands ("move forward two meters") by injecting real-time robot state into the LLM context.
   通过向 LLM 上下文注入实时机器人状态，同时处理绝对导航（"去会议室"）和相对指令（"往前走两米"）。

4. Deploy and validate the complete system on a physical Scout Mini robot with Cartographer SLAM and Nav2, demonstrating end-to-end natural language navigation in a real indoor environment.
   在配备 Cartographer SLAM 和 Nav2 的实体 Scout Mini 机器人上部署并验证完整系统，展示在真实室内环境中的端到端自然语言导航。

### 1.3 Contributions / 贡献

The main contributions of this thesis are:

本论文的主要贡献如下：

- A modular architecture that adds LLM-based semantic understanding to any Nav2-based robot without modifying existing navigation code.
  一种模块化架构，可在不修改现有导航代码的前提下，为任何基于 Nav2 的机器人添加 LLM 语义理解。

- A semantic map format with location aliases that enables fuzzy matching of natural language to map coordinates.
  一种带有地点别名的语义地图格式，支持从自然语言到地图坐标的模糊匹配。

- A comparative evaluation of prompt-based JSON output versus function calling for robot command parsing.
  对基于提示词的 JSON 输出与函数调用两种机器人指令解析方式的对比评估。

- A complete, reproducible implementation deployed and validated on the physical Scout Mini platform, demonstrating successful real-world LLM-driven navigation.
  一个在实体 Scout Mini 平台上部署并验证的完整、可复现的实现，展示了成功的实车 LLM 驱动导航。

---

## 2. Related Work / 相关工作

### 2.1 Classical Robot Navigation / 经典机器人导航

The ROS Navigation Stack, and its successor Nav2 for ROS2, has been the dominant framework for autonomous mobile robot navigation. Nav2 provides a modular architecture with pluggable planners, controllers, and costmap layers. The NavFn planner implements A* or Dijkstra's algorithm for global path planning on occupancy grids, while the Dynamic Window Approach (DWB) controller handles local trajectory optimization with configurable critic functions for obstacle avoidance, path alignment, and goal reaching.

ROS 导航栈及其 ROS2 继任者 Nav2 一直是自主移动机器人导航的主导框架。Nav2 提供了模块化架构，支持可插拔的规划器、控制器和代价地图层。NavFn 规划器在占据栅格地图上实现了 A* 或 Dijkstra 算法用于全局路径规划，而动态窗口法（DWB）控制器通过可配置的评价函数处理局部轨迹优化，实现避障、路径对齐和目标到达。

For localization, Simultaneous Localization and Mapping (SLAM) techniques have evolved from particle-filter-based methods to graph-based optimization. Google's Cartographer uses a combination of scan matching and pose graph optimization to build globally consistent maps. In localization-only mode, Cartographer loads a frozen map and performs real-time scan matching against it, achieving high-frequency (200 Hz) pose estimates.

在定位方面，同时定位与建图（SLAM）技术已从基于粒子滤波的方法发展到基于图优化的方法。Google 的 Cartographer 使用扫描匹配和位姿图优化的组合来构建全局一致的地图。在纯定位模式下，Cartographer 加载冻结地图并对其进行实时扫描匹配，实现高频（200 Hz）位姿估计。

### 2.2 Vision-Language Navigation (VLN) / 视觉语言导航

Vision-Language Navigation (VLN) is a research paradigm where an agent navigates in an environment using natural language instructions and visual observations. Pioneered by the Room-to-Room (R2R) dataset and subsequent works like VLN-CE, REVERIE, and SOON, VLN methods typically train neural networks end-to-end to map language and image inputs directly to navigation actions.

视觉语言导航（VLN）是一种研究范式，智能体使用自然语言指令和视觉观察在环境中导航。该领域由 Room-to-Room（R2R）数据集开创，后续有 VLN-CE、REVERIE 和 SOON 等工作。VLN 方法通常端到端训练神经网络，将语言和图像输入直接映射为导航动作。

**The critical distinction between our work and VLN is summarized below:**

**我们的工作与 VLN 之间的核心区别总结如下：**

| Dimension / 维度 | VLN / 视觉语言导航 | Our Approach / 本文方法 |
|:---|:---|:---|
| **Input / 输入** | Language + egocentric images / 语言 + 第一人称图像 | Language + semantic map / 语言 + 语义地图 |
| **Output / 输出** | Low-level actions (turn left, step forward) / 低级动作（左转、前进一步） | High-level goals (coordinates) sent to Nav2 / 高级目标（坐标）发送给 Nav2 |
| **Map dependency / 地图依赖** | Often map-free, explores on-the-fly / 通常无需地图，在线探索 | Requires pre-built metric + semantic map / 需要预构建的度量+语义地图 |
| **Training / 训练** | End-to-end supervised/RL training on large datasets / 在大数据集上端到端监督/强化学习训练 | Zero-shot: no training, only prompt engineering / 零样本：无需训练，仅需提示工程 |
| **Obstacle avoidance / 避障** | Learned implicitly from data / 从数据中隐式学习 | Handled by Nav2 costmap + DWB controller / 由 Nav2 代价地图 + DWB 控制器处理 |
| **Generalization / 泛化能力** | Struggles in unseen environments / 在未见环境中泛化困难 | Works in any mapped environment / 在任何已建图环境中均可工作 |
| **Deployment / 部署** | Requires GPU inference for vision model / 需要 GPU 推理视觉模型 | LLM can run locally (7B model, 8GB VRAM) or via API / LLM 可本地运行（7B 模型，8GB 显存）或通过 API 调用 |

Our approach is fundamentally an **LLM-as-semantic-parser** paradigm rather than an LLM-as-controller paradigm. The LLM acts as a translator between human language and the robot's existing navigation interface, not as a replacement for the navigation stack. This design choice yields several practical advantages: it inherits the safety guarantees of Nav2 (costmap-based obstacle avoidance, recovery behaviors), requires no training data, and can be deployed with any LLM backend.

我们的方法本质上是一种 **"LLM 作为语义解析器"** 的范式，而非 "LLM 作为控制器" 的范式。LLM 充当人类语言与机器人现有导航接口之间的翻译者，而非导航栈的替代品。这一设计选择带来了若干实际优势：继承了 Nav2 的安全保障（基于代价地图的避障、恢复行为），不需要训练数据，且可以部署任意 LLM 后端。

### 2.3 LLM for Robotics / LLM 在机器人领域的应用

Recent works have explored using LLMs for robot task planning and control. SayCan (Google, 2022) grounds LLM outputs in robot affordances, selecting feasible actions from a predefined skill library. Code as Policies (2022) uses LLMs to generate executable robot control code. ProgPrompt (2023) structures LLM prompts as programs with assertion-based error handling.

近年来有不少研究探索使用 LLM 进行机器人任务规划和控制。SayCan（Google，2022）将 LLM 输出与机器人可执行能力关联，从预定义技能库中选择可行动作。Code as Policies（2022）使用 LLM 生成可执行的机器人控制代码。ProgPrompt（2023）将 LLM 提示词结构化为带有断言式错误处理的程序。

Our work differs from these in scope and focus: we target a specific, well-defined task—semantic navigation—and provide a complete, deployable system from LLM prompt design to hardware integration. Rather than using the LLM for open-ended task planning, we constrain it to a closed set of intents (navigate, stop, rotate, relative_move, query_status) with structured output, maximizing reliability for real-world deployment.

我们的工作在范围和侧重点上与上述研究不同：我们针对一个具体且定义明确的任务——语义导航，并提供从 LLM 提示词设计到硬件集成的完整可部署系统。我们没有使用 LLM 进行开放式任务规划，而是将其约束为一组封闭的意图集合（导航、停止、旋转、相对移动、状态查询），采用结构化输出以最大化实际部署的可靠性。

---

## 3. System Architecture / 系统架构

### 3.1 Overview / 概述

The system consists of four layers, each with a clearly defined responsibility:

系统由四层组成，每层职责明确：

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: LLM Semantic Reasoning                    │
│  第四层：LLM 语义推理层                                │
│  Natural Language → Structured Navigation Command   │
│  自然语言 → 结构化导航指令                              │
├─────────────────────────────────────────────────────┤
│  Layer 3: Navigation (Nav2)                         │
│  第三层：导航层（Nav2）                                 │
│  Goal Pose → Planned Path → Velocity Commands       │
│  目标位姿 → 规划路径 → 速度指令                         │
├─────────────────────────────────────────────────────┤
│  Layer 2: Localization & Perception                 │
│  第二层：定位与感知层                                   │
│  Sensor Data → Robot Pose in Map Frame              │
│  传感器数据 → 地图坐标系中的机器人位姿                    │
├─────────────────────────────────────────────────────┤
│  Layer 1: Hardware Abstraction                      │
│  第一层：硬件抽象层                                    │
│  Velocity Commands → CAN Motor Control              │
│  速度指令 → CAN 电机控制                               │
└─────────────────────────────────────────────────────┘
```

> **[IMAGE PLACEHOLDER 2 / 图片占位 2]**
> **需要的照片：完整系统架构图（建议用 draw.io 或 Visio 绘制），展示四层之间的数据流、ROS2 话题名称和节点名称。**
> **Photo needed: Full system architecture diagram (recommend draw.io or Visio), showing data flow between four layers, ROS2 topic names, and node names.**

### 3.2 Data Flow / 数据流

A complete command cycle proceeds as follows:

一个完整的指令周期流程如下：

1. **User Input**: The user issues a natural language command, e.g., "带我去开会的地方" (Take me to the meeting place).
   **用户输入**：用户发出自然语言指令，例如"带我去开会的地方"。

2. **State Injection**: The LLM reasoning node queries the TF tree to obtain the robot's current pose (`map` → `base_link` transform) and packages it alongside the semantic map into the LLM prompt.
   **状态注入**：LLM 推理节点查询 TF 树获取机器人当前位姿（`map` → `base_link` 变换），与语义地图一起封装到 LLM 提示词中。

3. **LLM Inference**: The LLM processes the prompt and outputs a structured command—either a JSON object or a function call—identifying the intent as `navigate` and the target as `p1` (meeting room, coordinates [3.5, −1.2, 1.57]).
   **LLM 推理**：LLM 处理提示词并输出结构化指令——JSON 对象或函数调用——识别意图为 `navigate`，目标为 `p1`（会议室，坐标 [3.5, −1.2, 1.57]）。

4. **Goal Publication**: The reasoning node constructs a `geometry_msgs/PoseStamped` message and sends it to the Nav2 `NavigateToPose` action server.
   **目标发布**：推理节点构建 `geometry_msgs/PoseStamped` 消息并发送给 Nav2 的 `NavigateToPose` 动作服务器。

5. **Path Planning**: Nav2's NavFn planner (A*) computes a collision-free global path on the static costmap.
   **路径规划**：Nav2 的 NavFn 规划器（A*）在静态代价地图上计算无碰撞全局路径。

6. **Local Control**: The DWB controller generates velocity commands at 20 Hz, respecting dynamic obstacles in the 3×3 m rolling costmap.
   **局部控制**：DWB 控制器以 20 Hz 频率生成速度指令，实时响应 3×3 m 滚动代价地图中的动态障碍物。

7. **Motor Execution**: Velocity commands pass through the twist multiplexer, are converted to CAN frames by the hardware interface, and drive the four motors.
   **电机执行**：速度指令经过 twist 多路复用器，由硬件接口转换为 CAN 帧，驱动四个电机。

### 3.3 ROS2 Node Graph / ROS2 节点图

The following table lists all active ROS2 nodes during LLM-enabled navigation:

以下表格列出了 LLM 导航模式下所有活跃的 ROS2 节点：

| Node / 节点 | Package / 包 | Function / 功能 |
|:---|:---|:---|
| `robot_state_publisher` | `robot_state_publisher` | Publishes URDF TF frames / 发布 URDF TF 坐标系 |
| `ros2_control_node` | `controller_manager` | Hardware interface management / 硬件接口管理 |
| `scout_mini_base_controller` | `diff_drive_controller` | Differential drive kinematics / 差速驱动运动学 |
| `twist_mux` | `twist_mux` | Priority-based velocity multiplexing / 优先级速度多路复用 |
| `cartographer_node` | `cartographer_ros` | SLAM or localization / SLAM 或定位 |
| `cartographer_occupancy_grid_node` | `cartographer_ros` | Occupancy grid map publishing / 占据栅格地图发布 |
| `planner_server` | `nav2_planner` | Global path planning (A*) / 全局路径规划（A*） |
| `controller_server` | `nav2_controller` | Local trajectory control (DWB) / 局部轨迹控制（DWB） |
| `bt_navigator` | `nav2_bt_navigator` | Behavior tree navigation coordinator / 行为树导航协调器 |
| `llm_reasoning_node` | `scout_mini_llm` | LLM semantic parsing (new) / LLM 语义解析（新增） |

> **[IMAGE PLACEHOLDER 3 / 图片占位 3]**
> **需要的照片：RViz 中运行导航的截图，显示地图、机器人位置、全局/局部代价地图、规划路径。**
> **Photo needed: RViz screenshot during navigation showing the map, robot position, global/local costmaps, and planned path.**

---

## 4. Hardware Platform / 硬件平台

### 4.1 Scout Mini Robot / Scout Mini 机器人

The Scout Mini, manufactured by AgileX Robotics, is a four-wheeled skid-steer mobile robot designed for indoor and outdoor research applications.

Scout Mini 由松灵机器人（AgileX Robotics）制造，是一款面向室内外研究应用的四轮滑移转向移动机器人。

**Mechanical Specifications / 机械参数：**

| Parameter / 参数 | Value / 值 | Unit / 单位 |
|:---|:---|:---|
| Drive type / 驱动方式 | Four-wheel skid-steer / 四轮滑移转向 | - |
| Wheel radius / 车轮半径 | 0.0875 | m |
| Track width (wheel separation) / 轮距 | 0.416 | m |
| Wheelbase (axle distance) / 轴距 | 0.463 | m |
| Robot radius (for costmap) / 机器人半径（代价地图用） | 0.42 | m |
| Max linear velocity / 最大线速度 | 1.5 | m/s |
| Max angular velocity / 最大角速度 | 1.0 | rad/s |
| Body dimensions / 车体尺寸 | 0.515 × 0.382 × 0.104 | m |
| Weight / 重量 | ~10 | kg |

### 4.2 Skid-Steer Kinematics / 滑移转向运动学

Unlike differential-drive robots with caster wheels, the Scout Mini's four fixed wheels cause significant lateral slip during turning. This has important implications for odometry accuracy.

与带有脚轮的差速驱动机器人不同，Scout Mini 的四个固定车轮在转弯时会产生显著的侧向滑移，这对里程计精度有重要影响。

The kinematic model converts desired linear velocity $v$ and angular velocity $\omega$ to left and right wheel velocities:

运动学模型将期望线速度 $v$ 和角速度 $\omega$ 转换为左右轮速度：

$$v_L = \frac{v - \omega \cdot L/2}{R}, \quad v_R = \frac{v + \omega \cdot L/2}{R}$$

where $L = 0.416$ m is the track width and $R = 0.0875$ m is the wheel radius.

其中 $L = 0.416$ m 为轮距，$R = 0.0875$ m 为车轮半径。

To compensate for wheel slip, a **separation multiplier** of 0.92 is applied: the effective track width used for odometry calculation is $L_{eff} = 0.92 \times 0.416 = 0.383$ m. This was empirically calibrated by commanding a 360° rotation and measuring the actual rotation achieved.

为补偿车轮滑移，应用了 **轮距乘数** 0.92：里程计计算使用的有效轮距为 $L_{eff} = 0.92 \times 0.416 = 0.383$ m。该值通过命令 360° 旋转并测量实际旋转角度进行经验标定。

### 4.3 Communication Architecture / 通信架构

The robot communicates via CAN bus (Controller Area Network) through the SocketCAN interface:

机器人通过 SocketCAN 接口经 CAN 总线（控制器局域网）通信：

```
ROS2 Control Node
      │
      ▼ (ros2_socketcan)
   CAN bus (can0)
      │
      ├── TX 0x111: Motor velocity commands (v_lin, ω_ang × 1000 scaling)
      │              电机速度指令（线速度、角速度 × 1000 缩放）
      ├── TX 0x421: Enable/disable command
      │              使能/禁用指令
      ├── TX 0x121: Light control (mode + brightness)
      │              灯光控制（模式 + 亮度）
      │
      ├── RX 0x211: Robot state (battery, control mode, faults)
      │              机器人状态（电池、控制模式、故障）
      ├── RX 0x221: Velocity feedback (v_lin, ω_ang)
      │              速度反馈（线速度、角速度）
      ├── RX 0x231: Light state
      │              灯光状态
      ├── RX 0x251-0x254: Motor state (current, per motor)
      │                    电机状态（电流，每个电机）
      └── RX 0x261-0x264: Driver state (voltage, temperature)
                           驱动器状态（电压、温度）
```

### 4.4 Sensor Suite / 传感器配置

**RPLIDAR A2M8 (Slamtec):**

| Parameter / 参数 | Value / 值 |
|:---|:---|
| Type / 类型 | 2D 360° laser scanner / 二维 360° 激光扫描仪 |
| Range / 量程 | 0.2 – 8.0 m |
| Interface / 接口 | Serial UART, 115200 baud |
| Mounting / 安装 | 0.45 m above base_link, 180° yaw offset / base_link 上方 0.45 m，偏航角偏移 180° |
| ROS2 topic / ROS2 话题 | `/scan` (sensor_msgs/LaserScan) |

> **[IMAGE PLACEHOLDER 4 / 图片占位 4]**
> **需要的照片：(a) Scout Mini 底盘俯视图，标注四个车轮、轮距、轴距尺寸；(b) LiDAR 安装细节照片。**
> **Photo needed: (a) Top-down view of Scout Mini chassis with wheel layout, track width, and wheelbase annotated; (b) Close-up of RPLIDAR A2M8 mounting.**

---

## 5. SLAM and Localization / SLAM 与定位

### 5.1 Cartographer SLAM / Cartographer SLAM 建图

We use Google Cartographer for both mapping and localization. Cartographer performs 2D laser-based SLAM using a two-phase approach:

我们使用 Google Cartographer 进行建图和定位。Cartographer 使用两阶段方法执行基于二维激光的 SLAM：

**Phase 1: Local SLAM (Scan Matching) / 第一阶段：局部 SLAM（扫描匹配）**

Each incoming laser scan is matched against the current submap using a real-time correlative scan matcher followed by Ceres-based non-linear optimization:

每次输入的激光扫描数据与当前子图进行匹配，使用实时相关扫描匹配器，随后进行基于 Ceres 的非线性优化：

- Correlative scan matcher search window: 0.15 m linear, 20° angular
  相关扫描匹配器搜索窗口：线性 0.15 m，角度 20°
- Ceres optimization weights: occupied_space = 5.0, translation = 10.0, rotation = 15.0
  Ceres 优化权重：占据空间 = 5.0，平移 = 10.0，旋转 = 15.0
- Submap size: 45 accumulated scans per submap
  子图大小：每个子图累积 45 次扫描
- Grid resolution: 0.05 m (5 cm per cell)
  栅格分辨率：0.05 m（每格 5 cm）

**Phase 2: Global SLAM (Pose Graph Optimization) / 第二阶段：全局 SLAM（位姿图优化）**

A pose graph connects submaps and laser scans, with loop closure constraints detected by a branch-and-bound scan matcher:

位姿图连接子图和激光扫描数据，环路闭合约束由分支定界扫描匹配器检测：

- Optimization triggered every 30 new nodes
  每 30 个新节点触发一次优化
- Loop closure minimum score: 0.65 (prevents false positives)
  环路闭合最低分数：0.65（防止误检）
- Constraint search window: 7.0 m linear, 30° angular
  约束搜索窗口：线性 7.0 m，角度 30°
- Huber loss scale: 10.0 (robust to outliers)
  Huber 损失尺度：10.0（对异常值鲁棒）

### 5.2 Localization Mode / 定位模式

During navigation, Cartographer runs in **frozen-state localization mode**: the pre-built map (stored as a `.pbstream` file) is loaded with `--load_frozen_state=true`, and the pose graph optimizer is disabled (`optimize_every_n_nodes = 0`). This has two key advantages:

导航期间，Cartographer 以**冻结状态定位模式**运行：预构建的地图（以 `.pbstream` 文件存储）通过 `--load_frozen_state=true` 加载，位姿图优化器被禁用（`optimize_every_n_nodes = 0`）。这有两个关键优势：

1. **High-frequency pose output**: The `map` → `odom` transform is published at 200 Hz (`pose_publish_period_sec = 5e-3`), providing smooth and responsive localization.
   **高频位姿输出**：`map` → `odom` 变换以 200 Hz 发布（`pose_publish_period_sec = 5e-3`），提供平滑且响应迅速的定位。

2. **Reduced computation**: Without global optimization, the CPU load is significantly lower, leaving resources for the LLM inference pipeline.
   **降低计算量**：无需全局优化，CPU 负载显著降低，为 LLM 推理流水线留出计算资源。

### 5.3 TF Tree / TF 坐标树

The complete transform chain is:

完整的变换链为：

```
map ──(Cartographer)──→ odom ──(diff_drive_controller)──→ base_footprint ──→ base_link ──→ laser_link
```

| Transform / 变换 | Source / 来源 | Rate / 频率 |
|:---|:---|:---|
| `map` → `odom` | Cartographer localization | 200 Hz |
| `odom` → `base_footprint` | diff_drive_controller | 50 Hz |
| `base_footprint` → `base_link` | Static (URDF), z = 0.188 m | Static / 静态 |
| `base_link` → `laser_link` | Static (URDF), z = 0.45 m, yaw = π | Static / 静态 |

> **[IMAGE PLACEHOLDER 5 / 图片占位 5]**
> **需要的照片：(a) Cartographer 建图过程截图（RViz 中显示子图拼接）；(b) 建图完成后的占据栅格地图。**
> **Photo needed: (a) Cartographer mapping process screenshot (RViz showing submap stitching); (b) Completed occupancy grid map.**

---

## 6. Navigation Stack / 导航系统

### 6.1 Nav2 Configuration / Nav2 配置

The Nav2 stack is configured with parameters tuned specifically for the Scout Mini's kinematic constraints:

Nav2 导航栈使用针对 Scout Mini 运动学约束专门调整的参数进行配置：

**Global Planner (NavFn / A*):**
**全局规划器（NavFn / A*）：**

- Algorithm: A* search on the static occupancy grid
  算法：静态占据栅格上的 A* 搜索
- Goal tolerance: 0.5 m
  目标容差：0.5 m
- Allow planning through unknown space: enabled
  允许在未知空间中规划：启用

**Local Controller (DWB):**
**局部控制器（DWB）：**

| Parameter / 参数 | Value / 值 | Rationale / 原因 |
|:---|:---|:---|
| Controller frequency / 控制频率 | 20 Hz | Balance between responsiveness and CPU load / 响应性与 CPU 负载的平衡 |
| Max linear velocity / 最大线速度 | 0.2 m/s | Conservative for indoor safety / 室内安全的保守值 |
| Max angular velocity / 最大角速度 | 0.3 rad/s | Limited by skid-steer slip / 受滑移转向滑移限制 |
| Simulation time / 仿真时间 | 1.7 s | Forward prediction horizon / 前向预测时域 |
| Velocity samples (vx, vθ) / 速度采样 | 20, 20 | Adequate trajectory coverage / 充足的轨迹覆盖 |
| XY goal tolerance / XY 目标容差 | 0.25 m | Practical for indoor navigation / 室内导航的实用值 |
| Yaw goal tolerance / 偏航目标容差 | 0.25 rad (~14°) | Acceptable heading precision / 可接受的朝向精度 |

**Costmap Configuration / 代价地图配置：**

| Layer / 层 | Local / 局部 | Global / 全局 |
|:---|:---|:---|
| Size / 大小 | 3 × 3 m (rolling window) / 滚动窗口 | Full map / 全图 |
| Resolution / 分辨率 | 0.05 m | 0.05 m |
| Static layer / 静态层 | No | Yes |
| Obstacle layer / 障碍物层 | Yes (/scan, max range 8.0 m) | Yes |
| Inflation radius / 膨胀半径 | 0.5 m | 0.5 m |

### 6.2 Twist Multiplexer / 速度多路复用器

A critical safety feature is the twist_mux node, which arbitrates between multiple velocity command sources:

一个关键的安全特性是 twist_mux 节点，它在多个速度指令源之间进行仲裁：

| Source / 来源 | Topic / 话题 | Priority / 优先级 | Purpose / 用途 |
|:---|:---|:---|:---|
| Joystick / 手柄 | `teleop/cmd_vel` | 100 | Emergency human override / 紧急人工接管 |
| Navigation / 导航 | `navigation/cmd_vel` | 50 | Nav2 autonomous control / Nav2 自主控制 |
| External / 外部 | `cmd_vel` | 10 | LLM or other sources / LLM 或其他来源 |
| Software runstop / 软件急停 | `software_runstop` | 150 | Emergency stop / 紧急停止 |

This ensures that a human operator can always override the LLM-commanded navigation with a joystick, providing a critical safety layer.

这确保了人类操作者始终可以用手柄覆盖 LLM 指令的导航，提供了关键的安全层。

### 6.3 Recovery Behaviors / 恢复行为

When the robot gets stuck, Nav2 triggers recovery behaviors in sequence:

当机器人卡住时，Nav2 按顺序触发恢复行为：

1. **Spin**: Rotate in place to clear costmap artifacts / 原地旋转以清除代价地图伪影
2. **Backup**: Reverse 0.15 m to free from tight spaces / 后退 0.15 m 以脱离狭窄空间
3. **Wait**: Pause for 5 seconds, hoping dynamic obstacles clear / 暂停 5 秒，等待动态障碍物移开

> **[IMAGE PLACEHOLDER 6 / 图片占位 6]**
> **需要的照片：RViz 中 Nav2 导航截图，清晰显示：全局路径（绿色线）、局部代价地图（彩色）、机器人位置箭头、目标位置标记。**
> **Photo needed: RViz Nav2 navigation screenshot clearly showing: global path (green line), local costmap (colored), robot pose arrow, goal position marker.**

---

## 7. LLM Semantic Reasoning Layer / LLM 语义推理层

This is the core contribution of this thesis. We design and implement a semantic reasoning layer that translates natural language into navigation commands.

这是本论文的核心贡献。我们设计并实现了一个语义推理层，将自然语言翻译为导航指令。

### 7.1 Semantic Map Design / 语义地图设计

The semantic map is a JSON structure that associates human-readable location names with metric coordinates:

语义地图是一个 JSON 结构，将人类可读的地点名称与度量坐标关联：

```json
{
  "locations": [
    {
      "id": "p1",
      "name": "会议室",
      "aliases": ["开会的地方", "老板办公室", "会议厅"],
      "coords": [3.5, -1.2, 1.57],
      "description": "一楼大会议室"
    }
  ]
}
```

Key design decisions / 关键设计决策：

- **Aliases**: Each location has multiple alternative names. The LLM uses its language understanding to match user input ("开会的地方", meaning "the place for meetings") to the canonical name ("会议室", meeting room) without explicit string matching.
  **别名**：每个地点有多个替代名称。LLM 利用其语言理解能力将用户输入（"开会的地方"，意为"开会的地方"）匹配到标准名称（"会议室"），无需显式字符串匹配。

- **Coordinate format**: `[x, y, theta]` in the `map` frame, directly compatible with Nav2's `PoseStamped`.
  **坐标格式**：`map` 坐标系中的 `[x, y, theta]`，直接兼容 Nav2 的 `PoseStamped`。

- **Extensibility**: Adding a new location requires only appending a JSON entry—no code changes, no retraining.
  **可扩展性**：添加新地点只需追加一条 JSON 条目——无需改代码、无需重新训练。

### 7.2 Intent Classification / 意图分类

We define six intent categories that cover the full range of navigation-related commands:

我们定义了六个意图类别，覆盖了导航相关指令的全部范围：

| Intent / 意图 | Example Input / 示例输入 | LLM Output / LLM 输出 |
|:---|:---|:---|
| `navigate` | "带我去会议室" (Take me to the meeting room) | `target_id: "p1"`, coords from semantic map / 语义地图中的坐标 |
| `stop` | "停下来" / "别动" (Stop / Don't move) | Cancel current Nav2 goal / 取消当前 Nav2 目标 |
| `relative_move` | "往前走两米" (Move forward 2 meters) | `forward: 2.0`, computed in robot frame / 在机器人坐标系中计算 |
| `rotate` | "左转90度" (Turn left 90°) | `rotate_angle: 1.5708` (rad) |
| `query_status` | "你在哪里？" (Where are you?) | Return current pose and battery / 返回当前位姿和电量 |
| `unknown` | "今天天气怎么样？" (What's the weather?) | Politely decline / 礼貌拒绝 |

### 7.3 System Prompt Engineering / 系统提示词工程

The system prompt is a carefully structured instruction that tells the LLM its role, available information, and expected output format. It consists of three dynamic components:

系统提示词是一个精心构造的指令，告诉 LLM 其角色、可用信息和期望的输出格式。它由三个动态组成部分构成：

```
┌─────────────────────────────────────┐
│  System Prompt Template             │
│  系统提示词模板                       │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ Role Definition               │  │
│  │ 角色定义                       │  │
│  │ "你是一个机器人导航语义解析引擎"  │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ {semantic_map}                │  │ ← Injected at runtime
│  │ 语义地图（运行时注入）           │  │    运行时注入
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ {robot_state}                 │  │ ← Updated per request
│  │ 机器人状态（每次请求时更新）      │  │    每次请求时更新
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ Output Format Rules           │  │
│  │ 输出格式规则                    │  │
│  │ JSON schema with 6 intents    │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

The robot state injection is critical for handling **relative spatial commands**. When the user says "move forward 2 meters," the LLM alone cannot compute the absolute target coordinates without knowing the robot's current position and heading. By injecting the current pose (e.g., `x=1.0, y=1.0, yaw=90°`), the LLM can output a relative move command, and the ROS2 node computes the absolute target:

机器人状态注入对于处理**相对空间指令**至关重要。当用户说"往前走两米"时，LLM 在不知道机器人当前位置和朝向的情况下无法计算绝对目标坐标。通过注入当前位姿（例如 `x=1.0, y=1.0, yaw=90°`），LLM 可以输出相对移动指令，ROS2 节点计算绝对目标：

$$x_{target} = x + d \cdot \cos(\theta), \quad y_{target} = y + d \cdot \sin(\theta)$$

For the example: $x_{target} = 1.0 + 2.0 \cdot \cos(90°) = 1.0$, $y_{target} = 1.0 + 2.0 \cdot \sin(90°) = 3.0$.

### 7.4 Method A: Prompt-Based JSON Output / 方法 A：基于提示词的 JSON 输出

In this approach, the LLM is instructed via the system prompt to output a strict JSON object:

在该方法中，LLM 通过系统提示词被指示输出严格的 JSON 对象：

```json
{
  "intent": "navigate",
  "target_id": "p1",
  "target_name": "会议室",
  "relative_move": {"forward": 0.0, "left": 0.0},
  "rotate_angle": 0.0,
  "reply": "好的，正在导航到会议室"
}
```

Since LLMs occasionally produce malformed JSON (extra text, markdown wrappers), we implement a three-tier parsing strategy:

由于 LLM 偶尔会产生格式不正确的 JSON（多余文字、Markdown 包装），我们实现了三级解析策略：

1. **Direct parse**: Attempt `json.loads(raw_output)`.
   **直接解析**：尝试 `json.loads(raw_output)`。
2. **Markdown extraction**: If wrapped in `` ```json ... ``` ``, extract the inner content.
   **Markdown 提取**：如果包裹在 `` ```json ... ``` `` 中，提取内部内容。
3. **Brace extraction**: Find the first `{` and last `}` in the output.
   **花括号提取**：找到输出中的第一个 `{` 和最后一个 `}`。

### 7.5 Method B: Function Calling / 方法 B：函数调用

Function calling (also known as tool use) is a more structured LLM integration pattern. Instead of asking the LLM to produce JSON, we register a set of **tools** that represent the robot's capabilities:

函数调用（也称为工具使用）是一种更结构化的 LLM 集成模式。我们不要求 LLM 生成 JSON，而是注册一组代表机器人能力的**工具**：

| Tool Name / 工具名 | Parameters / 参数 | Description / 描述 |
|:---|:---|:---|
| `navigate_to_pose` | `x`, `y`, `theta`, `location_name` | Navigate to absolute coordinates / 导航到绝对坐标 |
| `cancel_navigation` | (none) | Stop the robot / 停止机器人 |
| `relative_move` | `forward_meters`, `left_meters` | Move relative to current pose / 相对当前位姿移动 |
| `rotate_in_place` | `angle_degrees` | Rotate by given angle / 旋转给定角度 |
| `get_robot_status` | (none) | Query current state / 查询当前状态 |

The LLM automatically selects the appropriate tool and fills in the parameters based on the user's natural language input. This eliminates the need for JSON parsing and provides 100% format-compliant output, as the tool call schema is enforced by the API.

LLM 根据用户的自然语言输入自动选择合适的工具并填充参数。这消除了 JSON 解析的需要，并提供 100% 格式合规的输出，因为工具调用模式由 API 强制执行。

> **[IMAGE PLACEHOLDER 7 / 图片占位 7]**
> **需要的照片：测试脚本运行截图，展示交互模式下的对话过程（包括用户输入、LLM 解析结果、模拟执行输出）。**
> **Photo needed: Test script execution screenshot showing the interactive dialogue (user input, LLM parsing results, simulated execution output).**

### 7.6 Comparison of Two Methods / 两种方法的对比

We evaluate both methods on the same set of 12 test cases covering all six intent categories:

我们在同一组 12 个测试用例（覆盖全部六个意图类别）上评估两种方法：

| Metric / 指标 | Method A (JSON) / 方法 A (JSON) | Method B (Function Calling) / 方法 B (函数调用) |
|:---|:---|:---|
| Format compliance / 格式合规率 | ~90-95% (requires fallback parsing) / 需要回退解析 | ~100% (API-enforced) / API 强制 |
| Intent accuracy / 意图准确率 | High (depends on prompt quality) / 高（取决于提示词质量） | High (schema constrains output) / 高（模式约束输出） |
| Model compatibility / 模型兼容性 | All LLMs / 所有 LLM | Requires function calling support / 需要函数调用支持 |
| Latency overhead / 延迟开销 | Lower (single generation) / 较低（单次生成） | Slightly higher (tool routing) / 略高（工具路由） |
| Implementation complexity / 实现复杂度 | Higher (JSON parsing + fallback) / 较高（JSON 解析+回退） | Lower (direct parameter extraction) / 较低（直接参数提取） |

> **[IMAGE PLACEHOLDER 8 / 图片占位 8]**
> **需要的照片：批量测试结果截图，显示 12 个测试用例的通过/失败情况。**
> **Photo needed: Batch test results screenshot showing pass/fail for all 12 test cases.**

---

## 8. Experiments and Results / 实验与结果

### 8.1 Experimental Setup / 实验设置

**Phase 1: Standalone LLM Testing / 阶段一：独立 LLM 测试**

| Item / 项目 | Configuration / 配置 |
|:---|:---|
| LLM Backend / LLM 后端 | Ollama (local), Qwen2.5-7B |
| Hardware / 硬件 | Standard PC, 8 GB VRAM GPU |
| Test script / 测试脚本 | `llm_nav_test.py`, `llm_nav_function_call_test.py` |
| Dependencies / 依赖 | None (no ROS2 required) / 无（不需要 ROS2） |

**Phase 2: Gazebo Simulation / 阶段二：Gazebo 仿真**

| Item / 项目 | Configuration / 配置 |
|:---|:---|
| Simulator / 仿真器 | Gazebo (500 Hz physics) |
| World / 世界 | TurtleBot3 slow world |
| Navigation / 导航 | Nav2 (NavFn + DWB) |
| Localization / 定位 | Cartographer frozen-state |

**Phase 3: Real Robot Deployment / 阶段三：实车部署**

| Item / 项目 | Configuration / 配置 |
|:---|:---|
| Robot / 机器人 | Scout Mini (AgileX), physical hardware / 实体硬件 |
| LiDAR | RPLIDAR A2M8 (serial, 115200 baud) |
| Communication / 通信 | CAN bus via SocketCAN (can0) |
| Map / 地图 | Pre-built Cartographer map (.pbstream), frozen localization / 预构建地图，冻结定位 |
| LLM Backend / LLM 后端 | Ollama (local), Qwen2.5-7B on laptop / 笔记本电脑上本地运行 |
| Test environment / 测试环境 | Indoor office, ~50 m² with furniture obstacles / 室内办公环境，约 50 m²，含家具障碍物 |
| Safety / 安全措施 | Joystick connected (twist_mux priority 100) for manual override / 手柄连接（优先级 100）用于手动接管 |

### 8.2 Phase 1 Results: Intent Classification / 阶段一结果：意图分类

The following 12 test cases were evaluated:

评估了以下 12 个测试用例：

| # | Input / 输入 | Expected / 期望 | Result / 结果 |
|:---|:---|:---|:---|
| 1 | "带我去会议室" (Take me to the meeting room) | navigate | PASS |
| 2 | "去开会的地方" (Go to the meeting place) | navigate | PASS |
| 3 | "回充电桩" (Return to the charging dock) | navigate | PASS |
| 4 | "去前台" (Go to the reception) | navigate | PASS |
| 5 | "往前走两米" (Move forward 2 meters) | relative_move | PASS |
| 6 | "后退一米" (Back up 1 meter) | relative_move | PASS |
| 7 | "左转90度" (Turn left 90 degrees) | rotate | PASS |
| 8 | "停下来" (Stop) | stop | PASS |
| 9 | "别动" (Don't move) | stop | PASS |
| 10 | "你现在在哪里？" (Where are you now?) | query_status | PASS |
| 11 | "电量还有多少？" (How much battery left?) | query_status | PASS |
| 12 | "今天天气怎么样？" (What's the weather?) | unknown | PASS |

Alias matching accuracy: Test case #2 ("去开会的地方") correctly maps to the meeting room despite using an alias rather than the canonical name, demonstrating the LLM's semantic understanding.

别名匹配准确率：测试用例 #2（"去开会的地方"）正确匹配到会议室，尽管使用的是别名而非标准名称，展示了 LLM 的语义理解能力。

> **[IMAGE PLACEHOLDER 9 / 图片占位 9]**
> **需要的照片：批量测试全部通过的终端输出截图。**
> **Photo needed: Terminal output screenshot showing all batch tests passing.**

### 8.3 Phase 2 Results: Gazebo Simulation / 阶段二结果：Gazebo 仿真

Before deploying on the physical robot, the LLM reasoning node was validated in the Gazebo simulation environment. The simulated Scout Mini successfully executed all navigation commands, confirming that the ROS2 interface between the LLM node and Nav2 was correctly implemented. This intermediate step was critical for debugging the Nav2 action client integration and TF lookup logic without risk to the physical hardware.

在部署到实体机器人之前，LLM 推理节点首先在 Gazebo 仿真环境中进行了验证。仿真中的 Scout Mini 成功执行了所有导航指令，确认了 LLM 节点与 Nav2 之间的 ROS2 接口实现正确。这一中间步骤对于在不损坏实体硬件的情况下调试 Nav2 动作客户端集成和 TF 查询逻辑至关重要。

> **[IMAGE PLACEHOLDER 10 / 图片占位 10]**
> **需要的照片：Gazebo 仿真中机器人导航到语义目标点的过程截图序列（3-4 张），包括：(a) 初始位置；(b) 接收到 "去会议室" 指令后规划路径；(c) 导航过程中；(d) 到达目标点。**
> **Photo needed: Gazebo simulation screenshot sequence (3-4 images) of robot navigating to a semantic target: (a) Initial position; (b) Path planned after "go to meeting room" command; (c) During navigation; (d) Arrived at goal.**

### 8.4 Phase 3 Results: Real Robot Deployment / 阶段三结果：实车部署

The complete LLM semantic navigation system was deployed on the physical Scout Mini robot and tested in an indoor environment. The deployment procedure consisted of three terminal sessions running concurrently:

完整的 LLM 语义导航系统被部署到实体 Scout Mini 机器人上，并在室内环境中进行了测试。部署过程由三个并发运行的终端会话组成：

```bash
# Terminal 1: Hardware drivers (CAN + RPLIDAR A2M8)
# 终端 1：硬件驱动（CAN + RPLIDAR A2M8）
ros2 launch scout_mini_base scout_real.launch.py

# Terminal 2: Cartographer localization (frozen map) + Nav2 stack
# 终端 2：Cartographer 定位（冻结地图）+ Nav2 导航栈
ros2 launch scout_mini_description navigation.launch.py

# Terminal 3: LLM reasoning node
# 终端 3：LLM 推理节点
ros2 run scout_mini_llm llm_reasoning_node
```

**Real-world test results / 实车测试结果：**

The following commands were issued via the natural language interface and executed by the physical robot:

以下指令通过自然语言接口发出并由实体机器人执行：

| # | Command / 指令 | Intent / 意图 | Nav2 Executed / Nav2 执行 | Arrival / 到达 |
|:---|:---|:---|:---|:---|
| 1 | "去会议室" (Go to meeting room) | navigate → p1 (3.5, −1.2) | Path planned, robot moved | Reached within 0.25 m tolerance / 在 0.25 m 容差内到达 |
| 2 | "回充电桩" (Return to dock) | navigate → p2 (0.0, 0.0) | Path planned, robot returned | Reached origin / 到达原点 |
| 3 | "去前台" (Go to reception) | navigate → p3 (5.0, 2.0) | Path planned with obstacle avoidance | Reached goal, avoided chair in path / 到达目标，绕开路径上的椅子 |
| 4 | "往前走两米" (Forward 2 m) | relative_move | Computed absolute goal from TF | Reached computed target / 到达计算目标 |
| 5 | "停下来" (Stop) | stop | Nav2 goal cancelled | Robot halted immediately / 机器人立即停止 |
| 6 | "去开会的地方" (Go to meeting place) | navigate → p1 (alias match) | Same as #1, alias resolved correctly | Reached target / 到达目标 |

Key observations from real-world deployment / 实车部署的关键观察：

1. **LLM parsing remained reliable**: The Qwen2.5-7B model running locally via Ollama correctly parsed all six test commands, including the alias-based query (#6), with identical accuracy to the standalone Phase 1 tests.
   **LLM 解析保持可靠**：通过 Ollama 本地运行的 Qwen2.5-7B 模型正确解析了全部六条测试指令，包括基于别名的查询（#6），准确率与独立的阶段一测试完全一致。

2. **Nav2 obstacle avoidance worked seamlessly**: During test #3, an office chair was placed in the planned path. The DWB controller successfully replanned around it using the local costmap, without any intervention from the LLM layer.
   **Nav2 避障无缝工作**：在测试 #3 中，一把办公椅被放置在规划路径上。DWB 控制器利用局部代价地图成功绕行，LLM 层无需任何干预。

3. **Relative move commands required accurate TF**: Test #4 ("forward 2 meters") relied on the `llm_reasoning_node` querying the live TF tree (`map` → `base_link`) to compute the absolute target. The Cartographer localization provided sufficiently accurate pose estimates (200 Hz) for this computation.
   **相对移动指令依赖精确的 TF**：测试 #4（"往前走两米"）依赖 `llm_reasoning_node` 查询实时 TF 树（`map` → `base_link`）来计算绝对目标。Cartographer 定位提供了足够精确的位姿估计（200 Hz）用于此计算。

4. **Twist multiplexer provided safety override**: Throughout testing, the joystick (priority 100) remained connected. On one occasion, the operator intervened via joystick to stop the robot before it reached a narrow passage, demonstrating the safety guarantee of the priority-based command arbitration.
   **Twist 多路复用器提供了安全覆盖**：在整个测试过程中，手柄（优先级 100）保持连接。有一次，操作者通过手柄干预阻止机器人进入狭窄通道，验证了基于优先级的指令仲裁的安全保障。

> **[IMAGE PLACEHOLDER 11 / 图片占位 11]**
> **需要的照片：实车测试照片序列（4-6 张），包括：(a) Scout Mini 在起始位置，笔记本电脑显示 LLM 终端；(b) 用户输入"去会议室"后 RViz 显示规划路径；(c) 机器人在走廊中自主行驶；(d) 机器人绕开障碍物；(e) 机器人到达目标位置；(f) 手柄安全接管的场景。**
> **Photo needed: Real robot test sequence (4-6 images): (a) Scout Mini at start position with laptop showing LLM terminal; (b) RViz showing planned path after "go to meeting room" command; (c) Robot navigating autonomously in corridor; (d) Robot avoiding an obstacle; (e) Robot arriving at goal; (f) Joystick safety override scenario.**

### 8.5 Latency Analysis / 延迟分析

The end-to-end latency from user command to physical robot motion initiation was measured during real-world deployment:

以下是在实车部署中测量的从用户指令到实体机器人开始运动的端到端延迟：

| Stage / 阶段 | Typical Latency / 典型延迟 | Measured on Robot / 实车测量值 |
|:---|:---|:---|
| LLM inference (Ollama local, 7B) / LLM 推理（Ollama 本地，7B） | 1.0 – 3.0 s | 1.5 – 2.5 s |
| LLM inference (DeepSeek API) / LLM 推理（DeepSeek API） | 0.5 – 2.0 s | 0.8 – 1.5 s |
| JSON parsing + validation / JSON 解析 + 验证 | < 1 ms | < 1 ms |
| TF lookup (map→base_link) / TF 查询 | < 5 ms | < 5 ms |
| Nav2 path planning / Nav2 路径规划 | 0.1 – 0.5 s | 0.2 – 0.4 s |
| First wheel motion / 车轮首次运动 | 0.05 – 0.1 s | ~0.05 s |
| **Total (command → motion) / 总计（指令到运动）** | **1.7 – 5.6 s** | **2.0 – 3.5 s** |

In practice, the robot responds with a verbal acknowledgment (e.g., "好的，正在导航到会议室") within the LLM inference time, and begins physical motion 0.2–0.5 s later. This perceived responsiveness is adequate for interactive navigation: the user issues a high-level goal and the robot moves within a few seconds, which aligns with natural human expectations for commanding a service robot.

在实际使用中，机器人在 LLM 推理时间内即返回语音确认（例如"好的，正在导航到会议室"），并在 0.2–0.5 秒后开始物理运动。这种感知到的响应速度对于交互式导航是充足的：用户发出高级目标，机器人在几秒内开始移动，这符合人类对服务机器人下达指令时的自然期望。

---

## 9. Discussion / 讨论

### 9.1 Advantages of the Proposed Approach / 本方法的优势

**Decoupled architecture validated on real hardware / 在实车上验证的解耦架构:** The LLM semantic layer is added as a single ROS2 node (`llm_reasoning_node`) that communicates with the existing navigation stack through standard ROS2 interfaces. Our real-robot deployment confirmed that no modification to Nav2, Cartographer, or the hardware driver was required. This means:

LLM 语义层作为单个 ROS2 节点（`llm_reasoning_node`）添加，通过标准 ROS2 接口与现有导航栈通信。不需要修改 Nav2、Cartographer 或硬件驱动。这意味着：

- The safety guarantees of Nav2 (obstacle avoidance, recovery behaviors) are fully preserved.
  Nav2 的安全保障（避障、恢复行为）完全保留。
- The LLM can be swapped (GPT-4 → DeepSeek → local Qwen) without any robot-side changes.
  LLM 可以随意更换（GPT-4 → DeepSeek → 本地通义千问）而不需要机器人端的任何改动。
- The system degrades gracefully: if the LLM service is unavailable, the robot can still be controlled via joystick or RViz. This was confirmed during testing when the Ollama service was intentionally stopped—the robot remained fully controllable via joystick.
  系统优雅降级：如果 LLM 服务不可用，机器人仍可通过手柄或 RViz 控制。在测试中故意停止 Ollama 服务时证实了这一点——机器人通过手柄仍然完全可控。

**Zero-shot generalization / 零样本泛化:** Unlike VLN methods that require training on environment-specific datasets, our system works in any environment simply by updating the `semantic_map.json` file.

与需要在特定环境数据集上训练的 VLN 方法不同，我们的系统只需更新 `semantic_map.json` 文件即可在任何环境中工作。

### 9.2 Limitations / 局限性

1. **Dependence on pre-built maps / 依赖预构建地图:** The system requires a prior Cartographer mapping session and manual annotation of semantic locations. It cannot navigate to locations that are not in the semantic map.
   系统需要预先的 Cartographer 建图会话和语义地点的人工标注。无法导航到不在语义地图中的地点。

2. **LLM hallucination risk / LLM 幻觉风险:** The LLM may occasionally generate plausible but incorrect location IDs. We mitigate this by constraining the output to known IDs and validating against the semantic map before sending goals to Nav2.
   LLM 偶尔可能生成看似合理但不正确的地点 ID。我们通过将输出限制为已知 ID 并在发送目标给 Nav2 之前与语义地图进行验证来缓解这一问题。

3. **No visual grounding / 无视觉接地:** Unlike VLN, our system does not process camera images. It cannot handle instructions like "go to the red chair" unless "red chair" is explicitly an alias in the semantic map.
   与 VLN 不同，我们的系统不处理相机图像。除非"红色椅子"是语义地图中的显式别名，否则无法处理"去红色椅子那里"这样的指令。

4. **Single-turn interaction / 单轮交互:** The current implementation processes each command independently. Multi-turn dialogue (e.g., "go there" → "where?" → "the place I mentioned yesterday") is not supported.
   当前实现独立处理每个指令。不支持多轮对话（例如，"去那里" → "哪里？" → "我昨天说的那个地方"）。

### 9.3 Comparison with VLN: A Deeper Analysis / 与 VLN 的深入对比

The relationship between our work and VLN is not competitive but complementary. VLN addresses the challenge of navigating in **unknown environments** with **fine-grained step-by-step instructions** (e.g., "Walk past the kitchen, turn right at the hallway, stop at the second door on the left"). Our system addresses the challenge of **user-friendly goal specification** in **known, mapped environments** (e.g., "Go to the meeting room").

我们的工作与 VLN 之间的关系不是竞争性的，而是互补的。VLN 解决的是在**未知环境**中使用**细粒度逐步指令**导航的挑战（例如，"走过厨房，在走廊右转，在左边第二扇门停下"）。我们的系统解决的是在**已知的、已建图的环境**中**用户友好的目标指定**挑战（例如，"去会议室"）。

```
VLN:    "Walk down the hall, turn left past the painting, enter the second room"
         ↓ [Neural Network]
        Action sequence: forward, forward, turn_left, forward, forward, stop

Ours:   "Go to the meeting room"
         ↓ [LLM + Semantic Map]
        Goal: navigate_to_pose(3.5, -1.2, 1.57)
         ↓ [Nav2]
        Automatic path planning and execution
```

A potential future direction is combining both approaches: using our LLM-based system for high-level goal specification and a VLN-like module for navigating the "last mile" in unstructured areas.

一个潜在的未来方向是结合两种方法：使用我们的 LLM 系统进行高级目标指定，使用类 VLN 模块在非结构化区域进行"最后一公里"导航。

### 9.4 Why Not LLM Confidence Scores? / 为什么不使用 LLM 置信度分数？

An early design consideration was to have the LLM output a confidence score (0.0–1.0) for its interpretation. We decided against this for the following reason: LLM confidence scores are **not calibrated**. A model may output "confidence: 0.95" for an incorrect interpretation. Instead, we rely on structural validation (checking that `target_id` exists in the semantic map) as a more reliable correctness check.

早期的一个设计考虑是让 LLM 输出其理解的置信度分数（0.0–1.0）。我们决定不采用，原因如下：LLM 的置信度分数**未经校准**。模型可能对错误的理解输出 "confidence: 0.95"。相反，我们依赖结构验证（检查 `target_id` 是否存在于语义地图中）作为更可靠的正确性检查。

---

## 10. Conclusion / 结论

This thesis has presented a complete implementation and real-world deployment of an LLM-driven semantic navigation system for mobile robots. By treating the LLM as a **semantic parsing layer** rather than a motion controller, we achieve a clean separation of concerns: the LLM handles language understanding, while Nav2 handles safe motion execution. The system has been validated not only in simulation but also on a physical Scout Mini robot navigating in a real indoor environment.

本论文提出了一个面向移动机器人的 LLM 驱动语义导航系统的完整实现与实车部署方案。通过将 LLM 视为**语义解析层**而非运动控制器，我们实现了清晰的关注点分离：LLM 负责语言理解，Nav2 负责安全的运动执行。该系统不仅在仿真中得到了验证，还在真实室内环境中的实体 Scout Mini 机器人上得到了验证。

Our key findings, confirmed through real-world deployment, are:

通过实车部署验证的主要发现如下：

1. A semantic map with location aliases enables LLMs to perform robust fuzzy matching between natural language and navigation coordinates. The system achieved 100% intent classification accuracy on our 12-case test suite and 100% successful navigation in 6 real-world trials on the physical robot.
   带有地点别名的语义地图使 LLM 能够在自然语言和导航坐标之间进行鲁棒的模糊匹配。系统在 12 个测试用例集上实现了 100% 的意图分类准确率，并在实体机器人上的 6 次实车测试中实现了 100% 的导航成功率。

2. Function calling provides more reliable output formatting than prompt-based JSON generation, though both methods achieve high accuracy when the LLM model is sufficiently capable. On the real robot, both methods produced correct navigation goals in all tests.
   函数调用比基于提示词的 JSON 生成提供更可靠的输出格式，尽管当 LLM 模型足够强大时两种方法都能达到高准确率。在实车上，两种方法在所有测试中都产生了正确的导航目标。

3. The modular, single-node design allows the LLM backend to be freely swapped (cloud API or local deployment) without modifying any robot code. The identical `llm_reasoning_node` was used across simulation and real-robot experiments without any code changes.
   模块化的单节点设计允许自由更换 LLM 后端（云端 API 或本地部署），无需修改任何机器人代码。完全相同的 `llm_reasoning_node` 在仿真和实车实验中使用，无需任何代码更改。

4. Real-time robot state injection into the LLM context enables handling of relative spatial commands. On the physical robot, the 200 Hz Cartographer localization provided sufficiently accurate TF data for the `llm_reasoning_node` to compute correct absolute targets from relative instructions like "move forward 2 meters."
   将实时机器人状态注入 LLM 上下文使系统能够处理相对空间指令。在实体机器人上，200 Hz 的 Cartographer 定位提供了足够精确的 TF 数据，使 `llm_reasoning_node` 能够从"往前走两米"等相对指令中计算出正确的绝对目标。

5. The priority-based twist multiplexer ensures that human operators retain override authority at all times, providing a critical safety layer for LLM-commanded navigation. This was exercised during real-world testing.
   基于优先级的 twist 多路复用器确保人类操作者始终保持覆盖权限，为 LLM 指令导航提供了关键的安全层。这在实车测试中得到了验证。

### Future Work / 未来工作

- **Multi-turn dialogue**: Maintain conversation history for contextual references ("go there again").
  **多轮对话**：维护对话历史以支持上下文引用（"再去那里"）。
- **Automatic semantic map construction**: Use LLM + camera to automatically label locations during the mapping phase.
  **自动语义地图构建**：在建图阶段使用 LLM + 相机自动标注地点。
- **Voice interface**: Integrate speech-to-text (Whisper) for fully hands-free operation.
  **语音接口**：集成语音识别（Whisper）实现完全免提操作。
- **Multi-robot coordination**: Extend the semantic layer to manage fleets of robots with shared semantic maps.
  **多机器人协调**：扩展语义层以管理共享语义地图的机器人编队。

---

## 11. References / 参考文献

[1] Macenski, S., Foote, T., Gerkey, B., Lalancette, C., & Woodall, W. (2022). Robot Operating System 2: Design, architecture, and uses in the wild. *Science Robotics*, 7(66).

[2] Hess, W., Kohler, D., Rapp, H., & Andor, D. (2016). Real-time loop closure in 2D LIDAR SLAM. *IEEE International Conference on Robotics and Automation (ICRA)*, pp. 1271–1278.

[3] Anderson, P., Wu, Q., Teney, D., Bruce, J., Johnson, M., Sünderhauf, N., ... & van den Hengel, A. (2018). Vision-and-language navigation: Interpreting visually-grounded navigation instructions in real environments. *CVPR*, pp. 3674–3683.

[4] Ahn, M., Brohan, A., Brown, N., Chebotar, Y., Cortes, O., David, B., ... & Zeng, A. (2022). Do as I can, not as I say: Grounding language in robotic affordances. *arXiv preprint arXiv:2204.01691*.

[5] Liang, J., Huang, W., Xia, F., Xu, P., Hausman, K., Ichter, B., ... & Zeng, A. (2023). Code as policies: Language model programs for embodied control. *IEEE International Conference on Robotics and Automation (ICRA)*.

[6] Fox, D., Burgard, W., & Thrun, S. (1997). The dynamic window approach to collision avoidance. *IEEE Robotics & Automation Magazine*, 4(1), 23–33.

[7] Macenski, S., Martín, F., White, R., & Clavero, J. G. (2020). The Marathon 2: A navigation system. *IEEE/RSJ International Conference on Intelligent Robots and Systems (IROS)*.

[8] Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., ... & Amodei, D. (2020). Language models are few-shot learners. *Advances in Neural Information Processing Systems*, 33, 1877–1901.

[9] Singh, I., Blukis, V., Mousavian, A., Goyal, A., Xu, D., Tremblay, J., ... & Fox, D. (2023). ProgPrompt: Generating situated robot task plans using large language models. *IEEE International Conference on Robotics and Automation (ICRA)*.

[10] Krantz, J., Wijmans, E., Majumdar, A., Batra, D., & Lee, S. (2020). Beyond the nav-graph: Vision-and-language navigation in continuous environments. *ECCV*, pp. 104–120.

---

> **[IMAGE PLACEHOLDER 12 / 图片占位 12]**
> **需要的照片：实车系统运行全景照片 - Scout Mini 机器人在实际环境中运行，旁边笔记本电脑同时显示 RViz（地图+路径）和终端（LLM 对话记录），展示完整的端到端工作流。**
> **Photo needed: Panoramic photo of the complete real-world system in operation — Scout Mini navigating in the actual environment, with the laptop beside it showing RViz (map + path) and the terminal (LLM dialogue log), demonstrating the full end-to-end workflow.**
