"""CodeMentor Agent MVP — Agent 模块 (Session 3).

本包实现三大核心 Agent：
- Orchestrator（教学主控）— 对话驱动的自适应学习导师
- Generator（出题）— 基于 seed_data 生成场景化 Mini-Project
- Validator（校验）— 静默预跑参考答案，确保零坏题率

实现依据：DOC-03 Agentic Workflow and Prompts
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
SEED_DATA_PATH = Path(__file__).parent.parent / "schemas" / "seed_data.json"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """从 prompts/ 目录加载 System Prompt（带缓存，运行期不可变）。

    :param name: prompt 名称（不含扩展名），如 "orchestrator"
    :return: prompt 全文
    :raises FileNotFoundError: prompt 文件不存在
    """
    prompt_path = PROMPTS_DIR / f"{name}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_seed_data() -> dict:
    """加载并缓存 seed_data.json（全局单例，避免多处重复 I/O）。

    :return: 解析后的 seed_data 字典
    """
    try:
        return json.loads(SEED_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"knowledge_atoms": [], "seed_problems": []}
