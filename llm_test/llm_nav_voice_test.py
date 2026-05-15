#!/usr/bin/env python3
"""
LLM 语音导航测试脚本 (不需要 ROS2)

流程：
  麦克风录音 → faster-whisper 本地转文字 → LLM Function Calling → 模拟导航执行

用法：
    pip install sounddevice faster-whisper
    python llm_nav_voice_test.py

首次运行会自动下载 Whisper 模型 (~150MB for tiny, ~1.5GB for medium)。
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

# ============================================================
# 配置区
# ============================================================

# LLM 后端 (和 llm_nav_function_call_test.py 保持一致)
API_BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL_NAME = "qwen2.5:7b"

# DeepSeek (推荐，效果更好)
# API_BASE_URL = "https://api.deepseek.com"
# API_KEY = "sk-xxx"
# MODEL_NAME = "deepseek-chat"

# OpenAI
# API_BASE_URL = "https://api.openai.com/v1"
# API_KEY = "sk-xxx"
# MODEL_NAME = "gpt-4o-mini"

# Whisper 模型大小: tiny(~150MB) / base(~300MB) / small(~500MB) / medium(~1.5GB)
# tiny 速度最快但准确率低，medium 准确率高但慢，base 是个好平衡点
WHISPER_MODEL_SIZE = "tiny"

# 录音参数
SAMPLE_RATE = 16000   # Whisper 要求 16kHz
RECORD_SECONDS = 5    # 每次录音时长（秒），说完后自动停止

SCRIPT_DIR = Path(__file__).parent


# ============================================================
# 语音录制
# ============================================================

def record_audio(seconds: int = RECORD_SECONDS) -> np.ndarray:
    """录制麦克风音频，返回 numpy 数组"""
    try:
        import sounddevice as sd
    except ImportError:
        print("[错误] 请安装 sounddevice: pip install sounddevice")
        sys.exit(1)

    print(f"  [录音] 开始录音 {seconds} 秒，请说话...")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    print("  [录音] 录音结束")
    return audio.flatten()


# ============================================================
# 语音识别 (faster-whisper 本地)
# ============================================================

_whisper_model = None  # 全局缓存，避免重复加载


def download_whisper_from_modelscope(model_size: str) -> str:
    """从 ModelScope 下载 whisper 模型，返回本地路径"""
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("  [提示] 安装 modelscope: pip install modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple")
        sys.exit(1)

    model_map = {
        "tiny": "iic/speech_whisper_tiny",
        "base": "iic/speech_whisper_base",
        "small": "iic/speech_whisper_small",
        "medium": "iic/speech_whisper_medium",
    }
    repo_id = model_map.get(model_size)
    if not repo_id:
        print(f"  [错误] 不支持的模型大小: {model_size}")
        sys.exit(1)

    print(f"  [Whisper] 从 ModelScope 下载模型 {model_size}...")
    model_dir = snapshot_download(repo_id)
    return model_dir


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            print("[错误] 请安装 faster-whisper: pip install faster-whisper")
            sys.exit(1)

        # 优先使用本地模型目录
        local_model_dir = Path(__file__).parent / f"whisper_{WHISPER_MODEL_SIZE}"
        if local_model_dir.exists():
            model_path = str(local_model_dir)
            print(f"  [Whisper] 从本地加载模型: {model_path}")
        else:
            # 尝试从 ModelScope 下载（国内稳定）
            try:
                model_path = download_whisper_from_modelscope(WHISPER_MODEL_SIZE)
            except Exception:
                # 回退到 HuggingFace
                model_path = WHISPER_MODEL_SIZE
                print(f"  [Whisper] 从 HuggingFace 下载模型 {WHISPER_MODEL_SIZE}...")

        print(f"  [Whisper] 加载模型中...")
        # cpu + int8 在没有 GPU 的机器上也能跑
        _whisper_model = WhisperModel(model_path, device="cpu", compute_type="int8")
        print("  [Whisper] 模型加载完成")
    return _whisper_model


def transcribe(audio: np.ndarray) -> str:
    """将音频数组转为文字"""
    model = get_whisper_model()

    # faster-whisper 需要从文件读取，写到临时 wav
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    sf.write(tmp_path, audio, SAMPLE_RATE)

    segments, info = model.transcribe(tmp_path, language="zh", beam_size=5)
    text = "".join(seg.text for seg in segments).strip()

    Path(tmp_path).unlink(missing_ok=True)
    return text


# ============================================================
# LLM Function Calling (复用 llm_nav_function_call_test.py 的逻辑)
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
                    "x": {"type": "number", "description": "目标点的 x 坐标 (米)"},
                    "y": {"type": "number", "description": "目标点的 y 坐标 (米)"},
                    "theta": {"type": "number", "description": "目标点的朝向角度 (弧度)"},
                    "location_name": {"type": "string", "description": "目标地点的名称"},
                },
                "required": ["x", "y", "theta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_navigation",
            "description": "取消当前导航任务，让机器人停下来。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "relative_move",
            "description": "相对当前位置移动。前进为正，后退为负。",
            "parameters": {
                "type": "object",
                "properties": {
                    "forward_meters": {"type": "number", "description": "前进距离 (米)，后退为负"},
                    "left_meters": {"type": "number", "description": "左移距离 (米)，右移为负", "default": 0.0},
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
                    "angle_degrees": {"type": "number", "description": "旋转角度 (度)，左转为正，右转为负"},
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
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


class MockRobot:
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
            {"x": round(self.x, 2), "y": round(self.y, 2),
             "yaw_deg": round(math.degrees(self.yaw), 1), "battery": self.battery},
            ensure_ascii=False,
        )

    def execute_tool_call(self, func_name: str, args: dict) -> str:
        dispatch = {
            "navigate_to_pose": lambda: self.navigate_to_pose(**args),
            "cancel_navigation": lambda: self.cancel_navigation(),
            "relative_move": lambda: self.relative_move(**args),
            "rotate_in_place": lambda: self.rotate_in_place(**args),
            "get_robot_status": lambda: self.get_robot_status(),
        }
        fn = dispatch.get(func_name)
        return fn() if fn else f"未知的函数: {func_name}"


def load_semantic_map():
    map_path = SCRIPT_DIR / "config" / "semantic_map.json"
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(semantic_map: dict, robot: MockRobot) -> str:
    map_str = json.dumps(semantic_map, ensure_ascii=False, indent=2)
    return f"""你是一个机器人导航助手。你可以通过调用工具来控制机器人。

## 已知语义地图
{map_str}

## 机器人当前状态
位置: x={robot.x:.2f}, y={robot.y:.2f}
朝向: {math.degrees(robot.yaw):.1f} 度
电量: {robot.battery}%

## 规则
1. 用户提到地图中的地点（包括别名）时，调用 navigate_to_pose 并填入对应坐标
2. 用户要求停止时，调用 cancel_navigation
3. 用户要求相对移动时，调用 relative_move
4. 用户要求旋转时，调用 rotate_in_place
5. 用户查询状态时，调用 get_robot_status
6. 每次只能调用一个工具
"""


def call_llm_with_tools(system_prompt: str, user_message: str):
    try:
        from openai import OpenAI
    except ImportError:
        print("[错误] 请安装 openai: pip install openai")
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


# ============================================================
# 主循环
# ============================================================

def run_voice_interactive():
    print("=" * 60)
    print("  LLM 语音导航测试")
    print(f"  语音识别: faster-whisper ({WHISPER_MODEL_SIZE})")
    print(f"  LLM: {MODEL_NAME} @ {API_BASE_URL}")
    print("  按 Enter 开始录音，说完后等待自动停止")
    print("  输入 'q' 退出，输入 't' 切换到文字输入模式")
    print("=" * 60)

    semantic_map = load_semantic_map()
    robot = MockRobot()
    text_mode = False

    # 预加载 Whisper 模型（避免第一次录音时卡顿）
    get_whisper_model()

    while True:
        try:
            if text_mode:
                prompt_str = "\n[文字] > "
            else:
                prompt_str = f"\n[按 Enter 录音 {RECORD_SECONDS}s / 输入文字直接发送 / q退出 / t切换模式] > "

            raw_input = input(prompt_str).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if raw_input.lower() == "q":
            print("再见!")
            break

        if raw_input.lower() == "t":
            text_mode = not text_mode
            mode_name = "文字" if text_mode else "语音"
            print(f"  已切换到{mode_name}输入模式")
            continue

        # 决定输入来源
        if text_mode or raw_input:
            # 有文字输入，直接用文字
            user_text = raw_input
            if not user_text:
                continue
            print(f"  [文字输入] {user_text}")
        else:
            # Enter 键（空输入）→ 录音
            audio = record_audio(RECORD_SECONDS)
            print("  [识别中...]")
            user_text = transcribe(audio)
            if not user_text:
                print("  [未识别到语音，请重试]")
                continue
            print(f"  [识别结果] {user_text}")

        # LLM 处理
        system_prompt = build_system_prompt(semantic_map, robot)
        try:
            print("  [LLM 思考中...]")
            msg = call_llm_with_tools(system_prompt, user_text)

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    print(f"  [调用] {func_name}({json.dumps(args, ensure_ascii=False)})")
                    result = robot.execute_tool_call(func_name, args)
                    print(f"  [结果] {result}")
            else:
                print(f"  [机器人] {msg.content}")

        except Exception as e:
            print(f"  [错误] {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    run_voice_interactive()
