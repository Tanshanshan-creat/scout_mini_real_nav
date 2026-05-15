#!/usr/bin/env python3
"""
LLM Function Calling 导航测试脚本 (不需要 ROS2)

与 llm_nav_test.py 的区别：
  - llm_nav_test.py 使用 "Prompt + JSON 输出" 方式
  - 本脚本使用 "Function Calling / Tool Use" 方式

Function Calling 的优势：LLM 不需要自己组织 JSON，
而是直接"调用"你预定义的函数，输出更稳定。

用法：
    1. pip install openai
    2. 配置下方的 API 信息
    3. python llm_nav_function_call_test.py
"""

import json
import math
import sys
from pathlib import Path

# ============================================================
# 配置区 (和 llm_nav_test.py 一样)
# ============================================================

# Ollama 本地部署 (免费)
API_BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL_NAME = "qwen2.5:7b"

# DeepSeek (推荐)
# API_BASE_URL = "https://api.deepseek.com"
# API_KEY = "sk-xxx"
# MODEL_NAME = "deepseek-chat"

# OpenAI
# API_BASE_URL = "https://api.openai.com/v1"
# API_KEY = "sk-xxx"
# MODEL_NAME = "gpt-4o-mini"

SCRIPT_DIR = Path(__file__).parent


# ============================================================
# 定义机器人的 "技能" (Tools)
# ============================================================

ROBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate_to_pose",
            "description": "导航到指定的地图坐标点。用于用户想去某个地点时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "目标点的 x 坐标 (米)",
                    },
                    "y": {
                        "type": "number",
                        "description": "目标点的 y 坐标 (米)",
                    },
                    "theta": {
                        "type": "number",
                        "description": "目标点的朝向角度 (弧度)",
                    },
                    "location_name": {
                        "type": "string",
                        "description": "目标地点的名称",
                    },
                },
                "required": ["x", "y", "theta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_navigation",
            "description": "取消当前导航任务，让机器人停下来。用于用户说停、别动、取消时调用。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "relative_move",
            "description": "相对当前位置移动。前进为正，后退为负。左移为正，右移为负。",
            "parameters": {
                "type": "object",
                "properties": {
                    "forward_meters": {
                        "type": "number",
                        "description": "前进距离 (米)，后退为负",
                    },
                    "left_meters": {
                        "type": "number",
                        "description": "左移距离 (米)，右移为负",
                        "default": 0.0,
                    },
                },
                "required": ["forward_meters"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rotate_in_place",
            "description": "原地旋转指定角度。左转为正，右转为负。",
            "parameters": {
                "type": "object",
                "properties": {
                    "angle_degrees": {
                        "type": "number",
                        "description": "旋转角度 (度)，左转为正，右转为负",
                    },
                },
                "required": ["angle_degrees"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_robot_status",
            "description": "查询机器人当前状态，包括位置、朝向、电量等。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


class MockRobot:
    """模拟机器人"""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.battery = 85.0

    def navigate_to_pose(self, x, y, theta, location_name="未知"):
        self.x, self.y, self.yaw = x, y, theta
        return f"正在导航到 {location_name} (x={x}, y={y})... 已到达!"

    def cancel_navigation(self):
        return "导航已取消，机器人已停止。"

    def relative_move(self, forward_meters, left_meters=0.0):
        self.x += forward_meters * math.cos(self.yaw) - left_meters * math.sin(self.yaw)
        self.y += forward_meters * math.sin(self.yaw) + left_meters * math.cos(self.yaw)
        return f"已移动。当前位置: ({self.x:.2f}, {self.y:.2f})"

    def rotate_in_place(self, angle_degrees):
        self.yaw += math.radians(angle_degrees)
        return f"已旋转 {angle_degrees} 度。当前朝向: {math.degrees(self.yaw):.1f} 度"

    def get_robot_status(self):
        return json.dumps(
            {
                "x": round(self.x, 2),
                "y": round(self.y, 2),
                "yaw_deg": round(math.degrees(self.yaw), 1),
                "battery": self.battery,
            },
            ensure_ascii=False,
        )

    def execute_tool_call(self, func_name: str, args: dict) -> str:
        """根据函数名和参数执行对应的动作"""
        if func_name == "navigate_to_pose":
            return self.navigate_to_pose(**args)
        elif func_name == "cancel_navigation":
            return self.cancel_navigation()
        elif func_name == "relative_move":
            return self.relative_move(**args)
        elif func_name == "rotate_in_place":
            return self.rotate_in_place(**args)
        elif func_name == "get_robot_status":
            return self.get_robot_status()
        else:
            return f"未知的函数: {func_name}"


def load_semantic_map():
    map_path = SCRIPT_DIR / "config" / "semantic_map.json"
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(semantic_map: dict, robot: MockRobot) -> str:
    """构建 Function Calling 模式的 System Prompt"""
    map_str = json.dumps(semantic_map, ensure_ascii=False, indent=2)
    return f"""你是一个机器人导航助手。你可以通过调用工具来控制机器人。

## 已知语义地图
{map_str}

## 机器人当前状态
位置: x={robot.x:.2f}, y={robot.y:.2f}
朝向: {math.degrees(robot.yaw):.1f} 度
电量: {robot.battery}%

## 规则
1. 用户提到地图中的地点(包括别名)时，调用 navigate_to_pose 并填入对应坐标
2. 用户要求停止时，调用 cancel_navigation
3. 用户要求相对移动(往前走X米)时，调用 relative_move
4. 用户要求旋转时，调用 rotate_in_place
5. 用户查询状态时，调用 get_robot_status
6. 每次只能调用一个工具
"""


def call_llm_with_tools(system_prompt: str, user_message: str):
    """使用 Function Calling 模式调用 LLM"""
    try:
        from openai import OpenAI
    except ImportError:
        print("\n[错误] 请先安装 openai 库: pip install openai")
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        tools=ROBOT_TOOLS,
        tool_choice="auto",
        temperature=0.1,
    )

    return response.choices[0].message


def run_interactive():
    print("=" * 60)
    print("  LLM Function Calling 导航测试 - 交互模式")
    print("  输入自然语言指令，LLM 会调用机器人的函数")
    print("  输入 'quit' 退出")
    print("=" * 60)

    semantic_map = load_semantic_map()
    robot = MockRobot()

    while True:
        try:
            user_input = input("\n[你] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break

        system_prompt = build_system_prompt(semantic_map, robot)

        try:
            print("  [思考中...]")
            msg = call_llm_with_tools(system_prompt, user_input)

            # 检查是否有 tool call
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    print(f"  [Tool Call] {func_name}({json.dumps(args, ensure_ascii=False)})")
                    result = robot.execute_tool_call(func_name, args)
                    print(f"  [执行结果] {result}")
            else:
                # LLM 直接回复文字 (没有调用工具)
                print(f"  [机器人] {msg.content}")

        except Exception as e:
            print(f"  [错误] {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    run_interactive()
