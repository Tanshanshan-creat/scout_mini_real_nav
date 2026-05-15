#!/usr/bin/env python3
"""
LLM 导航语义解析 - 独立测试脚本 (不需要 ROS2)

功能：用自然语言和 LLM 对话，LLM 将指令解析为导航命令。
这个脚本可以独立运行，不依赖 ROS2 和机器人硬件。

用法：
    1. 安装依赖:  pip install openai
    2. 设置环境变量:  export OPENAI_API_KEY="你的key"
       或在脚本中直接填写 API 配置
    3. 运行:  python llm_nav_test.py

支持的 LLM 后端：
    - OpenAI (GPT-4 / GPT-3.5)
    - 本地部署的兼容 API (Ollama, vLLM, LM Studio 等)
    - DeepSeek / 通义千问等国产模型 (兼容 OpenAI 格式)
"""

import json
import math
import os
import sys
from pathlib import Path

# ============================================================
# 配置区 - 根据你的情况修改这里
# ============================================================

# 方式1: 使用 OpenAI 官方 API
# API_BASE_URL = "https://api.openai.com/v1"
# API_KEY = "sk-xxx"
# MODEL_NAME = "gpt-4o-mini"

# 方式2: 使用 DeepSeek (推荐国内用户，便宜好用)
# API_BASE_URL = "https://api.deepseek.com"
# API_KEY = "sk-xxx"
# MODEL_NAME = "deepseek-chat"

# 方式3: 使用本地 Ollama (完全免费，离线可用)
# 先运行: ollama run qwen2.5:7b
API_BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"  # Ollama 不需要真实 key
MODEL_NAME = "qwen2.5:7b"

# 方式4: 使用 LM Studio 本地部署
# API_BASE_URL = "http://localhost:1234/v1"
# API_KEY = "lm-studio"
# MODEL_NAME = "loaded-model"


# ============================================================
# 核心代码 - 不需要修改
# ============================================================

# 脚本所在目录
SCRIPT_DIR = Path(__file__).parent


def load_semantic_map():
    """加载语义地图"""
    map_path = SCRIPT_DIR / "config" / "semantic_map.json"
    with open(map_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_system_prompt(semantic_map: dict, robot_state: dict) -> str:
    """加载并填充 System Prompt"""
    prompt_path = SCRIPT_DIR / "config" / "system_prompt.txt"
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    # 将语义地图和机器人状态填入模板
    map_str = json.dumps(semantic_map, ensure_ascii=False, indent=2)
    state_str = json.dumps(robot_state, ensure_ascii=False, indent=2)

    return template.replace("{semantic_map}", map_str).replace("{robot_state}", state_str)


class MockRobotState:
    """模拟机器人状态 (替代真实 ROS2 TF 查询)"""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0  # 弧度
        self.battery = 85.0

    def get_state_dict(self) -> dict:
        return {
            "position": {"x": round(self.x, 2), "y": round(self.y, 2)},
            "yaw_rad": round(self.yaw, 2),
            "yaw_deg": round(math.degrees(self.yaw), 1),
            "heading": self._yaw_to_heading(),
            "battery_percent": self.battery,
        }

    def _yaw_to_heading(self) -> str:
        """将 yaw 角转为方位描述"""
        deg = math.degrees(self.yaw) % 360
        directions = ["东", "东北", "北", "西北", "西", "西南", "南", "东南"]
        idx = int((deg + 22.5) / 45) % 8
        return directions[idx]

    def apply_command(self, parsed: dict):
        """根据 LLM 解析结果模拟更新机器人位置"""
        intent = parsed.get("intent", "unknown")

        if intent == "navigate":
            # 导航到目标点 - 直接更新到目标坐标
            tid = parsed.get("target_id")
            if tid:
                # 从语义地图中找坐标
                sem_map = load_semantic_map()
                for loc in sem_map["locations"]:
                    if loc["id"] == tid:
                        self.x = loc["coords"][0]
                        self.y = loc["coords"][1]
                        self.yaw = loc["coords"][2]
                        print(f"  [模拟] 机器人已到达 ({self.x}, {self.y})")
                        break

        elif intent == "relative_move":
            rm = parsed.get("relative_move", {})
            fwd = rm.get("forward", 0.0)
            left = rm.get("left", 0.0)
            # 根据当前朝向计算新坐标
            self.x += fwd * math.cos(self.yaw) - left * math.sin(self.yaw)
            self.y += fwd * math.sin(self.yaw) + left * math.cos(self.yaw)
            print(f"  [模拟] 机器人移动到 ({self.x:.2f}, {self.y:.2f})")

        elif intent == "rotate":
            angle = parsed.get("rotate_angle", 0.0)
            self.yaw += angle
            print(f"  [模拟] 机器人旋转到 {math.degrees(self.yaw):.1f} 度")

        elif intent == "stop":
            print("  [模拟] 机器人已停止")


def call_llm(system_prompt: str, user_message: str) -> str:
    """调用 LLM API (兼容 OpenAI 格式)"""
    try:
        from openai import OpenAI
    except ImportError:
        print("\n[错误] 请先安装 openai 库: pip install openai")
        sys.exit(1)

    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=API_KEY,
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,  # 低温度 = 更稳定的输出
    )

    return response.choices[0].message.content


def parse_llm_response(raw: str) -> dict:
    """从 LLM 的回复中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    if "```" in raw:
        lines = raw.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                if in_block:
                    break
                in_block = True
                continue
            if in_block:
                json_lines.append(line)
        if json_lines:
            try:
                return json.loads("\n".join(json_lines))
            except json.JSONDecodeError:
                pass

    # 尝试找到 { } 包裹的内容
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    return {"intent": "unknown", "reply": f"[解析失败] LLM 原始输出: {raw}"}


def run_test_cases():
    """运行预定义的测试用例 (批量测试)"""
    test_cases = [
        # (用户输入, 期望的 intent)
        ("带我去会议室", "navigate"),
        ("去开会的地方", "navigate"),
        ("回充电桩", "navigate"),
        ("去前台", "navigate"),
        ("往前走两米", "relative_move"),
        ("后退一米", "relative_move"),
        ("左转90度", "rotate"),
        ("停下来", "stop"),
        ("别动", "stop"),
        ("你现在在哪里？", "query_status"),
        ("电量还有多少？", "query_status"),
        ("今天天气怎么样？", "unknown"),
    ]

    print("=" * 60)
    print("  LLM 导航语义解析 - 批量测试")
    print("=" * 60)

    semantic_map = load_semantic_map()
    robot = MockRobotState()

    passed = 0
    failed = 0

    for i, (user_input, expected_intent) in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}/{len(test_cases)} ---")
        print(f"  用户输入: {user_input}")
        print(f"  期望意图: {expected_intent}")

        system_prompt = load_system_prompt(semantic_map, robot.get_state_dict())

        try:
            raw = call_llm(system_prompt, user_input)
            parsed = parse_llm_response(raw)
            actual_intent = parsed.get("intent", "unknown")

            print(f"  LLM 意图: {actual_intent}")
            print(f"  LLM 回复: {parsed.get('reply', 'N/A')}")

            if actual_intent == expected_intent:
                print(f"  结果: PASS")
                passed += 1
            else:
                print(f"  结果: FAIL (期望 {expected_intent}, 得到 {actual_intent})")
                failed += 1

        except Exception as e:
            print(f"  结果: ERROR - {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  测试结果: {passed} 通过 / {failed} 失败 / {len(test_cases)} 总计")
    print(f"{'=' * 60}")


def run_interactive():
    """交互模式 - 和 LLM 实时对话"""
    print("=" * 60)
    print("  LLM 导航语义解析 - 交互模式")
    print("  输入自然语言指令，LLM 会解析为导航命令")
    print("  输入 'quit' 退出, 'state' 查看机器人状态")
    print("=" * 60)

    semantic_map = load_semantic_map()
    robot = MockRobotState()

    while True:
        try:
            user_input = input("\n[你] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见!")
            break
        if user_input.lower() == "state":
            print(f"  机器人状态: {json.dumps(robot.get_state_dict(), ensure_ascii=False)}")
            continue

        # 每次都用最新的机器人状态构建 prompt
        system_prompt = load_system_prompt(semantic_map, robot.get_state_dict())

        try:
            print("  [思考中...]")
            raw = call_llm(system_prompt, user_input)
            parsed = parse_llm_response(raw)

            print(f"  [机器人] {parsed.get('reply', '...')}")
            print(f"  [解析结果] intent={parsed.get('intent')}", end="")

            if parsed.get("target_id"):
                print(f", target={parsed.get('target_name', parsed['target_id'])}", end="")
            if parsed.get("relative_move"):
                rm = parsed["relative_move"]
                print(f", forward={rm.get('forward', 0)}m, left={rm.get('left', 0)}m", end="")
            if parsed.get("rotate_angle"):
                print(f", rotate={math.degrees(parsed['rotate_angle']):.1f}deg", end="")
            print()

            # 模拟执行命令
            robot.apply_command(parsed)

        except Exception as e:
            print(f"  [错误] {e}")


def main():
    print("\n请选择运行模式:")
    print("  1. 交互模式 - 和 LLM 实时对话 (推荐先试这个)")
    print("  2. 批量测试 - 自动运行预定义测试用例")

    choice = input("\n请输入 1 或 2: ").strip()

    if choice == "2":
        run_test_cases()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
