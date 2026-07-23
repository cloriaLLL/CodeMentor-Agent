# P1 架构重构续作：子任务 A 收尾 + 子任务 C 实施

## Context（背景与目标）

本计划是 [`P1架构重构方案.md`](file:///c:/WorkSpace/CodeMentor%20Agent/.trae/documents/P1架构重构方案.md) 的续作。原计划包含三个子任务（B→A→C），其中：

- **子任务 B（清理旧 Generator-Validator 链路）**：✅ 已完成（pytest 基线 72 passed, 2 skipped）
- **子任务 A（拆分 ExerciseEvaluator God Class）**：⏳ **半途中断**——子包 4 个文件已创建，但缺 `__init__.py`、原 `.py` 未删、stale `.pyc` 未清，当前 import 处于歧义态
- **子任务 C（Prompt 外置到 prompts/）**：❌ 未开始

**本计划目标**：收尾子任务 A（解除 import 歧义、验证零回归），然后完整实施子任务 C（外置 8 个 prompt 文件、加 `lru_cache`、改 3 个模块的引用），全程保持零功能回归。

---

## 当前状态分析（基于 Phase 1 探索）

### 子任务 A 半途状态

| 路径 | 状态 | 说明 |
|---|---|---|
| `agents/exercise_evaluator/__init__.py` | ❌ 缺失 | 子包无法被 import |
| `agents/exercise_evaluator/models.py` | ✅ 已建（835B） | `EvaluationResult` Pydantic 模型 |
| `agents/exercise_evaluator/quality.py` | ✅ 已建（9355B） | `CodeQualityAssessor` 6 个纯函数 |
| `agents/exercise_evaluator/ai_feedback.py` | ✅ 已建（12826B） | `AIFeedbackBuilder` 5 个反馈方法 |
| `agents/exercise_evaluator/core.py` | ✅ 已建（17595B） | 瘦身 `ExerciseEvaluator`，组合模式，**用绝对导入** `from agents.exercise_evaluator.ai_feedback import AIFeedbackBuilder` |
| `agents/exercise_evaluator.py` | ⚠️ 仍存在（37327B） | 原 922 行 God Class，**必须删除**（与子包同名，Python 解析歧义） |
| `agents/__pycache__/exercise_evaluator.cpython-312.pyc` | ⚠️ 存在 | 旧文件缓存字节码，**必须删除** |

### 子任务 C 待办状态

| 路径 | 现状 |
|---|---|
| `prompts/` | 目录存在但**空**（子任务 B 删了 generator.txt/validator.txt/orchestrator.txt） |
| `agents/__init__.py:L20` `load_prompt` | **未加** `@lru_cache`（仅 `load_seed_data` 有） |
| `agents/orchestrator.py:L41` | `MENTOR_SYSTEM_PROMPT` 仍内嵌（~250 行） |
| `agents/orchestrator.py:L293` 附近 | `NOTEBOOK_MODE_SUFFIX` 仍内嵌 |
| `agents/exercise_generator.py:L74-163` | 4 个 `_XXX_PROMPT` 常量仍内嵌，含 `{{` `}}` 转义 |
| `agents/exercise_evaluator/ai_feedback.py:L103,L197` | 2 个 `_build_*_system_prompt` 方法体内嵌 prompt |

---

## 实施方案

### 第一阶段：子任务 A 收尾（解除 import 歧义）

#### 步骤 A1：创建 `agents/exercise_evaluator/__init__.py`

按依赖顺序 re-export 公开 API（避免部分初始化时的属性查找问题；虽然 `core.py` 用绝对导入触发的是 submodule 加载而非 package 属性查找，仍按依赖顺序排列以求清晰）：

```python
"""CodeMentor Agent - 多题型练习评估器子包。

从原 922 行 God Class (agents/exercise_evaluator.py) 拆分为：
- models.py:    EvaluationResult Pydantic 模型
- quality.py:   CodeQualityAssessor 纯函数代码质量评分
- ai_feedback.py: AIFeedbackBuilder LLM 反馈生成
- core.py:      ExerciseEvaluator 路由 + 沙箱编排（组合上述两类）

公开 API 向后兼容：`from agents.exercise_evaluator import ExerciseEvaluator` 签名不变。
"""
from agents.exercise_evaluator.ai_feedback import AIFeedbackBuilder
from agents.exercise_evaluator.core import ExerciseEvaluator
from agents.exercise_evaluator.models import EvaluationResult
from agents.exercise_evaluator.quality import CodeQualityAssessor

__all__ = ["EvaluationResult", "ExerciseEvaluator", "CodeQualityAssessor", "AIFeedbackBuilder"]
```

#### 步骤 A2：删除原 `agents/exercise_evaluator.py`

使用 `DeleteFile` 工具删除 37327B 的原 God Class 文件。**关键**：Python 包解析时同名 `.py` 文件与 `/` 目录不能共存——删除后子包 `__init__.py` 才能生效。

#### 步骤 A3：清理 stale `__pycache__`

删除 `agents/__pycache__/exercise_evaluator.cpython-312.pyc`（旧 `.py` 的字节码缓存，会干扰 import 解析）。

#### 步骤 A4：验证子任务 A

```powershell
# 1. import 冒烟：确认 module 路径指向子包
python -c "from agents.exercise_evaluator import ExerciseEvaluator; print(ExerciseEvaluator.__module__)"
# 期望输出：agents.exercise_evaluator.core

# 2. 零回归测试
pytest tests/ -q
# 期望：72 passed, 2 skipped
```

---

### 第二阶段：子任务 C 实施（Prompt 外置）

#### 步骤 C1：给 `load_prompt` 加 `@lru_cache`

修改 [agents/__init__.py](file:///c:/WorkSpace/CodeMentor%20Agent/agents/__init__.py) L20-30：

- 在 `def load_prompt(name: str) -> str:` 上方加 `@lru_cache(maxsize=None)`
- 已有 `from functools import lru_cache`（L13），无需新增 import
- **理由**：prompt 文件在运行期不变，缓存避免每次 LLM 调用都做磁盘 I/O；与 `load_seed_data` 保持一致

#### 步骤 C2：创建 8 个 prompt 文件

**操作原则**：从源码原样提取字符串内容，**不修改任何字符**（包括首尾换行、emoji、Markdown 标记）。提取后用 `assert 原常量 == load_prompt("xxx")` 验证一致性。

| 文件 | 源 | 含 `.format()` 占位符? | 转义注意 |
|---|---|---|---|
| `prompts/mentor.txt` | `orchestrator.py` `MENTOR_SYSTEM_PROMPT`（L41-290） | 否 | 无 |
| `prompts/mentor_notebook_suffix.txt` | `orchestrator.py` `NOTEBOOK_MODE_SUFFIX`（L293-307） | 否 | 无 |
| `prompts/exercise_understanding.txt` | `exercise_generator.py` `_UNDERSTANDING_PROMPT`（L74-98） | 是 `{subtype_desc}{knowledge_point}{difficulty}{language}` | **保留 `{{` `}}`**（JSON 示例的 `{` `}`） |
| `prompts/exercise_modification.txt` | `exercise_generator.py` `_MODIFICATION_PROMPT`（L100-120） | 是 | **保留 `{{` `}}`** |
| `prompts/exercise_creation.txt` | `exercise_generator.py` `_CREATION_PROMPT`（L122-141） | 是 | **保留 `{{` `}}`** |
| `prompts/exercise_project.txt` | `exercise_generator.py` `_PROJECT_PROMPT`（L143-163） | 是 | **保留 `{{` `}}`** |
| `prompts/feedback_understanding.txt` | `ai_feedback.py` `_build_understanding_feedback_system_prompt` 返回值（L113-144） | 否 | 无 |
| `prompts/feedback_code.txt` | `ai_feedback.py` `_build_ai_feedback_system_prompt` 返回值（L202-236） | 否 | 无 |

**关键风险点**：`exercise_*.txt` 中 JSON 示例的 `{{` `}}` 必须原样保留——`.format()` 会把它们解析为字面 `{` `}`。若误改为单 `{` `}`，`.format()` 会抛 `KeyError`。

#### 步骤 C3：修改 `agents/orchestrator.py`

1. 删除 `MENTOR_SYSTEM_PROMPT` 常量定义（L41-290，~250 行）
2. 删除 `NOTEBOOK_MODE_SUFFIX` 常量定义（L293-307）
3. 在文件顶部 import 区加：`from agents import load_prompt`
4. `__init__` 方法中（原 `self.SYSTEM_PROMPT = MENTOR_SYSTEM_PROMPT` 处）改为：`self.SYSTEM_PROMPT = load_prompt("mentor")`
5. `_build_messages` 方法中（原引用 `NOTEBOOK_MODE_SUFFIX` 处）改为：`load_prompt("mentor_notebook_suffix")`
6. **先做一致性 assert 再删常量**：临时跑 `assert MENTOR_SYSTEM_PROMPT == load_prompt("mentor")` 确认零字符差异后再删

#### 步骤 C4：修改 `agents/exercise_generator.py`

1. 删除 4 个 `_XXX_PROMPT` 常量定义（L74-163）
2. 在文件顶部 import 区加：`from agents import load_prompt`
3. 4 个调用点改为 `load_prompt("exercise_xxx").format(...)`：
   - L243: `_UNDERSTANDING_PROMPT.format(...)` → `load_prompt("exercise_understanding").format(...)`
   - L318: `_MODIFICATION_PROMPT.format(...)` → `load_prompt("exercise_modification").format(...)`
   - L348: `_CREATION_PROMPT.format(...)` → `load_prompt("exercise_creation").format(...)`
   - L377: `_PROJECT_PROMPT.format(...)` → `load_prompt("exercise_project").format(...)`
4. **冒烟**：对每个模板跑 `load_prompt("exercise_xxx").format(subtype_desc="x", knowledge_point="y", difficulty="z", language="python")` 确认无 `KeyError`

#### 步骤 C5：修改 `agents/exercise_evaluator/ai_feedback.py`

1. 在文件顶部 import 区加：`from agents import load_prompt`
2. `_build_understanding_feedback_system_prompt` 方法体（L113-144）改为：
   ```python
   def _build_understanding_feedback_system_prompt(self) -> str:
       """Build system prompt for understanding exercise feedback (externalized to prompts/)."""
       return load_prompt("feedback_understanding")
   ```
3. `_build_ai_feedback_system_prompt` 方法体（L202-236）改为：
   ```python
   def _build_ai_feedback_system_prompt(self) -> str:
       """Build system prompt for AI feedback generation (externalized to prompts/)."""
       return load_prompt("feedback_code")
   ```
4. 保留方法签名（作为包装器），调用方 `core.py` 无需改动

#### 步骤 C6：验证子任务 C

```powershell
# 1. 零回归测试
pytest tests/ -q
# 期望：72 passed, 2 skipped

# 2. prompt 加载冒烟（含 .format() 转义验证）
python -c "from agents import load_prompt; [print(f'{n}: {len(load_prompt(n))} chars') for n in ['mentor','mentor_notebook_suffix','exercise_understanding','exercise_modification','exercise_creation','exercise_project','feedback_understanding','feedback_code']]"

# 3. .format() 占位符验证（4 个 exercise 模板）
python -c "from agents import load_prompt; [load_prompt(n).format(subtype_desc='x', knowledge_point='y', difficulty='z', language='python') for n in ['exercise_understanding','exercise_modification','exercise_creation','exercise_project']]; print('format OK')"

# 4. import 冒烟
python -c "from agents.orchestrator import OrchestratorAgent; from agents.exercise_evaluator import ExerciseEvaluator; from agents.exercise_generator import ExerciseGeneratorAgent; print('imports OK')"
```

---

## 整体验证清单

子任务 A、C 全部完成后执行：

1. `pytest tests/ -q` — 全套测试零回归（基线 72 passed, 2 skipped）
2. `python -c "from agents.orchestrator import OrchestratorAgent; from agents.exercise_evaluator import ExerciseEvaluator; print('imports OK')"` — import 冒烟
3. 确认 `agents/exercise_evaluator.py` 单文件已替换为 `agents/exercise_evaluator/` 子包（5 个文件：`__init__.py` + 4 个模块）
4. 确认 `prompts/` 目录有 8 个新文件
5. 确认 `agents/__init__.py` 的 `load_prompt` 已加 `@lru_cache`
6. 前端 `pnpm tsc --noEmit`（确认无前端引用被破坏——本次改动纯后端，预期无影响）

---

## 假设与决策

1. **不补单元测试**：原计划提到"推荐补 `test_exercise_evaluator_quality.py` / `test_prompts.py`"，本续作**不补**——保持零回归验证以 pytest 现有套件为准，新增测试属于独立增强任务，避免扩大改动面。
2. **不启动后端服务手动冒烟**：依赖 LLM API key（用户已声明 `.env` 密钥工程完毕后再处理），手动 `/api/chat` 冒烟留待用户后续验证。本计划以 pytest + import 冒烟为验收门槛。
3. **`__init__.py` 用绝对导入**：与 `core.py` 已有的绝对导入风格保持一致（项目无相对导入先例）。
4. **prompt 文件原样提取**：不修改任何字符，包括首尾换行、emoji、Markdown 标记。用 `assert` 验证一致性后再删原常量。
5. **保留 `_build_*_system_prompt` 方法签名**：作为 `load_prompt()` 的包装器，避免改动 `core.py` 的调用点，最小化 diff。
6. **执行顺序**：A 收尾 → C1（lru_cache）→ C2（建文件）→ C3/C4/C5（改引用，可并行读但串行写）→ 整体验证。A 必须先于 C，因为 C5 要改 `ai_feedback.py`，而该文件目前只有在 A 完成后才能被正确 import。

---

## 提交粒度

建议 2 个独立 commit（可独立 revert）：
1. `refactor: split ExerciseEvaluator into sub-package (p1-2)` — 子任务 A 收尾
2. `refactor: externalize inline prompts to prompts/ (p1-4)` — 子任务 C
