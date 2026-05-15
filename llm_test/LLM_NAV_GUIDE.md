# Scout Mini + LLM 语义导航 - 从零开始的完整指南

> 本文档面向 LLM 零基础读者，从原理到实操一步步讲清楚。

---

## 目录

1. [你现在有什么](#1-你现在有什么)
2. [我们要做什么](#2-我们要做什么)
3. [LLM 基础原理 (5 分钟入门)](#3-llm-基础原理)
4. [整体架构设计](#4-整体架构设计)
5. [仿真流程 - 3 个阶段](#5-仿真流程)
6. [阶段一：纯 LLM 测试 (今天就能跑)](#6-阶段一纯-llm-测试)
7. [阶段二：LLM + ROS2 仿真](#7-阶段二llm--ros2-仿真)
8. [阶段三：LLM + 真实机器人](#8-阶段三llm--真实机器人)
9. [两种实现方式对比](#9-两种实现方式对比)
10. [常见问题](#10-常见问题)

---

## 1. 你现在有什么

你的 Scout Mini 项目已经有完整的导航能力：

```
用户在 RViz 中点目标点
        │
        ▼
   Nav2 (路径规划)
        │
        ▼
  Cartographer (定位)  +  LiDAR (感知)
        │
        ▼
  Scout Mini 底盘执行运动
```

**已有能力：**
- Cartographer 建图 + 定位
- Nav2 路径规划 + 避障
- 真实硬件驱动 (CAN 通信)
- Gazebo 仿真环境

**缺少的：** 用自然语言控制机器人（"去会议室" → 机器人自己过去）

---

## 2. 我们要做什么

加一层 "语义理解层"，让用户说人话，机器人听得懂：

```
用户说: "去会议室"
        │
        ▼
  ┌─────────────────┐
  │  LLM 语义解析层  │  ← 新增的部分
  │  "会议室" → (3.5, -1.2) │
  └─────────────────┘
        │
        ▼
   Nav2 (路径规划)      ← 已有的
        │
        ▼
   机器人执行运动        ← 已有的
```

**核心思路：LLM 只负责 "理解" 和 "翻译"，不负责控制机器人。**

---

## 3. LLM 基础原理

### 3.1 什么是 LLM？

LLM (Large Language Model, 大语言模型) 就是 ChatGPT / 通义千问 / DeepSeek 背后的技术。

**你可以理解为：一个超级厉害的 "文字接龙" 程序。**

```
你输入: "中国的首都是"
LLM 输出: "北京"
```

它不是查数据库，而是从海量文本中 "学会" 了语言规律。

### 3.2 我们怎么用 LLM？

我们用 LLM 做一件事：**把人话翻译成机器人能理解的指令。**

```
输入: "带我去开会的地方"
      ↓ LLM 翻译
输出: {"intent": "navigate", "target_id": "p1", "coords": [3.5, -1.2, 1.57]}
```

### 3.3 三个关键概念

#### System Prompt (系统提示词)
告诉 LLM "你是谁、你该怎么做" 的一段话。就像给新员工的工作手册。

```
"你是一个机器人导航引擎。已知地图上有这些地点: [...]
用户说话后，请输出 JSON 格式的导航命令。"
```

#### 语义地图 (Semantic Map)
一个 JSON 文件，把地图上的坐标和人类语言对应起来：

```json
{
  "id": "p1",
  "name": "会议室",
  "aliases": ["开会的地方", "老板办公室"],
  "coords": [3.5, -1.2, 1.57]
}
```

LLM 看到这个就知道 "开会的地方" = 坐标 (3.5, -1.2)。

#### Function Calling (函数调用)
一种更高级的用法。你预先定义机器人能做的动作（函数），LLM 直接"调用"这些函数：

```
用户: "去会议室"
LLM 调用: navigate_to_pose(x=3.5, y=-1.2, theta=1.57)
```

不需要你手动解析 JSON，LLM 直接告诉你该调哪个函数、传什么参数。

### 3.4 为什么 LLM 适合做这件事？

| 传统方法 | LLM 方法 |
|---------|---------|
| 需要穷举所有说法: "去会议室"、"到会议室"、"前往会议室"... | LLM 自动理解各种说法 |
| 新增地点 = 改代码 | 新增地点 = 改 JSON 配置 |
| 无法处理模糊指令 | "去那个开会的地方" 也能理解 |

---

## 4. 整体架构设计

### 4.1 最终目标架构

```
┌──────────────────────────────────────────────────────┐
│                    用户语音/文字输入                      │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│              llm_reasoning_node (ROS2 节点)           │
│                                                      │
│  1. 接收用户输入                                       │
│  2. 从 TF 树获取机器人当前位置                           │
│  3. 加载语义地图                                       │
│  4. 拼接 System Prompt + 用户输入                      │
│  5. 调用 LLM API                                     │
│  6. 解析 LLM 返回的 JSON / Function Call               │
│  7. 计算目标坐标                                       │
│  8. 发送 Nav2 Goal                                    │
└───────┬──────────────────────────────────┬────────────┘
        │                                  │
        ▼                                  ▼
┌───────────────┐                ┌──────────────────┐
│   LLM API     │                │     Nav2         │
│ (云端或本地)    │                │  (路径规划+控制)   │
└───────────────┘                └──────────────────┘
```

### 4.2 你的程序需要改成分布式吗？

**不需要大改！** 只需要加一个 ROS2 节点：

```
现有节点:                        新增节点:
├── scout_mini_base              ├── llm_reasoning_node  ← 只加这一个
├── cartographer_node
├── nav2 各节点
└── ...
```

这个节点通过 ROS2 话题/服务和已有系统通信，完全解耦，不影响已有代码。

---

## 5. 仿真流程

我们分 3 个阶段，由简到难，每一步都能独立验证：

```
阶段一 (今天)           阶段二 (1-2周)          阶段三 (之后)
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ 纯 LLM 测试  │  →   │ LLM + Gazebo │  →   │ LLM + 真实车 │
│ 不需要 ROS2  │      │   仿真联调    │      │   实车部署    │
│ Python 脚本  │      │  ROS2 节点    │      │              │
└─────────────┘      └─────────────┘      └─────────────┘
   验证 LLM 能理解指令      验证 LLM 能控制仿真车     验证真实场景
```

---

## 6. 阶段一：纯 LLM 测试

> 目标：验证 LLM 能正确理解自然语言指令并输出结构化命令。
> 不需要 ROS2、不需要机器人，一台电脑就能跑。

### 6.1 环境准备

```bash
# 安装 Python 依赖
pip install openai
```

### 6.2 选择 LLM 后端 (三选一)

#### 方案 A：Ollama 本地部署 (推荐新手，免费离线)

```bash
# 1. 下载安装 Ollama: https://ollama.com/download
# 2. 拉取模型 (首次需要下载 4-5GB)
ollama run qwen2.5:7b

# 3. 模型启动后会自动提供 API: http://localhost:11434/v1
```

#### 方案 B：DeepSeek (推荐，便宜好用)

```
1. 注册: https://platform.deepseek.com
2. 创建 API Key
3. 修改 llm_nav_test.py 中的配置:
   API_BASE_URL = "https://api.deepseek.com"
   API_KEY = "sk-你的key"
   MODEL_NAME = "deepseek-chat"
```

#### 方案 C：OpenAI

```
1. 注册: https://platform.openai.com
2. 创建 API Key
3. 修改配置:
   API_BASE_URL = "https://api.openai.com/v1"
   API_KEY = "sk-你的key"
   MODEL_NAME = "gpt-4o-mini"
```

### 6.3 运行测试

```bash
cd llm_test

# 方式1: 交互模式 (和 LLM 对话)
python llm_nav_test.py
# 选择 1，然后输入: "带我去会议室"

# 方式2: 批量测试 (自动跑所有测试用例)
python llm_nav_test.py
# 选择 2

# 方式3: Function Calling 模式
python llm_nav_function_call_test.py
```

### 6.4 预期输出

```
[你] > 带我去会议室
  [思考中...]
  [机器人] 好的，正在导航到会议室
  [解析结果] intent=navigate, target=会议室
  [模拟] 机器人已到达 (3.5, -1.2)

[你] > 往前走两米
  [思考中...]
  [机器人] 收到，向前移动两米
  [解析结果] intent=relative_move, forward=2.0m, left=0.0m
  [模拟] 机器人移动到 (5.50, -1.20)
```

### 6.5 这一步验证了什么？

- LLM 能理解中文自然语言
- LLM 能正确匹配地点别名 ("开会的地方" → 会议室)
- LLM 能输出稳定的 JSON 格式
- LLM 能区分不同意图 (导航/停止/旋转/查询)

---

## 7. 阶段二：LLM + ROS2 仿真

> 目标：在 Gazebo 仿真中，用自然语言控制虚拟机器人导航。

### 7.1 架构

```
终端1: Gazebo + Nav2 仿真
        ↓ (ROS2 话题)
终端2: llm_reasoning_node
        ↓ (API 调用)
        LLM 服务
        ↓ (解析后)
终端2: → 发布 Nav2 Goal
        ↓
终端1: 机器人开始移动
```

### 7.2 创建 ROS2 包 (后续实现)

```bash
cd src/my_scout_mini_project/scout_mini_ros2
ros2 pkg create scout_mini_llm --build-type ament_python \
  --dependencies rclpy geometry_msgs nav2_msgs tf2_ros
```

### 7.3 核心节点设计 (llm_reasoning_node)

```python
# 伪代码 - 展示核心逻辑
class LLMReasoningNode(Node):
    def __init__(self):
        # 1. 订阅用户输入 (可以是话题、服务或终端输入)
        self.create_subscription(String, '/user_command', self.on_command)

        # 2. TF 监听器 - 获取机器人实时位置
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # 3. Nav2 动作客户端 - 发送导航目标
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        # 4. 加载语义地图和 System Prompt
        self.semantic_map = load_json('semantic_map.json')

    def on_command(self, msg):
        # 获取机器人当前位置
        robot_pose = self.tf_buffer.lookup_transform('map', 'base_link', Time())

        # 调用 LLM
        result = call_llm(user_input=msg.data, robot_pose=robot_pose)

        # 执行动作
        if result['intent'] == 'navigate':
            self.send_nav_goal(result['coords'])
```

### 7.4 仿真运行步骤

```bash
# 终端1: 启动仿真 + Nav2
ros2 launch scout_mini_description auto_localization.py

# 终端2: 启动 LLM 节点
ros2 run scout_mini_llm llm_reasoning_node

# 终端3: 发送自然语言指令
ros2 topic pub /user_command std_msgs/String "data: '去会议室'" --once
```

---

## 8. 阶段三：LLM + 真实机器人

> 与阶段二几乎相同，只需要改启动命令。

```bash
# 终端1: 启动真实机器人
ros2 launch scout_mini_base scout_real.launch.py

# 终端2: 启动导航
ros2 launch scout_mini_description navigation.launch.py

# 终端3: 启动 LLM 节点 (代码完全不变)
ros2 run scout_mini_llm llm_reasoning_node
```

**从仿真到实车，LLM 节点的代码一行都不用改**，这就是 ROS2 的好处。

---

## 9. 两种实现方式对比

本项目提供了两个测试脚本，对应两种 LLM 集成方式：

### 方式 A：Prompt + JSON 输出 (`llm_nav_test.py`)

```
用户输入 → System Prompt 指导 LLM → LLM 输出 JSON → 你的代码解析 JSON
```

| 优点 | 缺点 |
|-----|-----|
| 所有 LLM 都支持 | JSON 格式偶尔不稳定 |
| 实现简单 | 需要写 JSON 解析容错代码 |
| Ollama 本地模型也能用 | 复杂指令可能输出错误 |

### 方式 B：Function Calling (`llm_nav_function_call_test.py`)

```
用户输入 → LLM 自动选择函数 → 直接输出函数名+参数 → 你的代码执行函数
```

| 优点 | 缺点 |
|-----|-----|
| 输出格式 100% 稳定 | 部分小模型不支持 |
| 不需要解析 JSON | 需要 OpenAI 兼容的 API |
| 更适合生产环境 | Ollama 部分模型不支持 |

### 推荐

- **学习阶段 / 本地测试** → 方式 A (Prompt + JSON)
- **生产部署 / 追求稳定** → 方式 B (Function Calling)

---

## 10. 常见问题

### Q: LLM 会不会让机器人撞墙？
**不会。** LLM 只负责"理解指令"并给出目标坐标，实际的路径规划和避障由 Nav2 完成。Nav2 会自动绕开障碍物。

### Q: LLM 反应慢怎么办？
- 本地部署 (Ollama) 通常 1-3 秒响应
- 云端 API (DeepSeek) 通常 0.5-2 秒
- 机器人可以先回复 "收到，正在规划"，再异步执行

### Q: 离线能用吗？
可以。用 Ollama 部署本地模型，完全不需要网络。推荐 qwen2.5:7b，8GB 显存就能跑。

### Q: 语义地图怎么建？
1. 先用 Cartographer 建好物理地图 (你已经做了)
2. 在地图上标注关键地点的坐标 (RViz 中读取)
3. 手动填写 `semantic_map.json`

### Q: 和 VLN (Vision-Language Navigation) 有什么区别？
| 本项目 | VLN |
|-------|-----|
| LLM 理解文字指令 → 输出坐标 | 模型理解文字 + 图像 → 直接输出动作 |
| 依赖已有地图 | 不一定需要地图 |
| LLM 不控制底层运动 | 模型端到端控制 |
| 简单可靠，适合工程部署 | 复杂，目前多在学术研究 |

### Q: 需要多少算力？
- **LLM 推理**: 8GB 显存的显卡就够跑 7B 模型
- **ROS2 + Nav2**: 和现在一样，不增加负担
- **两者可以跑在不同机器上** (LLM 通过 HTTP API 调用)

---

## 11. 语音输入模式

> 用麦克风说话，自动识别为文字，再交给 LLM 解析导航指令。

### 流程

```
麦克风录音 (sounddevice)
        │
        ▼
faster-whisper 本地语音识别
        │  "去会议室"
        ▼
LLM Function Calling
        │  navigate_to_pose(x=3.5, y=-1.2, theta=1.57)
        ▼
模拟/真实导航执行
```

### 安装依赖

```bash
pip install sounddevice faster-whisper
```

首次运行会自动下载 Whisper 模型（`base` 约 300MB，完全离线）。

### 运行

```bash
cd llm_test
python llm_nav_voice_test.py
```

### 操作说明

| 操作 | 效果 |
|------|------|
| 直接按 Enter | 开始录音 5 秒，说完等待识别 |
| 输入文字后回车 | 跳过录音，直接用文字 |
| 输入 `t` | 切换到纯文字模式（不录音） |
| 输入 `q` | 退出 |

### Whisper 模型选择

在 `llm_nav_voice_test.py` 顶部修改 `WHISPER_MODEL_SIZE`：

| 模型 | 大小 | 速度 | 中文准确率 |
|------|------|------|-----------|
| `tiny` | ~150MB | 最快 | 一般 |
| `base` | ~300MB | 快 | 好（默认） |
| `small` | ~500MB | 中 | 更好 |
| `medium` | ~1.5GB | 慢 | 最好 |

有 GPU 时把 `device="cpu"` 改为 `device="cuda"` 可大幅提速。

---

## 文件说明

```
llm_test/
├── LLM_NAV_GUIDE.md               ← 你正在看的文档
├── llm_nav_test.py                 ← 方式A: Prompt+JSON 测试脚本
├── llm_nav_function_call_test.py   ← 方式B: Function Calling 测试脚本
├── llm_nav_voice_test.py           ← 方式C: 语音输入 + Function Calling
└── config/
    ├── semantic_map.json           ← 语义地图 (地点名称+坐标)
    └── system_prompt.txt           ← LLM 系统提示词模板
```

## 下一步行动

1. **今天**: 跑通阶段一的测试脚本，感受 LLM 解析效果；试试语音模式
2. **本周**: 调整 `semantic_map.json`，加入你真实地图的地点
3. **下周**: 创建 ROS2 的 `scout_mini_llm` 包，接入 Gazebo 仿真
4. **之后**: 实车测试
