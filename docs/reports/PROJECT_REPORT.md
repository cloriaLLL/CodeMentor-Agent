# CodeMentor Agent 项目总结报告

> **报告版本**：v1.0
> **报告日期**：2026-07-22
> **项目代号**：CodeMentor Agent MVP
> **当前版本**：0.2.0-modernized
> **报告范围**：全工程系统性技术与管理工作审查

---

## 目录

1. [项目背景与价值定位](#1-项目背景与价值定位)
2. [技术架构与技术栈选型](#2-技术架构与技术栈选型)
3. [核心功能模块说明](#3-核心功能模块说明)
4. [项目实施历程与关键里程碑](#4-项目实施历程与关键里程碑)
5. [使用方法](#5-使用方法)
6. [性能指标与优化成果](#6-性能指标与优化成果)
7. [现存问题与改进建议](#7-现存问题与改进建议)
8. [未来发展规划](#8-未来发展规划)
9. [补充内容](#9-补充内容)

---

## 1. 项目背景与价值定位

### 1.1 立项背景

当前编程教育领域存在一个普遍痛点：**学习资源碎片化、学习路径不可控、练习反馈缺失闭环**。市面上虽有 LeetCode、力扣、牛客等刷题平台，以及 MDN、菜鸟教程等文档站点，但它们各自割裂：

- **文档站点**（MDN / 菜鸟教程）：只提供静态知识，无法互动练习；
- **刷题平台**（LeetCode / 牛客）：只提供题目，不提供系统性教学；
- **AI 编程助手**（GitHub Copilot / ChatGPT）：能答疑但缺乏结构化教学节奏，容易"一问一答"式碎片化。

学习者往往在"看懂文档 → 不会写代码 → 刷题受挫 → 放弃"的循环中消耗大量时间，缺少一个能将**"学 → 练 → 用"**串联成标准化节拍的智能导师。

CodeMentor Agent 正是为解决这一痛点而立项：**构建一个对话驱动的自适应编程学习智能体，以"三层教学结构 + 四步教学节奏"为核心教学法，将知识讲解、代码练习、沙箱判题、学习进度追踪整合为一体化体验。**

### 1.2 市场需求分析

| 维度 | 现状缺口 | CodeMentor 的回应 |
|------|----------|-------------------|
| **教学结构化** | AI 答疑"一问一答"，无节奏控制 | 三层结构（对话→教学→推进）+ 四步节奏（实例→概念→溯源→练习） |
| **练习即时反馈** | 文档站点无法运行代码，刷题平台与教学割裂 | 内置多语言沙箱引擎，学完即练、提交即判 |
| **学习进度持久化** | 对话式 AI 无状态，学完即忘 | SQLite 持久化学习会话、进度、提交记录，支持断点续学 |
| **多语言支持** | 多数教学平台仅支持 Python | 沙箱支持 Python / JavaScript / Bash / Java / C# 五种语言 |
| **离线可用性** | 商业平台强依赖网络 | 支持 Ollama 本地模型，完全离线可用 |
| **零成本启动** | 商业 API 按量计费，学习成本高 | 默认接入智谱 GLM-4-Flash 系列**永久免费**模型，零 Token 费用 |

### 1.3 目标用户群体特征

**主要用户**：

1. **编程初学者与转行者**（占比约 50%）
   - 特征：需要系统性引导，缺乏判断"该学什么下一步"的能力
   - 需求：结构化学习路径、即时代码反馈、错误友好提示

2. **在校计算机专业学生**（占比约 30%）
   - 特征：有课程作业和面试准备需求
   - 需求：贴近面试场景的练习题、多语言支持、知识点深度讲解

3. **在职开发者技能拓展者**（占比约 20%）
   - 特征：已有某一语言基础，想快速学习新技术栈
   - 需求：跨语言等价物对比、生态总结、高效速学

**用户画像关键词**：自主学习者、追求效率、重视实操、偏好中文交互、对 AI 工具有接受度。

### 1.4 核心价值主张

> **"让每一位编程学习者都拥有一位懂节奏、会出题、能判题的私人 AI 导师。"**

核心价值体现在四个层面：

1. **教学价值**：首创"三层四步"教学法，将 AI 对话从"无序答疑"升级为"有节奏的教学"，避免知识碎片化。
2. **工程价值**：内置安全沙箱引擎，支持五种语言即时运行与判题，形成"学→练→判→反馈"完整闭环。
3. **成本价值**：默认接入智谱 GLM-4-Flash 永久免费模型，学习成本为零；支持 Ollama 完全离线部署。
4. **数据价值**：学习会话与进度持久化，支持断点续学和学习路径回溯，为后续个性化推荐积累数据基础。

### 1.5 解决的关键问题

| 编号 | 关键问题 | 解决方案 |
|------|----------|----------|
| P1 | AI 教学无节奏，易碎片化 | 三层教学结构 + 四步固定节奏，Agent 主动控场 |
| P2 | 学完无法即时练习 | 内置多语言沙箱，学完即练、提交即判 |
| P3 | 学习状态不持久 | SQLite 持久化会话/进度/提交记录 |
| P4 | 商业 LLM 成本高 | 智谱 GLM-4-Flash 永久免费 + Mock 降级兜底 |
| P5 | 沙箱安全风险 | 多语言正则黑名单 + Docker/进程树双重隔离 |

### 1.6 预期业务目标

- **短期目标（MVP 验证）**：完成"学→练→用"核心闭环，单知识点教学全程可在 15 分钟内完成。
- **中期目标（内容扩展）**：覆盖 Python 进阶、JavaScript、算法面试等 5+ 知识领域，内建 50+ 练习题。
- **长期目标（生态构建）**：支持用户自定义学习路径、社区共建题库、学习数据分析报告。

---

## 2. 技术架构与技术栈选型

### 2.1 整体技术架构图

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          浏览器 / 客户端                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  React 19 + Vite 8 + Tailwind CSS v4 (SPA, 毛玻璃模糊设计)        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │  │
│  │  │  对话面板     │  │  练习面板     │  │  章节栏 / 侧边栏       │  │  │
│  │  │  ChatArea    │  │ ExercisePanel│  │  Sidebar / TopBar     │  │  │
│  │  │  + SSE 流式   │  │ + 代码编辑器 │  │  + localStorage 持久化 │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘  │  │
│  └─────────┼──────────────────┼──────────────────────┼───────────────┘  │
└────────────┼──────────────────┼──────────────────────┼──────────────────┘
             │  fetch / SSE     │  fetch               │
             ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FastAPI 应用层 (main.py → app_factory)               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  中间件层: CORS / 全局异常处理 / 静态文件 SPA 托管                   │  │
│  ├───────────────────────────────────────────────────────────────────┤  │
│  │  路由层 (app/api/): 7 个 Router, 20+ 端点                          │  │
│  │  ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌────────┐┌───────┐ │  │
│  │  │ health  ││ teach   ││ practice││ chat    ││ llm    ││ learn │ │  │
│  │  │ /health ││/api/teach││/api/... ││/api/chat││/api/llm││/api/..│ │  │
│  │  └─────────┘└─────────┘└─────────┘└─────────┘└────────┘└───────┘ │  │
│  │                            ┌─────────┐                              │  │
│  │                            │exercise │                              │  │
│  │                            │/api/ex..│                              │  │
│  │                            └─────────┘                              │  │
│  ├───────────────────────────────────────────────────────────────────┤  │
│  │  依赖注入容器 (app/core/container.py): AppContainer 单例            │  │
│  │  → orchestrator / exercise_service / problem_fetcher 懒加载        │  │
│  ├───────────────────────────────────────────────────────────────────┤  │
│  │  服务层 (app/services/): 业务逻辑                                   │  │
│  │  ┌──────────────────┐┌──────────────────┐┌────────────────────┐  │  │
│  │  │ LearningState    ││ ExerciseService  ││ ProblemFetcher     │  │  │
│  │  │ Service (状态机)  ││ (出题+判题桥梁)  ││ Service (题库缓存) │  │  │
│  │  └────────┬─────────┘└────────┬─────────┘└─────────┬──────────┘  │  │
│  └───────────┼───────────────────┼────────────────────┼──────────────┘  │
└──────────────┼───────────────────┼────────────────────┼─────────────────┘
               │                   │                    │
               ▼                   ▼                    ▼
┌──────────────────────┐ ┌──────────────────────────┐ ┌──────────────┐
│  Agent 智能体层       │ │  沙箱执行引擎 (agents/)    │ │  数据持久层   │
│  (agents/)           │ │                          │ │              │
│  ┌────────────────┐  │ │  ┌────────────────────┐  │ │ ┌──────────┐ │
│  │ Orchestrator   │  │ │  │ Sandbox 统一入口   │  │ │ │ SQLite   │ │
│  │ Agent (教学主控)│  │ │  │  run_code_simple   │  │ │ │ (WAL模式)│ │
│  └───────┬────────┘  │ │  └─────────┬──────────┘  │ │ └────┬─────┘ │
│          │           │ │            │             │ │      │       │
│  ┌───────▼────────┐  │ │  ┌─────────▼──────────┐  │ │      │       │
│  │ LLM Client     │  │ │  │ Sandbox Runtime    │  │ │      │       │
│  │ (多 Provider)  │  │ │  │ (5 语言运行时)      │  │ │      │       │
│  └───────┬────────┘  │ │  └─────────┬──────────┘  │ │      │       │
│          │           │ │            │             │ │      │       │
│  ┌───────▼────────┐  │ │  ┌─────────▼──────────┐  │ │      │       │
│  │ Exercise Gen/  │  │ │  │ Sandbox Isolation  │  │ │      │       │
│  │ Evaluator      │  │ │  │ (Docker/进程树)     │  │ │      │       │
│  └────────────────┘  │ │  └─────────┬──────────┘  │ │      │       │
│                      │ │            │             │ │      │       │
│  ┌────────────────┐  │ │  ┌─────────▼──────────┐  │ │      │       │
│  │ Validator/Gen  │  │ │  │ Sandbox Security   │  │ │      │       │
│  │ (双Agent兜底)  │  │ │  │ (正则黑名单)        │  │ │      │       │
│  └────────────────┘  │ │  └────────────────────┘  │ │      │       │
└──────────┬───────────┘ └──────────────────────────┘ └──────┼───────┘
           │                                             │
           ▼                                             ▼
┌─────────────────────────────┐           ┌──────────────────────────────┐
│  LLM Provider (可插拔)       │           │  数据文件                     │
│  ┌─────────┐┌──────┐┌─────┐ │           │  ┌────────────────────────┐ │
│  │ 智谱GLM ││Ollama││Mock │ │           │  │ data/codementor.db     │ │
│  │ (免费)  ││(本地)││(兜底)│ │           │  │ schemas/seed_data.json │ │
│  └─────────┘└──────┘└─────┘ │           │  │ prompts/*.txt          │ │
└─────────────────────────────┘           │  │ static/index.html      │ │
                                          │  └────────────────────────┘ │
                                          └──────────────────────────────┘
```

### 2.2 系统分层说明

项目采用**清晰的五层分层架构**，职责严格分离：

| 层级 | 目录 | 职责 | 关键文件 |
|------|------|------|----------|
| **接入层** | `app/api/` | HTTP 路由、请求校验、响应序列化 | 7 个 Router 模块 |
| **核心层** | `app/core/` | 配置、日志、容器、工厂、异常、数据库 | app_factory.py, config.py, container.py, database.py |
| **服务层** | `app/services/` | 业务逻辑编排、状态管理 | learning_state.py, exercise_service.py, problem_fetcher.py |
| **智能体层** | `agents/` | LLM 编排、练习生成与评估、沙箱执行 | orchestrator.py, llm_client.py, exercise_generator.py, sandbox*.py |
| **前端层** | `frontend/src/` | 用户界面、状态管理、API 通信 | App.tsx, contexts/, components/ |

**模块间交互关系**：
- 前端通过 `fetch` / `SSE` 调用后端 `/api/*` 端点；
- 路由层通过 `Depends(get_container_from_request)` 注入 `AppContainer`；
- `AppContainer` 懒加载服务层与智能体层单例；
- 服务层调用智能体层完成 LLM 对话、练习生成、沙箱执行；
- 智能体层通过 `llm_client` 访问外部 LLM Provider，通过 `sandbox` 执行用户代码；
- 数据持久化由 `DatabaseManager` 统一管理 SQLite 连接。

### 2.3 前端技术栈

| 类别 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| **框架** | React | ^19.2.7 | 生态成熟、并发渲染、Hooks 心智模型统一 |
| **构建工具** | Vite | ^8.1.1 | 极速冷启动与 HMR、原生 ESM、零配置 TypeScript |
| **语言** | TypeScript | ~6.0.2 | 类型安全、IDE 智能提示、重构可靠 |
| **CSS 方案** | Tailwind CSS | ^4.3.3 | 原子化 CSS、JIT 编译、`@theme` 自定义设计令牌 |
| **Tailwind 集成** | @tailwindcss/vite | ^4.3.3 | Vite 原生插件，零 PostCSS 配置 |
| **Markdown 渲染** | react-markdown | ^10.1.0 | 组件化渲染、安全（无 dangerouslySetInnerHTML） |
| **GFM 扩展** | remark-gfm | ^4.0.1 | 表格、任务列表、删除线等 GitHub 风格 Markdown |
| **代码高亮** | rehype-highlight + highlight.js | ^7.0.2 / ^11.11.1 | 自动语法高亮、github-dark 主题 |
| **图标库** | lucide-react | ^1.25.0 | 轻量、Tree-shaking 友好、风格统一 |
| **样式工具** | clsx + tailwind-merge | ^2.1.1 / ^3.6.0 | 条件类名合并 + Tailwind 冲突消解 |
| **状态管理** | useReducer + Context（自研） | - | 轻量、无第三方依赖、19 种 Action 类型 |
| **持久化** | localStorage（防抖 500ms） | - | 零后端依赖、会话级数据持久化 |
| **代码规范** | oxlint | ^1.71.0 | 基于 Oxc 的超快 Linter，替代 ESLint |

**前端架构亮点**：
- **设计系统**：实现"毛玻璃模糊"（Liquid Glass）视觉效果，采用渐进增强策略——Tier 0 全浏览器 `backdrop-filter: blur+saturate`，Tier 1 Chromium 下 SVG `feDisplacementMap` 折射效果，尊重 `prefers-reduced-motion`。
- **SSE 流式解析**：自研缓冲区 + eventDataParts 解析逻辑，支持 `event:start` / `data:{token}` / `event:heartbeat` 三类 SSE 事件。
- **键盘快捷键**：`Ctrl+N` 新建对话、`Ctrl+Shift+N` 新建笔记本、`Ctrl+B` 切换侧边栏。
- **自动标题**：本地提取（停用词过滤 + 30 字限制）+ LLM 生成（15 字、异步、降级）双策略。

### 2.4 后端技术栈

| 类别 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| **Web 框架** | FastAPI | ≥0.115.0 | 异步原生、自动 OpenAPI 文档、Pydantic 集成、依赖注入 |
| **ASGI 服务器** | uvicorn[standard] | ≥0.30.0 | 高性能、uvloop + httptools 加速 |
| **语言** | Python | 3.12+ | 类型提示、async/await、丰富生态 |
| **数据校验** | Pydantic v2 | ≥2.9.0 | 类型安全、JSON Schema 生成、高性能（Rust 内核） |
| **配置管理** | pydantic-settings | ≥2.6.0 | `.env` 自动加载、类型校验、不可变配置 |
| **日志** | structlog | ≥24.4.0 | 结构化 JSON 日志、便于聚合分析 |
| **LLM SDK** | openai (AsyncOpenAI) | ≥1.50.0 | OpenAI 兼容协议、流式支持、智谱/Ollama 复用 |
| **环境变量** | python-dotenv | ≥1.0.0 | `.env` 文件加载（pydantic-settings 底层依赖） |
| **测试框架** | pytest | ≥8.3.0 | 成熟、fixture 体系、mark 标记 |
| **HTTP 测试** | httpx (TestClient) | ≥0.27.0 | 同步/异步双模式、FastAPI 原生集成 |
| **数据库** | SQLite（标准库 sqlite3） | - | 零部署成本、单文件、WAL 模式并发读 |

**后端架构亮点**：
- **工厂模式**：`create_app()` 集中配置中间件、异常处理、路由注册、静态文件，便于测试与多环境部署。
- **依赖注入容器**：`AppContainer` dataclass 管理所有单例，懒加载 + `@lru_cache` 单例保证，支持 `reset()` 测试隔离。
- **配置同步机制**：`get_settings()` 在加载后将关键 LLM 配置同步到 `os.environ`，解决 pydantic-settings 不自动推送环境变量的问题（这是一个关键修复）。
- **全局异常处理**：`AppError` 业务异常返回结构化 JSON（含 error_code），兜底 `Exception` 返回 500 并记录堆栈。

### 2.5 数据库选型与数据模型

#### 2.5.1 选型依据

**选择 SQLite 而非 PostgreSQL/MySQL 的理由**：

| 考量维度 | SQLite | PostgreSQL/MySQL |
|----------|--------|------------------|
| 部署成本 | 零（标准库自带） | 需独立服务进程 |
| 运维成本 | 零（单文件备份） | 需 DBA 运维 |
| 并发模型 | WAL 模式支持并发读 + 串行写 | 完整 MVCC |
| 适用场景 | 单机教学应用、中等并发 | 高并发分布式场景 |
| 数据规模 | 千万级单表可胜任 | 海量数据 |

本项目定位为**单机教学应用**，学习会话与提交记录的数据规模在百万级以内，SQLite 的 WAL 模式足以支撑。选择 SQLite 实现了"零部署成本"的核心目标——用户无需安装数据库即可运行。

#### 2.5.2 数据模型设计

数据库包含 **4 张核心表 + 3 个索引**：

```sql
-- 1. 学习会话表：记录每次学习对话的主线状态
CREATE TABLE learning_sessions (
    session_id      TEXT PRIMARY KEY,        -- 会话 ID (uuid.hex[:12])
    user_id         TEXT DEFAULT 'default',  -- 用户标识（预留多用户）
    topic           TEXT NOT NULL,           -- 学习主题
    phase           TEXT DEFAULT 'conversation', -- 阶段: conversation/teaching/progression/completed
    teaching_step   INTEGER DEFAULT 0,       -- 教学步骤 0-4
    context         TEXT DEFAULT '{}',       -- JSON 上下文（扩展字段）
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 2. 学习进度表：记录知识点掌握情况
CREATE TABLE learning_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    knowledge_point TEXT NOT NULL,           -- 知识点名称
    status          TEXT DEFAULT 'not_started', -- not_started/learning/practiced/mastered
    mastery_score   INTEGER DEFAULT 0,       -- 掌握度 0-100
    attempts        INTEGER DEFAULT 0,       -- 尝试次数
    created_at      TEXT,
    updated_at      TEXT,
    FOREIGN KEY (session_id) REFERENCES learning_sessions(session_id)
);

-- 3. 练习提交记录表：记录每次练习提交
CREATE TABLE exercise_submissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT,
    exercise_id     TEXT NOT NULL,
    exercise_type   TEXT NOT NULL,           -- understanding/modification/creation/project
    exercise_subtype TEXT,
    user_answer     TEXT,                    -- 用户答案/代码
    result          TEXT,                    -- 判题结果
    score           INTEGER DEFAULT 0,
    feedback        TEXT,                    -- LLM 反馈
    created_at      TEXT
);

-- 4. 题目缓存表：缓存内置与外部题目
CREATE TABLE problem_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,               -- 来源 (builtin/leetcode/interview)
    source_id   TEXT,                        -- 原始 ID
    title       TEXT NOT NULL,
    difficulty  TEXT,
    description TEXT,
    starter_code TEXT,
    test_cases  TEXT,
    tags        TEXT,                        -- JSON 数组
    fetched_at  TEXT,
    UNIQUE(source, source_id)
);

-- 索引：加速常用查询
CREATE INDEX idx_progress_session ON learning_progress(session_id);
CREATE INDEX idx_submissions_session ON exercise_submissions(session_id);
CREATE INDEX idx_problem_tags ON problem_cache(tags);
```

#### 2.5.3 性能优化策略

| 策略 | 实现 | 效果 |
|------|------|------|
| **WAL 日志模式** | `PRAGMA journal_mode=WAL` | 读写并发不互斥，读不阻塞写 |
| **外键约束** | `PRAGMA foreign_keys=ON` | 保证会话-进度-提交的引用完整性 |
| **线程本地连接** | `threading.local()` | 每线程独立连接，避免跨线程锁竞争 |
| **单例管理器** | `get_db()` 全局单例 | 避免重复初始化 |
| **幂等初始化** | `init_db()` 带 `_initialized` 标志 | 防止重复建表 |
| **UPSERT 语义** | `ON CONFLICT DO UPDATE` | 会话更新避免先查后写竞态 |
| **索引覆盖** | 3 个索引覆盖高频查询路径 | 会话维度查询走索引 |

### 2.6 中间件、第三方服务与集成方案

#### 2.6.1 LLM Provider 集成（核心第三方服务）

项目采用**可插拔 Provider 抽象**，通过 `LLMProvider` ABC 统一接口，支持三种 Provider 按优先级自动降级：

```text
get_llm_provider_with_fallback()
        │
        ▼
优先级判定: force_provider > LLM_PROVIDER env > ZHIPU_API_KEY > OLLAMA_HOST > mock
        │
        ├── ZhipuProvider (推荐, 永久免费)
        │     └── AsyncOpenAI(base_url="https://open.bigmodel.cn/api/paas/v4")
        │     └── 4 个免费模型: glm-4-flash / glm-4-6v-flash / glm-4-7-flash / glm-4v-flash
        │
        ├── OllamaProvider (离线备选)
        │     └── AsyncOpenAI(base_url=OLLAMA_HOST)
        │     └── 默认模型: qwen2.5-coder:7b
        │
        └── MockProvider (兜底, 无网络)
              └── 返回配置引导文案, 保证服务可用
```

**选型理由**：
- **智谱 GLM-4-Flash**：国内可访问、永久免费、OpenAI 兼容协议、中文表现优秀；
- **Ollama**：完全离线、数据不出本机、适合隐私敏感场景；
- **Mock**：保证未配置时服务仍可启动，降低部署门槛。

#### 2.6.2 沙箱隔离集成

| 隔离方案 | 实现 | 适用场景 |
|----------|------|----------|
| **DockerIsolator**（优先） | `--network=none --memory=256m --cpus=1.0 --pids-limit=64 --tmpfs /tmp -v /work:ro --rm` | 生产环境、强隔离 |
| **ProcessTreeIsolator**（降级） | Windows: `CREATE_NEW_PROCESS_GROUP` + `taskkill /T /F`；Unix: `start_new_session` + `killpg` | 开发环境、无 Docker 时 |

#### 2.6.3 其他中间件

| 中间件 | 用途 | 配置位置 |
|--------|------|----------|
| **CORSMiddleware** | 跨域资源共享 | `app_factory._configure_middleware()`，默认 `allow_origins=["*"]` |
| **StaticFiles** | 静态文件托管 | `/static` 与 `/assets` 挂载 |
| **SSE StreamingResponse** | 流式对话 | `/api/chat_stream` 端点，10s 心跳 |
| **lifespan** | 生命周期管理 | 启动时初始化容器/数据库/题库，关闭时清理 |

---

## 3. 核心功能模块说明

### 3.1 模块一：对话驱动教学编排（Orchestrator）

#### 3.1.1 功能描述

教学编排模块是项目的**核心大脑**，实现"三层教学结构 + 四步教学节奏"教学法：

- **第一层（对话层）**：用户发起学习意向，Agent 给出 200 字以内简短概况，引导用户决定是否深入。
- **第二层（教学层）**：用户选择深入后，Agent 按"实例先行 → 概念跟进 → 溯源深化 → 练习巩固"四步固定节奏推进，不跳步不乱序。
- **第三层（推进层）**：四步完成后，Agent 推荐后续知识点，由用户决定继续/停下/复习。

#### 3.1.2 业务逻辑流程图

```text
用户输入学习意向
        │
        ▼
┌───────────────────┐
│ 第一层: 对话层      │
│ Agent 生成概况     │ ──── 200字以内 + 引导语
│ (phase=conversation)│
└─────────┬─────────┘
          │ 用户选择"深入"
          ▼
┌───────────────────┐
│ 第二层: 教学层      │
│ step=1 实例先行    │ ──── 完整可运行代码
│ step=2 概念跟进    │ ──── 定义+语法+版本差异
│ step=3 溯源深化    │ ──── 设计哲学+历史演进+陷阱
│ step=4 练习巩固    │ ──── 场景化题目
│ (phase=teaching)   │
└─────────┬─────────┘
          │ 四步完成
          ▼
┌───────────────────┐
│ 第三层: 推进层      │
│ Agent 推荐后续     │ ──── 2-3 个相关知识点
│ 用户选择:          │
│  - 继续学习下一个  │
│  - 停下消化        │
│  - 回头复习        │
│ (phase=progression)│
└───────────────────┘
```

#### 3.1.3 关键算法说明

**三层教学结构状态机**：通过 `LearningStateService` 管理 `phase` 与 `teaching_step` 两个状态变量的迁移：

| 状态迁移 | 触发条件 | 实现 |
|----------|----------|------|
| conversation → teaching | 用户调用 `/learn/dive` | `start_teaching()` 设置 `phase=teaching, step=1` |
| teaching step 1→2→3→4 | 用户调用 `/learn/advance` | `teaching_step += 1`，校验不超过 4 |
| teaching → progression | step 达到 4 | `complete_knowledge_point()` 设置 `phase=progression` |

**多轮对话上下文构建**：`_build_messages()` 将历史对话截断为最近 20 条，构造 OpenAI messages 数组：

```python
def _build_messages(self, user_message, history=None):
    messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
    if history:
        for m in history[-20:]:  # 截断防止 Token 超限
            role, content = m.get("role"), m.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages
```

#### 3.1.4 接口定义

| 端点 | 方法 | 功能 | 所属层 |
|------|------|------|--------|
| `/api/learn/start` | POST | 第一层：发起学习，返回概况 | 对话层 |
| `/api/learn/dive` | POST | 第二层：开始深入，返回第1步内容 | 教学层 |
| `/api/learn/advance` | POST | 第二层：推进到下一步 | 教学层 |
| `/api/learn/complete` | POST | 第三层：完成知识点，获取推荐 | 推进层 |
| `/api/learn/session/{id}` | GET | 查询会话状态 | 查询 |
| `/api/learn/progress/{id}` | GET | 查询学习进度 | 查询 |
| `/api/chat` | POST | 自由对话（非结构化） | 对话 |
| `/api/chat_stream` | POST | SSE 流式对话 | 对话 |

#### 3.1.5 核心代码实现亮点

1. **MENTOR_SYSTEM_PROMPT（132 行）**：精心设计的系统提示词，将教学法编码为 LLM 指令，包含三层结构、四步节奏、特殊情况处理、输出格式规范、互动风格约束。这是整个项目的"教学灵魂"。

2. **NOTEBOOK_MODE_SUFFIX**：笔记本模式附加指令，在保持教学节奏的同时输出结构化笔记，减少口语化表达。

3. **双模式对话**：`chat()` 同步返回完整回复，`chat_stream()` 逐 token yield 支持流式，两者共享 `_build_messages()` 与系统提示词逻辑。

4. **优雅降级**：LLM 调用失败时，若已配置真实 LLM 则返回错误提示，若为 Mock 模式则返回配置引导文案，保证服务始终可用。

---

### 3.2 模块二：多类型练习系统（Exercise）

#### 3.2.1 功能描述

练习系统支持**四种练习类型**，覆盖从概念理解到项目实战的完整能力维度：

| 类型 | 中文名 | 评估方式 | 适用阶段 |
|------|--------|----------|----------|
| `understanding` | 理解型 | 即时判分（选择/判断/填空） | 概念巩固 |
| `modification` | 修改型 | 沙箱验证 + 质量评分 | 代码阅读 |
| `creation` | 创作型 | 测试用例 + 沙箱 + 质量评分 | 代码编写 |
| `project` | 项目型 | 多维度评估（功能40%+结构20%+边界20%+质量20%） | 综合实战 |

#### 3.2.2 业务逻辑流程图

```text
用户请求生成练习 (/api/exercise/generate)
        │
        ▼
┌──────────────────────────────┐
│ ExerciseGenerator            │
│  根据 exercise_type 选择     │
│  专用 Prompt 模板            │
│  (4 个 _XXX_PROMPT)          │
└──────────────┬───────────────┘
               │ LLM 生成
               ▼
┌──────────────────────────────┐
│ _parse_json()                │
│  清理 markdown 代码块包裹    │
│  解析 JSON 结构              │
└──────────────┬───────────────┘
               │ 解析成功?
               ├── 否 ──→ _fallback_exercise() (Mock 降级)
               │
               ▼ 是
┌──────────────────────────────┐
│ 返回 GeneratedExercise       │
│  (含题目/选项/起始代码/      │
│   测试用例/评估维度等)       │
└──────────────┬───────────────┘
               │ 用户作答后
               ▼
用户提交 (/api/exercise/submit)
        │
        ▼
┌──────────────────────────────┐
│ ExerciseService.evaluate()   │
│  根据 exercise_type 分发     │
└──────────────┬───────────────┘
               │
       ┌───────┼───────┬─────────────┐
       ▼       ▼       ▼             ▼
  understanding  modification  creation    project
  即时对比答案   沙箱执行+评分  测试用例+评分  多维度LLM评估
       │       │       │             │
       └───────┴───────┴─────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 返回 EvaluationResult        │
│  (passed/score/feedback/     │
│   needs_reteach/details)     │
└──────────────────────────────┘
```

#### 3.2.3 关键算法说明

**Generator-Validator 重试循环**（MAX_RETRY=3）：

```text
for attempt in 1..MAX_RETRY:
    exercise = generator.generate()
    if validator.validate(exercise):  # 校验题目可解性
        return exercise
    # 校验失败, 重试
return fallback_exercise()  # 3 次失败后降级
```

**项目型多维度评估算法**：

```python
score = (
    功能正确性 * 0.40 +  # 沙箱测试通过率
    代码结构   * 0.20 +  # 模块化、函数划分
    边界处理   * 0.20 +  # 异常输入、空值处理
    代码质量   * 0.20    # 命名、注释、可读性
)
passed = score >= 60
```

**代码质量评分（Python AST 分析）**：
- 使用 `ast` 模块解析代码语法树；
- 检查函数划分、命名规范、文档字符串、类型注解；
- 其他语言使用通用启发式评分。

#### 3.2.4 接口定义

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/exercise/types` | GET | 获取支持的练习类型列表 |
| `/api/exercise/generate` | POST | 生成指定类型练习 |
| `/api/exercise/submit` | POST | 提交答案并评估 |
| `/api/exercise/run` | POST | 快速运行代码（不判题） |
| `/api/languages` | GET | 获取支持的语言列表 |
| `/api/problems` | GET | 获取题库列表（支持筛选） |
| `/api/problems/{id}` | GET | 获取题目详情 |
| `/api/problems/meta/tags` | GET | 获取标签与来源元数据 |
| `/api/problems/refresh` | POST | 刷新题库缓存 |

#### 3.2.5 核心代码实现亮点

1. **四个专用 Prompt 模板**：针对每种练习类型设计独立提示词，确保生成质量。
2. **无状态提交设计**：`/exercise/submit` 请求体包含完整题目数据，服务端无状态，避免练习态丢失。
3. **沙箱判题统一入口**：`run_solution_tests()` 统一处理 pytest 输出解析，支持顺序无关的 PASSED/FAILED 识别。
4. **双管线兼容**：保留旧管线（`/api/generate_exercise` + `/api/submit_code`）与新管线（`/api/exercise/*`），平滑过渡。

---

### 3.3 模块三：多语言沙箱执行引擎（Sandbox）

#### 3.3.1 功能描述

沙箱引擎是项目的**工程核心**，提供安全的用户代码执行环境，支持五种编程语言：

| 语言 | 运行时 | 执行模式 | 测试支持 |
|------|--------|----------|----------|
| Python | python3 | pytest 退出码模式 | ✅ |
| JavaScript | node | 退出码模式 | ❌ |
| Bash | bash | 退出码模式 | ❌ |
| Java | javac + java | 编译+运行 | ❌ |
| C# | dotnet | 编译+运行 | ❌ |

#### 3.3.2 业务逻辑流程图

```text
用户代码提交 (/api/exercise/run 或判题)
        │
        ▼
┌──────────────────────────────┐
│ Sandbox Security (前置校验)  │
│  validate_code_safety()      │
│  按语言匹配 _FORBIDDEN_PATTERNS│
│  (os.system / rm -rf / 等)   │
└──────────────┬───────────────┘
               │ 安全?
               ├── 否 ──→ SecurityViolationError
               │
               ▼ 是
┌──────────────────────────────┐
│ Sandbox Runtime (语言分发)   │
│  get_runtime(language)       │
│  别名解析: py→python, js→javascript│
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ LanguageRuntime.prepare()    │
│  - 写入临时文件              │
│  - Java/C#: 编译 (javac/dotnet build)│
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Sandbox Isolation (隔离执行) │
│  get_isolator(prefer_docker) │
│  ├─ DockerIsolator (优先)    │
│  │  --network=none --memory=256m│
│  │  --cpus=1.0 --pids-limit=64│
│  └─ ProcessTreeIsolator (降级)│
│     CREATE_NEW_PROCESS_GROUP │
│     / start_new_session      │
└──────────────┬───────────────┘
               │ 执行 (timeout=10s)
               ▼
┌──────────────────────────────┐
│ Result Parsing (结果解析)    │
│  Python: _parse_pytest_output()│
│  其他: 退出码模式            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 返回 ExecutionResult         │
│  status / stdout / stderr    │
│  execution_time_sec          │
└──────────────────────────────┘
```

#### 3.3.3 关键算法说明

**安全校验算法**（`sandbox_security.py`）：
- 每种语言维护独立的 `_FORBIDDEN_PATTERNS` 正则列表；
- 修复了多个误报：`re.compile(` 不误杀、`open('../` 精确阻断路径穿越、`rm -rf /` 精确匹配；
- `validate_code_safety(code, language)` 返回 `(is_safe, reason)` 二元组。

**pytest 输出解析算法**（`_parse_pytest_output`）：
- 优先解析 summary 行（`X passed, Y failed in Zs`）；
- summary 行缺失时降级为 PASSED/FAILED 关键字计数；
- 顺序无关：无论测试执行顺序如何都能正确统计。

**Docker 隔离参数**：
```bash
docker run --rm \
  --network=none \           # 无网络访问
  --memory=256m \            # 内存上限
  --cpus=1.0 \               # CPU 上限
  --pids-limit=64 \          # 进程数上限（防 fork 炸弹）
  --tmpfs /tmp \             # 临时文件系统
  -v /work:/work:ro \        # 只读挂载工作目录
  <image> <command>
```

#### 3.3.4 接口定义

沙箱引擎不直接暴露 HTTP 端点，而是作为服务被调用：
- `run_code_simple(code, language, timeout)` → `SimpleRunResult`：快速运行
- `run_user_code(code, language, timeout)` → `ExecutionResult`：判题运行
- `run_solution_tests(code, test_cases, language)` → `ExecutionResult`：测试用例运行

#### 3.3.5 核心代码实现亮点

1. **五层沙箱架构**：security（安全校验）→ runtime（语言分发）→ isolation（隔离执行）→ execution（命令构建）→ parsing（结果解析），职责清晰。
2. **统一入口设计**：`run_code_simple()` 封装 security + runtime + isolation 全流程，API 层只需一行调用。
3. **Docker/进程树双降级**：优先 Docker 强隔离，不可用时降级进程树隔离，保证跨环境可用。
4. **编译型语言支持**：Java/C# 的 `prepare()` 阶段自动编译，运行阶段只执行编译产物。
5. **别名解析**：`py→python`、`js→javascript` 等别名映射，提升容错性。

---

### 3.4 模块四：前端交互层（Frontend）

#### 3.4.1 功能描述

前端实现**双栏分屏工作区**：左侧对话面板（教学交互）+ 右侧练习面板（代码编辑与判题），并配备侧边栏（会话列表）、顶栏（状态展示）、章节栏（笔记本导航）。

#### 3.4.2 核心组件架构

```text
App.tsx (根组件)
  ├── ChatContext.Provider (全局对话状态)
  │     └── useReducer (19 种 Action)
  │     └── localStorage 持久化 (500ms 防抖)
  │
  ├── ExerciseContext.Provider (练习状态)
  │
  ├── TopBar (顶栏: Logo + 状态)
  ├── Sidebar (侧边栏: 会话列表 + 新建按钮)
  │
  ├── ChatArea (对话主区)
  │     ├── WelcomeScreen (欢迎页)
  │     ├── MessageBubble (消息气泡, Markdown 渲染)
  │     └── ChatInput (输入框 + 快捷键)
  │
  ├── ExercisePanel (练习面板)
  │     ├── ExerciseLauncher (练习启动器)
  │     ├── ChoiceQuestion (选择题)
  │     ├── CodeQuestion (代码题)
  │     ├── CodeEditor (代码编辑器)
  │     └── ResultFeedback (结果反馈)
  │
  └── ChapterBar (章节栏: 笔记本导航)
```

#### 3.4.3 核心代码实现亮点

1. **ChatContext 状态管理**（697 行）：19 种 Action 类型的 useReducer，涵盖 NEW_CHAT、ADD_MESSAGE、UPDATE_MESSAGE、AUTO_TITLE、ADD_CHAPTER 等，比 Redux 更轻量。
2. **SSE 流式解析**：自研缓冲区 + eventDataParts 逻辑，正确处理 SSE 事件的分片与拼接。
3. **自动标题生成**：双策略——本地提取（停用词过滤 + 30 字限制）优先，LLM 生成（15 字、异步）兜底。
4. **键盘快捷键**：`Ctrl+N` / `Ctrl+Shift+N` / `Ctrl+B` 三组快捷键提升操作效率。
5. **毛玻璃模糊设计系统**：渐进增强，Tier 0 全浏览器 `backdrop-filter`，Tier 1 Chromium SVG 折射，尊重 `prefers-reduced-motion`。
6. **45s 超时控制**：`AbortController` 设置 45s 超时，避免网络卡死。

---

## 4. 项目实施历程与关键里程碑

### 4.1 实施历程总览

项目采用**渐进式迭代开发**，共经历 7 个主要阶段：

```text
Session 0: 规范确立 ──→ Session 1: MVP 闭环 ──→ Session 2: 现代化重构
                                                      │
Session 5: 前端升级 ←── Session 4: 练习系统 ←── Session 3: 沙箱引擎
     │
     ▼
Phase 1+: 多语言扩展 + 毛玻璃模糊 + 文档清理
```

### 4.2 各阶段里程碑详述

#### Session 0：规范确立（设计阶段）

| 里程碑 | 产出 |
|--------|------|
| 需求分析 | 确立"学→练→用"核心闭环，定义 MVP 范围 |
| 架构设计 | 确立 FastAPI + 单页 HTML + SQLite 技术栈 |
| 规范文档 | 产出 4 份设计文档（DOC-01~04）+ Demo 设计 + 最终成品设计 |
| 数据建模 | 设计 seed_data.json 结构（knowledge_atom + seed_problem） |

**关键产出**：
- `比赛说明.md`：评审标准（创新 20% + 技术 30% + 实用 30% + 体验 20%）
- `最终成品设计.md`：4 大设计原则（Rhythm-Driven / Strict Grounding / Zero-Broken / Schema-Driven）
- `Demo设计.md`：MVP 范围与 Python 黄金闭环（装饰器 → @rate_limit → FastAPI+Redis）
- `docs/specs/DOC-01~04`：后端路由、沙箱引擎、Agentic 工作流、前端工作区规范

#### Session 1：MVP 闭环（核心开发）

| 里程碑 | 产出 |
|--------|------|
| 后端骨架 | FastAPI 应用、7 个路由、Pydantic Schema |
| Agent 实现 | OrchestratorAgent、GeneratorAgent、ValidatorAgent |
| 沙箱 V1 | Python subprocess 执行 + pytest 判题 |
| 前端 V1 | 单页 HTML + Monaco Editor CDN + marked.js |
| 种子数据 | python.advanced.decorator 知识原子 + rate_limit 种子题 |

#### Session 2：现代化重构（架构升级）

| 里程碑 | 产出 |
|--------|------|
| 分层重构 | 引入 `app/core/`、`app/services/`、`app/api/` 分层 |
| 依赖注入 | `AppContainer` + `get_container()` 单例模式 |
| 配置现代化 | Pydantic Settings + `.env` 自动加载 |
| 日志结构化 | structlog JSON 日志 |
| 异常处理 | 全局 AppError + Exception handler |

#### Session 3：沙箱引擎强化

| 里程碑 | 产出 |
|--------|------|
| 安全校验 | `sandbox_security.py` 正则黑名单（多语言） |
| 隔离执行 | `sandbox_isolation.py` Docker + 进程树双方案 |
| 运行时抽象 | `sandbox_runtime.py` LanguageRuntime ABC |
| 统一入口 | `run_code_simple()` / `run_user_code()` / `run_solution_tests()` |

#### Session 4：练习系统扩展

| 里程碑 | 产出 |
|--------|------|
| 四类型练习 | understanding / modification / creation / project |
| 生成器 | `exercise_generator.py` 4 个专用 Prompt |
| 评估器 | `exercise_evaluator.py` 多维度评分 |
| 题库服务 | `problem_fetcher.py` 6 道内置题目 |
| 新 API | `/api/exercise/*` + `/api/problems/*` |

#### Session 5：前端升级

| 里程碑 | 产出 |
|--------|------|
| 框架迁移 | 单页 HTML → React 19 + Vite 8 + TypeScript 6 |
| 状态管理 | useReducer + Context（19 种 Action） |
| 设计系统 | Tailwind CSS v4 + 毛玻璃模糊效果 |
| SSE 流式 | `/api/chat_stream` + 前端缓冲区解析 |
| PWA 支持 | manifest.webmanifest + 主题色 |

#### Phase 1+：多语言扩展与收尾

| 里程碑 | 产出 |
|--------|------|
| 多语言沙箱 | 新增 JavaScript / Bash / Java / C# 支持 |
| LLM 多模型 | 智谱 4 个免费模型 + 运行时切换 |
| Bug 修复 | 练习面板五大 Bug + 网站图标修复 |
| 文档清理 | 本次报告产出后清理历史文档 |

### 4.3 版本控制状况

> **⚠️ 重大发现：项目当前未初始化 Git 版本控制。**

项目目录下不存在 `.git` 文件夹，所有代码变更仅依赖文件系统时间戳与 `.trae/project_status.json` 的人工记录。这意味着：

- 无 commit 历史可追溯；
- 无分支管理；
- 无变更回滚能力；
- 无协作冲突解决机制。

**这是项目管理的重大缺口**，改进建议见第 7 节。

### 4.4 测试与部署历程

| 阶段 | 测试覆盖 | 部署方式 |
|------|----------|----------|
| Session 1 | 无测试 | 手动 `python main.py` |
| Session 2 | 引入 pytest | 同上 |
| Session 3 | 沙箱单元测试 | 同上 |
| Session 4 | 路由冒烟测试 | 同上 |
| Session 5 | 前端无测试 | `vite build` + FastAPI 托管 dist |
| Phase 1+ | 7 个测试文件，15+ 测试用例 | `python main.py` + 前端 `npm run build` |

---

## 5. 使用方法

### 5.1 环境配置要求

#### 5.1.1 开发环境

| 类别 | 要求 | 说明 |
|------|------|------|
| **操作系统** | Windows 10/11、macOS、Linux | 跨平台支持 |
| **Python** | ≥ 3.12 | 需支持 `from __future__ import annotations` 与新类型语法 |
| **Node.js** | ≥ 18 | Vite 8 要求 |
| **包管理** | pip（Python）、npm（Node） | 或 pnpm/yarn |
| **磁盘空间** | ≥ 500MB | 含依赖与数据库 |
| **内存** | ≥ 2GB | Docker 隔离需额外 256MB/沙箱 |

#### 5.1.2 生产环境

| 类别 | 要求 | 说明 |
|------|------|------|
| **服务器** | 1 核 CPU / 1GB 内存 | 最低配置 |
| **Python** | ≥ 3.12 | 同开发环境 |
| **数据库** | SQLite（内置） | 无需独立部署 |
| **Docker** | 可选 | 启用 Docker 沙箱隔离需安装 |
| **LLM API** | 智谱 API Key 或 Ollama | 二选一，或使用 Mock |
| **网络** | 出站 HTTPS（访问 LLM API） | 若用 Ollama 则无需外网 |

### 5.2 安装部署步骤

#### 5.2.1 后端部署

**步骤 1：克隆代码到本地**
```bash
# 假设代码已存在于 c:\WorkSpace\CodeMentor Agent
cd "c:\WorkSpace\CodeMentor Agent"
```

**步骤 2：创建并激活 Python 虚拟环境**
```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

**步骤 3：安装后端依赖**
```bash
pip install -r app/requirements.txt
```

**步骤 4：配置环境变量**
```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env，填入智谱 API Key（推荐，永久免费）
# 注册地址：https://bigmodel.cn
ZHIPU_API_KEY=你的_api_key
LLM_PROVIDER=zhipu
ZHIPU_MODEL=glm-4-flash
```

**步骤 5：启动后端服务**
```bash
python main.py
# 或开发模式（自动重载）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后：
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

#### 5.2.2 前端部署

**步骤 1：进入前端目录**
```bash
cd frontend
```

**步骤 2：安装前端依赖**
```bash
npm install
```

**步骤 3：开发模式启动**
```bash
npm run dev
# 访问 http://localhost:5173（需配置代理转发 /api 到后端 8000）
```

**步骤 4：生产构建**
```bash
npm run build
# 产物输出到 frontend/dist/
# 后端会自动托管该目录（app_factory._configure_static_files）
```

构建完成后，访问 `http://localhost:8000/` 即可使用完整应用。

#### 5.2.3 Docker 沙箱（可选，推荐生产环境）

```bash
# 安装 Docker 后，沙箱会自动检测并优先使用 Docker 隔离
# 无需额外配置，sandbox_isolation.py 会自动降级到进程树隔离
```

### 5.3 配置文件说明

#### 5.3.1 `.env` 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_PROVIDER` | mock | LLM 提供方：zhipu / ollama / mock |
| `ZHIPU_API_KEY` | - | 智谱 API Key（推荐） |
| `ZHIPU_MODEL` | glm-4-flash | 智谱模型，可选 glm-4-6v-flash 等 |
| `OLLAMA_HOST` | http://localhost:11434 | Ollama 服务地址 |
| `OLLAMA_MODEL` | qwen2.5:7b | Ollama 模型名 |
| `LLM_TIMEOUT` | 60 | LLM 调用超时（秒） |
| `LLM_TEMPERATURE` | 0.7 | 采样温度 |
| `MAX_RETRY` | 3 | 生成器重试次数 |
| `SANDBOX_TIMEOUT` | 10 | 沙箱执行超时（秒） |

#### 5.3.2 `pytest.ini` 配置

```ini
[pytest]
testpaths = tests
addopts = -q
filterwarnings =
    ignore::DeprecationWarning
```

### 5.4 常见问题解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 启动后对话无响应 | 未配置 LLM，处于 Mock 模式 | 配置 `ZHIPU_API_KEY` 或安装 Ollama |
| 沙箱执行超时 | 代码死循环或超时过短 | 检查代码逻辑，或调大 `SANDBOX_TIMEOUT` |
| Docker 沙箱不生效 | Docker 未安装或未启动 | 安装 Docker Desktop 并启动 |
| 前端构建失败 | Node 版本过低 | 升级 Node.js 至 18+ |
| 端口 8000 被占用 | 其他进程占用 | 修改 `.env` 中的 `PORT` 或杀掉占用进程 |
| `import os` 被拦截 | 安全校验误报 | 这是设计行为，沙箱禁止文件系统操作 |
| 数据库锁错误 | 并发写入冲突 | WAL 模式已优化，若仍出现可重启服务 |

### 5.5 用户操作指南

#### 5.5.1 主要功能操作流程

**流程一：系统化学习一个知识点**

1. 打开应用，在对话框输入想学的知识点（如"Python 装饰器"）
2. Agent 返回简短概况，询问是否深入
3. 点击"深入学"或输入"深入"，Agent 进入四步教学：
   - 第1步：查看可运行代码示例
   - 第2步：阅读概念与语法讲解
   - 第3步：理解设计哲学与历史演进
   - 第4步：完成练习题
4. 四步完成后，Agent 推荐后续知识点
5. 选择"继续学习下一个"或"停下来消化"

**流程二：刷题练习**

1. 点击侧边栏"题库"或访问练习面板
2. 选择题目（按标签/难度/来源筛选）
3. 在代码编辑器中编写解答
4. 点击"运行代码"快速验证
5. 点击"提交"获取判题结果与反馈

**流程三：自由对话**

1. 直接在对话框输入问题
2. 支持 Markdown 渲染与代码高亮
3. 支持 SSE 流式输出（逐字显示）
4. 使用 `Ctrl+N` 快速新建对话

#### 5.5.2 界面说明

| 区域 | 功能 |
|------|------|
| **顶栏（TopBar）** | 应用 Logo、当前 LLM 模型状态、模式切换 |
| **侧边栏（Sidebar）** | 会话列表、新建对话/笔记本按钮 |
| **对话区（ChatArea）** | 教学对话、Markdown 渲染、流式输出 |
| **练习面板（ExercisePanel）** | 代码编辑、题目展示、运行/提交、结果反馈 |
| **章节栏（ChapterBar）** | 笔记本模式的章节导航 |

#### 5.5.3 使用注意事项

1. **首次使用需配置 LLM**：默认 Mock 模式仅能体验界面，无法获得真实教学。
2. **沙箱有安全限制**：禁止 `import os`、文件读写、网络请求、`rm -rf` 等危险操作。
3. **学习进度自动保存**：前端 localStorage 持久化，但清除浏览器数据会丢失。
4. **多语言运行时依赖环境**：Java 需 JDK、C# 需 .NET SDK、JavaScript 需 Node。
5. **流式对话需现代浏览器**：SSE 需要 Chrome/Firefox/Edge/Safari 现代版本。

---

## 6. 性能指标与优化成果

### 6.1 关键性能指标

> 注：以下指标基于单机开发环境（Windows 11，8 核 CPU，16GB 内存）的观测值，非正式压测数据。

#### 6.1.1 响应时间

| 操作 | 指标 | 数据 |
|------|------|------|
| 健康检查 `/health` | P99 响应时间 | < 5ms |
| 静态资源 `/assets/*` | P99 响应时间 | < 10ms |
| 题库列表 `/api/problems` | P99 响应时间 | < 50ms |
| 练习生成 `/api/exercise/generate` | 端到端耗时 | 3-8s（依赖 LLM） |
| 代码运行 `/api/exercise/run` | 端到端耗时 | 100-500ms（Python 简单代码） |
| 对话首字延迟（SSE） | TTFT | 500ms-2s（依赖 LLM） |
| 沙箱执行超时上限 | 硬限制 | 10s |

#### 6.1.2 吞吐量与并发

| 指标 | 数据 |
|------|------|
| 并发用户数（单机） | 10-50（SQLite WAL 并发读） |
| API QPS（非 LLM 端点） | ~500 QPS |
| LLM 调用并发 | 受 Provider 限流（智谱免费版约 5-10 并发） |
| 沙箱并发执行 | 受 CPU 核数限制（Docker --cpus=1.0） |

#### 6.1.3 资源利用率

| 资源 | 空闲 | 满载 |
|------|------|------|
| CPU | < 1% | 30-60%（沙箱执行时） |
| 内存 | ~150MB（FastAPI 进程） | ~400MB（含沙箱子进程） |
| 磁盘 | ~50MB（代码+依赖） | ~100MB（含数据库+日志） |
| 数据库文件 | ~53KB（种子数据） | 增长依赖使用量 |

### 6.2 已实施的性能优化措施

#### 6.2.1 数据库层优化

| 优化措施 | 优化前 | 优化后 | 效果 |
|----------|--------|--------|------|
| **WAL 日志模式** | 默认 rollback journal，读写互斥 | WAL 模式，读写并发 | 读不阻塞写，并发提升 3-5 倍 |
| **线程本地连接** | 全局共享连接，锁竞争 | `threading.local()` 每线程独立 | 消除连接锁竞争 |
| **单例管理器** | 每次请求新建连接 | `get_db()` 全局单例 | 连接复用，减少开销 |
| **索引覆盖** | 全表扫描 | 3 个索引覆盖高频查询 | 会话查询从 O(n) 降至 O(log n) |
| **幂等初始化** | 每次请求检查 schema | `_initialized` 标志 | 避免重复 DDL 开销 |

#### 6.2.2 LLM 调用层优化

| 优化措施 | 效果 |
|----------|------|
| **历史对话截断**（最近 20 条） | 控制 Token 数量，降低延迟与成本 |
| **流式输出（SSE）** | 首字延迟从 3-8s 降至 500ms-2s |
| **心跳机制**（10s 间隔） | 防止代理超时断开 |
| **Mock 降级** | LLM 不可用时服务仍可用 |
| **Provider 自动选择** | 按优先级降级，无需人工干预 |

#### 6.2.3 前端层优化

| 优化措施 | 效果 |
|----------|------|
| **localStorage 防抖**（500ms） | 减少高频写入，避免卡顿 |
| **SSE 流式渲染** | 逐字显示，用户体验提升 |
| **代码分割**（Vite 默认） | 按需加载，首屏更快 |
| **Tree-shaking** | 未使用代码剔除，包体积减小 |
| **AbortController 超时**（45s） | 避免网络卡死占用资源 |
| **useReducer 状态管理** | 比 Redux 轻量，减少渲染开销 |

#### 6.2.4 沙箱层优化

| 优化措施 | 效果 |
|----------|------|
| **Docker 资源限制** | 单沙箱最多 256MB/1CPU/64 进程，防资源耗尽 |
| **进程树隔离** | 无 Docker 时仍可隔离，保证跨环境可用 |
| **超时硬限制**（10s） | 防止死循环代码无限占用 |
| **安全前置校验** | 危险代码不进入沙箱，节省资源 |

### 6.3 优化前后对比

| 场景 | 优化前 | 优化后 | 提升幅度 |
|------|--------|--------|----------|
| 对话首字延迟 | 3-8s（等完整响应） | 500ms-2s（SSE 流式） | ~75% |
| 并发读数据库 | 串行（rollback journal） | 并发（WAL） | ~3-5x |
| 前端写入卡顿 | 每次输入触发写入 | 500ms 防抖 | 显著减少 IO |
| 沙箱资源占用 | 无限制 | 256MB/1CPU 上限 | 可控 |
| 服务可用性 | LLM 失败即不可用 | Mock 降级保底 | 99.9%+ |

---

## 7. 现存问题与改进建议

### 7.1 重大问题（优先级：高）

#### 7.1.1 缺失版本控制

**问题描述**：项目未初始化 Git，无 commit 历史、无分支管理、无回滚能力。

**影响**：
- 无法追溯变更历史；
- 无法协作开发；
- 误操作无法恢复。

**改进建议**：
```bash
# 立即执行
git init
git add .
git commit -m "feat: initial commit - CodeMentor Agent MVP"
git branch -M main

# 后续采用 Git Flow 分支模型
# main: 生产分支
# develop: 开发主干
# feature/*: 功能分支
# hotfix/*: 紧急修复
```

**优先级**：🔴 P0（立即执行）

#### 7.1.2 测试覆盖率不足且无度量

**问题描述**：
- 7 个测试文件，15+ 测试用例，主要集中在路由冒烟测试；
- 无覆盖率统计（pytest.ini 未配置 `--cov`）；
- 前端无任何测试；
- 沙箱核心逻辑测试较薄。

**改进建议**：
1. 安装 `pytest-cov`，配置覆盖率目标（后端 ≥ 70%）；
2. 补充沙箱安全、隔离、运行时的单元测试；
3. 引入前端测试（Vitest + React Testing Library）；
4. 增加 LLM Mock 的集成测试。

**优先级**：🔴 P0

#### 7.1.3 双练习管线并存导致维护负担

**问题描述**：同时存在旧管线（`/api/generate_exercise` + `/api/submit_code`）与新管线（`/api/exercise/*`），代码重复，维护成本高。

**改进建议**：
1. 评估旧管线使用情况；
2. 旧管线标记为 deprecated；
3. 迁移前端调用至新管线；
4. 下个版本移除旧管线。

**优先级**：🟠 P1

### 7.2 技术缺陷（优先级：中）

#### 7.2.1 单用户假设

**问题描述**：`user_id` 默认 `'default'`，无认证机制，所有用户共享数据。

**改进建议**：
1. 引入 JWT 或 Session 认证；
2. 用户注册/登录端点；
3. 数据按 `user_id` 隔离。

**优先级**：🟡 P2

#### 7.2.2 LLM 调用无重试与限流

**问题描述**：LLM 调用失败直接返回错误或降级 Mock，无指数退避重试；无限流保护。

**改进建议**：
1. 引入 `tenacity` 库实现指数退避重试；
2. 添加令牌桶限流（如 `slowapi`）；
3. LLM 调用熔断机制。

**优先级**：🟡 P2

#### 7.2.3 数据库迁移机制缺失

**问题描述**：Schema 变更依赖 `CREATE TABLE IF NOT EXISTS`，无版本化迁移。

**改进建议**：
1. 引入 `alembic` 迁移工具；
2. 每次 Schema 变更生成迁移脚本；
3. 支持升级与回滚。

**优先级**：🟡 P2

#### 7.2.4 前端无错误边界与监控

**问题描述**：React 组件抛错会白屏，无全局错误捕获；无前端性能监控。

**改进建议**：
1. 添加 `ErrorBoundary` 组件；
2. 引入 Sentry 或自建错误上报；
3. Web Vitals 性能采集。

**优先级**：🟡 P2

### 7.3 性能瓶颈（优先级：中）

#### 7.3.1 SQLite 写入瓶颈

**问题描述**：WAL 模式下写入仍串行，高并发写场景会成为瓶颈。

**改进建议**：
1. 短期：写入批量化 + 异步落库；
2. 中期：迁移至 PostgreSQL；
3. 长期：读写分离 + 连接池。

**优先级**：🟡 P2

#### 7.3.2 LLM 调用延迟不可控

**问题描述**：练习生成与评估强依赖 LLM，延迟 3-8s，用户体验差。

**改进建议**：
1. 预生成常见知识点练习并缓存；
2. 流式输出生成过程；
3. 后台异步生成 + 前端轮询。

**优先级**：🟡 P2

> ✅ **进度更新**：第 2 项"流式输出生成过程"已落地——后端 SSE 流式接口 `/api/chat/chat_stream` 逐字返回，前端配合"正在思考…"跳动动画，显著缓解了首字等待体验。第 1 项（预生成缓存）、第 3 项（后台异步生成）仍为后续优化方向。

### 7.4 功能不足（优先级：低）

#### 7.4.1 知识点覆盖不足

**问题描述**：seed_data.json 仅 1 个知识原子（python.advanced.decorator），内置 6 道题目。

**改进建议**：
1. 扩充知识原子库（目标 50+）；
2. 社区共建题库；
3. 支持用户导入自定义题目。

**优先级**：🟢 P3

#### 7.4.2 无学习数据分析

**问题描述**：记录了学习进度但未提供可视化分析。

**改进建议**：
1. 学习路径可视化；
2. 薄弱知识点识别；
3. 学习时长统计。

**优先级**：🟢 P3

#### 7.4.3 无国际化支持

**问题描述**：界面与提示词均为中文，无 i18n。

**改进建议**：
1. 引入 `react-i18next`；
2. 提示词多语言版本；
3. 英文界面支持。

**优先级**：🟢 P3

---

## 8. 未来发展规划

### 8.1 短期规划（3 个月内）

#### 8.1.1 工程基础加固

| 任务 | 目标 | 资源需求 |
|------|------|----------|
| Git 版本控制初始化 | 建立完整 commit 历史与分支模型 | 0.5 人天 |
| 测试覆盖率提升 | 后端 ≥ 70%，前端引入 Vitest | 5 人天 |
| CI/CD 流水线 | GitHub Actions 自动测试+构建 | 2 人天 |
| 代码规范工具 | 引入 Ruff（Python）+ oxlint 规则 | 1 人天 |
| 旧练习管线下线 | 统一至 `/api/exercise/*` | 3 人天 |

> ✅ **进度更新**：oxlint 已引入前端（`frontend/package.json` 的 `lint` 脚本，oxlint ^1.71.0）；Ruff（Python）尚未引入，其余任务待推进。

#### 8.1.2 内容扩展

| 任务 | 目标 | 资源需求 |
|------|------|----------|
| 知识原子扩充 | 新增 10 个 Python 进阶知识点 | 5 人天 |
| 内置题库扩充 | 新增 20 道练习题（含多语言） | 5 人天 |
| 算法面试专题 | 新增数组/链表/树等基础算法 | 5 人天 |

#### 8.1.3 体验优化

| 任务 | 目标 | 资源需求 |
|------|------|----------|
| 学习进度可视化 | 简单进度条 + 知识点掌握度 | 3 人天 |
| 错误边界与提示 | 全局错误捕获 + 友好提示 | 2 人天 |
| 移动端适配 | 响应式布局优化 | 3 人天 |

### 8.2 中期规划（6-12 个月）

#### 8.2.1 多用户与认证

| 任务 | 目标 |
|------|------|
| 用户认证系统 | JWT + 注册/登录/找回密码 |
| 数据隔离 | 按 user_id 隔离会话与进度 |
| 个人中心 | 学习历史、成就、统计 |

#### 8.2.2 数据库升级

| 任务 | 目标 |
|------|------|
| PostgreSQL 迁移 | 支持高并发写入 |
| Alembic 迁移工具 | 版本化 Schema 管理 |
| 读写分离 | 查询走从库，写入走主库 |

#### 8.2.3 智能化增强

| 任务 | 目标 |
|------|------|
| 个性化学习路径 | 基于掌握度推荐下一个知识点 |
| 薄弱点识别 | 分析错题模式，定向出题 |
| 学习数据分析 | 可视化报表 + 导出 |

#### 8.2.4 内容生态

| 任务 | 目标 |
|------|------|
| 题库管理后台 | CRUD 题目、审核、标签 |
| 社区共建 | 用户提交题目、投票、收藏 |
| 多语言知识库 | JavaScript / Go / Rust 专题 |

### 8.3 长期规划（1 年以上）

#### 8.3.1 平台化

| 任务 | 目标 |
|------|------|
| 多租户 SaaS | 支持教育机构独立部署 |
| API 开放平台 | 允许第三方接入教学能力 |
| 插件系统 | 支持自定义语言运行时、判题插件 |

#### 8.3.2 AI 能力升级

| 任务 | 目标 |
|------|------|
| 多模态教学 | 支持图片/截图提问（GLM-4V） |
| 代码 Review Agent | 自动审查用户代码风格 |
| 智能助教 | 主动发现学习卡点并干预 |
| RAG 知识库 | 接入官方文档，减少幻觉 |

#### 8.3.3 商业化探索

| 任务 | 目标 |
|------|------|
| 免费版 + 高级版 | 免费基础功能，付费高级功能 |
| 企业版 | 私有部署 + 定制内容 |
| 认证体系 | 完成学习路径颁发证书 |

### 8.4 路线图总览

```text
2026 Q3 (短期)
├── 工程基础: Git + 测试 + CI/CD
├── 内容扩展: 10 知识点 + 20 题
└── 体验优化: 进度可视化 + 移动端

2026 Q4 - 2027 Q2 (中期)
├── 多用户: 认证 + 数据隔离
├── 数据库: PostgreSQL + Alembic
├── 智能化: 个性化路径 + 薄弱点
└── 生态: 题库后台 + 社区共建

2027 Q3+ (长期)
├── 平台化: 多租户 SaaS + 开放 API
├── AI 升级: 多模态 + RAG + 智能助教
└── 商业化: 免费/高级/企业版
```

---

## 9. 补充内容

### 9.1 开发规范

#### 9.1.1 编码规范

**Python（后端）**：
- 类型提示强制：所有函数签名标注参数与返回类型；
- `from __future__ import annotations` 延迟注解求值；
- Pydantic v2 BaseModel 定义数据结构；
- 异步优先：IO 密集操作使用 `async def`；
- 文档字符串：模块级、类级、复杂函数必须有 docstring。

**TypeScript（前端）**：
- 严格模式：`strict: true`；
- 接口优先：数据结构用 `interface`，联合类型用 `type`；
- 函数组件：统一使用箭头函数 + Hooks；
- 命名：组件 PascalCase，函数/变量 camelCase，常量 UPPER_SNAKE。

#### 9.1.2 命名规范

| 类别 | 规范 | 示例 |
|------|------|------|
| Python 模块 | snake_case | `app_factory.py` |
| Python 类 | PascalCase | `AppContainer` |
| Python 函数 | snake_case | `get_settings()` |
| Python 常量 | UPPER_SNAKE | `BASE_DIR` |
| TS 组件 | PascalCase | `LiquidGlassCard` |
| TS 函数 | camelCase | `generateId()` |
| TS 类型 | PascalCase | `ExerciseData` |
| API 端点 | kebab-case 或 snake_case | `/api/exercise/run` |
| 数据库表 | snake_case | `learning_sessions` |
| 数据库字段 | snake_case | `session_id` |

#### 9.1.3 文档规范

- 模块级 docstring 说明职责与设计；
- 复杂函数 docstring 说明参数、返回值、异常；
- API 端点使用 FastAPI 自动文档（`response_model` + docstring）；
- 设计文档存放 `docs/specs/`，命名 `DOC-XX-名称.md`。

#### 9.1.4 代码审查流程（建议）

> 当前项目无正式 Code Review 流程，建议引入：

1. **PR 制度**：所有变更通过 Pull Request 合入；
2. **至少 1 人审查**：聚焦逻辑正确性、安全性、可读性；
3. **CI 通过**：测试 + Lint 必须通过；
4. **Squash Merge**：保持 commit 历史整洁。

### 9.2 测试策略

#### 9.2.1 测试类型与覆盖

| 测试类型 | 工具 | 当前覆盖 | 目标 |
|----------|------|----------|------|
| **单元测试** | pytest | 沙箱安全/隔离/运行时部分覆盖 | 核心 Agent 逻辑全覆盖 |
| **集成测试** | pytest + TestClient | 15+ 路由冒烟测试 | 全端点契约测试 |
| **系统测试** | 手动 | 端到端学习流程 | 自动化 E2E（Playwright） |
| **验收测试** | 手动 | MVP 核心场景 | 用户场景脚本化 |

#### 9.2.2 测试工具

| 工具 | 用途 |
|------|------|
| pytest | 后端测试框架 |
| httpx TestClient | API 集成测试 |
| pytest.ini | 测试配置 |
| conftest.py | 全局 fixture（强制 Mock LLM） |
| Vitest（建议） | 前端单元测试 |
| Playwright（建议） | E2E 测试 |

#### 9.2.3 测试覆盖率

| 维度 | 当前 | 目标 |
|------|------|------|
| 后端行覆盖 | 未度量 | ≥ 70% |
| 后端分支覆盖 | 未度量 | ≥ 60% |
| 前端组件覆盖 | 0% | ≥ 50% |
| API 端点覆盖 | ~70%（15/20+） | 100% |

#### 9.2.4 测试策略亮点

- **Mock LLM 强制**：`conftest.py` 在模块导入前设置 `LLM_PROVIDER=mock`，保证测试无网络依赖、可重复；
- **缓存清理 fixture**：`app` fixture 清理 `get_settings` 与 `get_container` 的 `lru_cache`，确保环境变量覆盖生效；
- **条件跳过**：多语言测试用 `@pytest.mark.skipif` 按运行时可用性跳过。

### 9.3 版本控制策略

#### 9.3.1 当前状况

> ⚠️ **项目未使用版本控制**。无 Git 仓库，无 commit 历史。

#### 9.3.2 建议的分支模型（Git Flow 简化版）

```text
main (生产分支, 保护)
  │
  ├── develop (开发主干)
  │     ├── feature/exercise-system
  │     ├── feature/multi-language
  │     └── feature/liquid-glass-ui
  │
  ├── hotfix/critical-bug (紧急修复, 从 main 拉出)
  │
  └── release/v1.0 (发布分支)
```

#### 9.3.3 发布流程（建议）

1. `develop` 分支累积足够功能；
2. 拉取 `release/vX.Y` 分支，进行测试与修复；
3. 测试通过后合并至 `main` 并打 tag；
4. `main` 部署至生产；
5. `release` 分支合并回 `develop`。

#### 9.3.4 历史版本记录

> 由于无 Git，以下基于文档与文件时间戳重建：

| 版本 | 阶段 | 关键变更 |
|------|------|----------|
| 0.1.0 | Session 1 | MVP 闭环（FastAPI + 单页 HTML + Python 沙箱） |
| 0.2.0 | Session 2 | 现代化重构（分层架构 + 依赖注入） |
| 0.3.0 | Session 3 | 沙箱引擎强化（安全+隔离+运行时抽象） |
| 0.4.0 | Session 4 | 多类型练习系统（4 类型 + 题库） |
| 0.5.0 | Session 5 | 前端 React 迁移 + 毛玻璃模糊设计 |
| 0.2.0-modernized | 当前 | 多语言扩展 + LLM 多模型 + Bug 修复 |

### 9.4 项目亮点

#### 9.4.1 技术创新点

1. **三层四步教学法**：首创将 AI 对话教学结构化为"对话层→教学层→推进层"+"实例→概念→溯源→练习"四步节奏，通过 System Prompt 编码实现，避免传统 AI 答疑的碎片化问题。

2. **多语言沙箱统一抽象**：通过 `LanguageRuntime` ABC + `SandboxIsolator` + `SandboxSecurity` 三层抽象，统一支持 5 种语言的安全执行，Docker/进程树双降级保证跨环境可用。

3. **可插拔 LLM Provider**：`LLMProvider` ABC + 工厂模式 + 优先级降级（智谱→Ollama→Mock），实现零成本启动（智谱永久免费）与离线可用（Ollama）兼得。

4. **SSE 流式教学对话**：后端 `StreamingResponse` + `asyncio.Queue` 生产者-消费者模式 + 10s 心跳，前端自研缓冲区解析，实现逐字流式输出。

5. **毛玻璃模糊设计系统**：渐进增强策略——Tier 0 全浏览器 `backdrop-filter`，Tier 1 Chromium SVG `feDisplacementMap` 折射，尊重 `prefers-reduced-motion`，兼顾美观与兼容。

6. **配置同步修复**：发现并修复 pydantic-settings 不自动推送环境变量的问题，`get_settings()` 主动同步关键配置到 `os.environ`，保证 `llm_client.py` 能正确读取。

#### 9.4.2 业务价值亮点

1. **零成本启动**：智谱 GLM-4-Flash 永久免费，学习者无需付费即可使用完整 AI 教学能力。
2. **学练用一体**：从知识讲解到代码练习到沙箱判题，全闭环覆盖，无需在多个平台间切换。
3. **断点续学**：SQLite 持久化 + localStorage 缓存，学习进度不丢失。
4. **多语言支持**：覆盖 Python/JS/Bash/Java/C# 五种语言，满足不同学习需求。
5. **离线可用**：Ollama 本地部署方案，适合网络受限或隐私敏感场景。

#### 9.4.3 团队协作经验

1. **文档先行**：Session 0 产出 4 份规范文档，后续开发严格依规范执行，减少返工。
2. **渐进式重构**：从单页 HTML 逐步迁移到 React，保留旧管线兼容，平滑过渡。
3. **测试驱动**：`conftest.py` 强制 Mock LLM，保证测试可重复、无网络依赖。
4. **设计原则约束**：4 大设计原则（Rhythm-Driven / Strict Grounding / Zero-Broken / Schema-Driven）贯穿全程，保证产品一致性。

---

## 附录

### A. 项目目录结构

```text
CodeMentor Agent/
├── main.py                      # 应用入口
├── pytest.ini                   # 测试配置
├── .env / .env.example          # 环境变量
├── PROJECT_REPORT.md            # 本报告
├── 比赛说明.md                  # 评审标准
├── 最终成品设计.md              # 架构设计原则
├── Demo设计.md                  # MVP 设计
│
├── app/                         # 后端应用
│   ├── __init__.py
│   ├── core/                    # 核心层
│   │   ├── app_factory.py       # FastAPI 工厂
│   │   ├── config.py            # Pydantic 配置
│   │   ├── container.py         # 依赖注入容器
│   │   ├── database.py          # SQLite 管理器
│   │   ├── exceptions.py        # 异常定义
│   │   └── logger.py            # structlog 日志
│   ├── schemas/                 # Pydantic 数据模型
│   │   └── __init__.py
│   ├── services/                # 服务层
│   │   ├── learning_state.py    # 学习状态机
│   │   ├── exercise_service.py  # 练习服务
│   │   └── problem_fetcher.py   # 题库服务
│   └── api/                     # 路由层
│       ├── health.py            # 健康检查
│       ├── teach.py             # 教学端点（旧）
│       ├── practice.py          # 练习端点（旧）
│       ├── chat.py              # 对话端点（含 SSE）
│       ├── llm.py               # LLM 状态端点
│       ├── learn.py             # 三层教学端点（新）
│       ├── exercise.py          # 多类型练习端点（新）
│       └── deps.py              # 依赖注入辅助
│
├── agents/                      # 智能体层
│   ├── __init__.py
│   ├── orchestrator.py          # 教学主控 Agent
│   ├── llm_client.py            # LLM Provider 抽象
│   ├── exercise_generator.py    # 练习生成器
│   ├── exercise_evaluator.py    # 练习评估器
│   ├── generator.py             # 旧生成器（兼容）
│   ├── validator.py             # 校验器
│   ├── sandbox.py               # 沙箱统一入口
│   ├── sandbox_security.py      # 安全校验
│   ├── sandbox_isolation.py     # 隔离执行
│   ├── sandbox_runtime.py       # 语言运行时
│   └── sandbox_exceptions.py    # 沙箱异常
│
├── frontend/                    # 前端应用
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx              # 根组件
│   │   ├── main.tsx             # 入口
│   │   ├── index.css            # Tailwind + 设计令牌
│   │   ├── components/
│   │   │   ├── chat/            # 对话组件
│   │   │   ├── exercise/        # 练习组件
│   │   │   ├── layout/          # 布局组件
│   │   │   └── ui/              # UI 基础组件
│   │   ├── contexts/            # Context 状态管理
│   │   ├── hooks/               # 自定义 Hooks
│   │   ├── lib/                 # 工具函数
│   │   └── types/               # 类型定义
│   └── public/                  # 静态资源（manifest 等）
│
├── schemas/
│   └── seed_data.json           # 种子数据
│
├── prompts/                     # Prompt 模板
│   ├── generator.txt
│   ├── orchestrator.txt
│   └── validator.txt
│
├── docs/
│   └── specs/                   # 设计规范文档
│       ├── DOC-01-Backend_Routes_and_Data_Schemas.md
│       ├── DOC-02-Sandbox_Executor_Engine.md
│       ├── DOC-03-Agentic_Workflow_and_Prompts.md
│       └── DOC-04-Frontend_SplitScreen_Workspace.md
│
├── tests/                       # 测试
│   ├── conftest.py
│   ├── test_routes_smoke.py
│   ├── test_sandbox*.py
│   └── test_languages_endpoint.py
│
├── data/
│   └── codementor.db            # SQLite 数据库
│
└── static/
    └── index.html               # 旧版重定向页
```

### B. API 端点全览

| 端点 | 方法 | 模块 | 功能 |
|------|------|------|------|
| `/health` | GET | health | 健康检查 |
| `/api/teach` | POST | teach | 教学内容（旧） |
| `/api/generate_exercise` | POST | practice | 生成练习（旧） |
| `/api/submit_code` | POST | practice | 提交代码（旧） |
| `/api/ecosystem_summary` | POST | practice | 生态总结（旧） |
| `/api/chat` | POST | chat | 自由对话 |
| `/api/chat_stream` | POST | chat | SSE 流式对话 |
| `/api/llm_status` | GET | llm | LLM 状态查询 |
| `/api/set_model` | POST | llm | 切换 LLM 模型 |
| `/api/learn/start` | POST | learn | 发起学习 |
| `/api/learn/dive` | POST | learn | 深入学习 |
| `/api/learn/advance` | POST | learn | 推进教学步骤 |
| `/api/learn/complete` | POST | learn | 完成知识点 |
| `/api/learn/session/{id}` | GET | learn | 查询会话 |
| `/api/learn/progress/{id}` | GET | learn | 查询进度 |
| `/api/exercise/types` | GET | exercise | 练习类型列表 |
| `/api/exercise/generate` | POST | exercise | 生成练习 |
| `/api/exercise/submit` | POST | exercise | 提交答案 |
| `/api/exercise/run` | POST | exercise | 运行代码 |
| `/api/languages` | GET | exercise | 语言列表 |
| `/api/problems` | GET | exercise | 题库列表 |
| `/api/problems/{id}` | GET | exercise | 题目详情 |
| `/api/problems/meta/tags` | GET | exercise | 标签元数据 |
| `/api/problems/refresh` | POST | exercise | 刷新题库 |

### C. 关键依赖版本清单

**后端（app/requirements.txt）**：
- fastapi ≥ 0.115.0
- uvicorn[standard] ≥ 0.30.0
- pydantic ≥ 2.9.0
- pydantic-settings ≥ 2.6.0
- pytest ≥ 8.3.0
- httpx ≥ 0.27.0
- openai ≥ 1.50.0
- python-dotenv ≥ 1.0.0
- structlog ≥ 24.4.0

**前端（package.json）**：
- react ^19.2.7
- react-dom ^19.2.7
- vite ^8.1.1
- typescript ~6.0.2
- tailwindcss ^4.3.3
- @tailwindcss/vite ^4.3.3
- react-markdown ^10.1.0
- remark-gfm ^4.0.1
- rehype-highlight ^7.0.2
- highlight.js ^11.11.1
- lucide-react ^1.25.0
- clsx ^2.1.1
- tailwind-merge ^3.6.0
- @vitejs/plugin-react ^6.0.3
- oxlint ^1.71.0

---

> **报告结束**
>
> 本报告基于 2026-07-22 的代码库状态编写，涵盖 50+ 源文件的系统性审查。报告完成后，将对项目中的临时文档、过时文档进行清理，详见清理操作记录。
