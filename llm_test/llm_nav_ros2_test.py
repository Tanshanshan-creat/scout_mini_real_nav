#!/usr/bin/env python3
"""
LLM 语音导航 ROS2 测试脚本

流程：
  麦克风录音 → faster-whisper 转文字 → LLM Function Calling → Nav2 发送导航目标

前置条件：
    1. 先启动仿真: ros2 launch scout_mini_description scout_auto.launch.py
    2. 等待 Nav2 初始化完成
    3. 运行本脚本: python3 llm_nav_ros2_test.py

依赖：
    pip install openai numpy sounddevice soundfile faster-whisper
"""

import os
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

# ROS2
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from action_msgs.msg import GoalStatus

# ============================================================
# 配置区
# ============================================================

API_BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL_NAME = "qwen2.5:7b"

WHISPER_MODEL_SIZE = "tiny"
SAMPLE_RATE = 16000
RECORD_SECONDS = 5

SCRIPT_DIR = Path(__file__).parent


# ============================================================
# 语音识别
# ============================================================

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        local_model_dir = SCRIPT_DIR / f"whisper_{WHISPER_MODEL_SIZE}"
        if local_model_dir.exists():
            model_path = str(local_model_dir)
        else:
            model_path = WHISPER_MODEL_SIZE
        print(f"  [Whisper] 加载模型 {model_path}...")
        _whisper_model = WhisperModel(model_path, device="cpu", compute_type="int8")
        print("  [Whisper] 模型加载完成")
    return _whisper_model


def record_audio(seconds=RECORD_SECONDS):
    import sounddevice as sd
    print(f"  [录音] 开始录音 {seconds} 秒...")
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    print("  [录音] 结束")
    return audio.flatten()


def transcribe(audio: np.ndarray) -> str:
    model = get_whisper_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    sf.write(tmp_path, audio, SAMPLE_RATE)
    segments, _ = model.transcribe(tmp_path, language="zh", beam_size=5)
    text = "".join(seg.text for seg in segments).strip()
    Path(tmp_path).unlink(missing_ok=True)
    return text


# ============================================================
# ROS2 Nav2 导航
# ============================================================

class Nav2Client(Node):
    def __init__(self):
        super().__init__('llm_nav_test_node')
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._init_pose_pub = self.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        self.get_logger().info("等待 Nav2 action server...")
        self._action_client.wait_for_server()
        self.get_logger().info("Nav2 已连接!")
        # 发布初始位姿
        self._publish_initial_pose()

    def _publish_initial_pose(self):
        msg = PoseWithCovarianceStamped()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.pose.orientation.w = 1.0
        import time
        time.sleep(1.0)  # 等待publisher就绪
        self._init_pose_pub.publish(msg)
        self.get_logger().info("已发布初始位姿 (0, 0)")
        time.sleep(2.0)  # 等待AMCL收敛

    def send_goal(self, x, y, theta):
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.orientation.z = math.sin(theta / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(theta / 2.0)

        self.get_logger().info(f"发送导航目标: ({x:.3f}, {y:.3f}, θ={math.degrees(theta):.1f}°)")
        future = self._action_client.send_goal_async(goal_msg, feedback_callback=self._feedback_cb)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()

        if not goal_handle.accepted:
            return "导航目标被拒绝"

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        status = result_future.result().status

        if status == GoalStatus.STATUS_SUCCEEDED:
            return "导航成功，已到达目标!"
        else:
            return f"导航失败，状态码: {status}"

    def cancel_goal(self):
        self._action_client._cancel_goal_async()
        return "导航已取消"

    def _feedback_cb(self, feedback_msg):
        pos = feedback_msg.feedback.current_pose.pose.position
        self.get_logger().info(f"  当前位置: ({pos.x:.2f}, {pos.y:.2f})")


# ============================================================
# LLM Function Calling
# ============================================================

ROBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "navigate_to_pose",
            "description": "导航到指定的地图坐标点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "目标 x 坐标 (米)"},
                    "y": {"type": "number", "description": "目标 y 坐标 (米)"},
                    "theta": {"type": "number", "description": "目标朝向 (弧度)"},
                    "location_name": {"type": "string", "description": "地点名称"},
                },
                "required": ["x", "y", "theta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_navigation",
            "description": "取消当前导航任务。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def load_semantic_map():
    map_path = SCRIPT_DIR / "config" / "semantic_map.json"
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(semantic_map: dict) -> str:
    map_str = json.dumps(semantic_map, ensure_ascii=False, indent=2)
    return f"""你是一个机器人导航助手。用户说出目的地，你调用 navigate_to_pose 发送导航。

## 已知语义地图
{map_str}

## 规则
1. 用户提到地图中的地点（包括别名）时，调用 navigate_to_pose 并填入对应坐标
2. 用户要求停止时，调用 cancel_navigation
3. 每次只调用一个工具
"""


def call_llm_with_tools(system_prompt: str, user_message: str):
    from openai import OpenAI
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


# ============================================================
# 主循环
# ============================================================

def main():
    rclpy.init()
    nav_client = Nav2Client()
    semantic_map = load_semantic_map()
    system_prompt = build_system_prompt(semantic_map)

    print("=" * 60)
    print("  LLM 语音导航 ROS2 测试")
    print(f"  语音: faster-whisper ({WHISPER_MODEL_SIZE})")
    print(f"  LLM: {MODEL_NAME} @ {API_BASE_URL}")
    print("  按 Enter 录音 / 输入文字直接发送 / q 退出")
    print("=" * 60)

    get_whisper_model()

    while True:
        try:
            raw = input(f"\n[Enter录音{RECORD_SECONDS}s / 输文字 / q退出] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if raw.lower() == "q":
            break

        if raw:
            user_text = raw
        else:
            audio = record_audio()
            user_text = transcribe(audio)
            if not user_text:
                print("  [未识别到语音]")
                continue
            print(f"  [识别] {user_text}")

        try:
            print("  [LLM 思考中...]")
            msg = call_llm_with_tools(system_prompt, user_text)

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    print(f"  [调用] {func_name}({json.dumps(args, ensure_ascii=False)})")

                    if func_name == "navigate_to_pose":
                        result = nav_client.send_goal(args["x"], args["y"], args.get("theta", 0.0))
                    elif func_name == "cancel_navigation":
                        result = nav_client.cancel_goal()
                    else:
                        result = f"未知函数: {func_name}"
                    print(f"  [结果] {result}")
            else:
                print(f"  [回复] {msg.content}")
        except Exception as e:
            print(f"  [错误] {e}")
            import traceback
            traceback.print_exc()

    nav_client.destroy_node()
    rclpy.shutdown()
    print("再见!")


if __name__ == "__main__":
    main()
