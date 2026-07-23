# DOC-04: Frontend SplitScreen Workspace Specification

> **文档定位**：CodeMentor Agent MVP 前端单页应用规范
> **依据**：`Demo设计.md` §1.1 UI 裁剪（左侧 Agent 聊天 + 右侧 Monaco Editor 双栏 HTML 单页）+ §2.1 目录结构（static/index.html）+ §4 End-to-End Sequence
> **状态**：Session 0 规范确立
> **约束**：单页 HTML（MVP 不引入前端构建工具），CDN 加载 Monaco Editor

---

## 1. 文档概述

本规范定义 CodeMentor Agent MVP 前端 `static/index.html` 单页应用，包含：
- 双栏布局结构（左侧 Chat + 右侧 Monaco Editor）
- Monaco Editor 初始化与配置
- 三状态机驱动的 UI 切换（TeachMode / PracticeMode / EcosystemMode）
- 与 FastAPI 后端的 fetch 通信封装
- 用户交互流程与错误处理

### 1.1 MVP 裁剪方案（匹配 Demo设计.md §1.1）
- ✅ 采取「左侧 Agent 聊天对话 + 右侧 Monaco Editor」双栏 HTML 单页结构
- ❌ 替代复杂的前端框架（React/Vue）

### 1.2 技术选型
| 项目 | 选型 | 理由 |
|------|------|------|
| HTML 结构 | 单文件 `index.html` | MVP 极简，无需构建工具 |
| 样式 | 内嵌 `<style>` | 减少文件依赖 |
| 脚本 | 内嵌 `<script>` | 减少文件依赖 |
| 代码编辑器 | Monaco Editor（CDN） | VSCode 同款，支持 Python 语法高亮 |
| 通信 | fetch API | 原生支持，无需第三方库 |
| Markdown 渲染 | marked.js（CDN） | 轻量 Markdown 解析 |

### 1.3 目录结构
```
codementor-mvp/
└── static/
    └── index.html      # 双栏单页应用（HTML + CSS + JS 内嵌）
```

---

## 2. 页面布局结构

### 2.1 整体布局

```text
┌─────────────────────────────────────────────────────────────────┐
│  Header: CodeMentor Agent | 当前状态徽章: TeachMode            │
├──────────────────────────────┬──────────────────────────────────┤
│                              │                                  │
│  Left Panel (40% width)      │  Right Panel (60% width)         │
│  ┌────────────────────────┐  │  ┌────────────────────────────┐  │
│  │ Agent Chat Workspace   │  │  │ Monaco Editor Workspace   │  │
│  │                        │  │  │                            │  │
│  │ ┌──────────────────┐   │  │  │  def rate_limit(...):      │  │
│  │ │ Agent Message    │   │  │  │      # 请补全代码           │  │
│  │ │ (Markdown)       │   │  │  │      pass                  │  │
│  │ └──────────────────┘   │  │  │                            │  │
│  │                        │  │  │                            │  │
│  │ ┌──────────────────┐   │  │  │                            │  │
│  │ │ User Message     │   │  │  │                            │  │
│  │ └──────────────────┘   │  │  │                            │  │
│  │                        │  │  │                            │  │
│  └────────────────────────┘  │  └────────────────────────────┘  │
│  ┌────────────────────────┐  │  ┌────────────────────────────┐  │
│  │ Action Buttons:        │  │  │ Action Buttons:             │  │
│  │ [开始练习] [更多示例]  │  │  │ [提交代码] [重置]           │  │
│  └────────────────────────┘  │  └────────────────────────────┘  │
└──────────────────────────────┴──────────────────────────────────┘
```

### 2.2 HTML 骨架

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeMentor Agent</title>
    <!-- Monaco Editor CDN -->
    <script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js"></script>
    <!-- marked.js for Markdown rendering -->
    <script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
    <style>
        /* 见 §3 样式规范 */
    </style>
</head>
<body>
    <header class="app-header">
        <h1>CodeMentor Agent</h1>
        <span id="state-badge" class="state-badge">TeachMode</span>
    </header>
    
    <main class="workspace">
        <!-- 左侧 Agent Chat -->
        <section class="chat-panel">
            <div id="chat-messages" class="chat-messages"></div>
            <div class="chat-actions">
                <button id="btn-practice">开始练习</button>
                <button id="btn-more-examples">更多示例</button>
                <button id="btn-ecosystem">查看生态总结</button>
            </div>
        </section>
        
        <!-- 右侧 Monaco Editor -->
        <section class="editor-panel">
            <div id="monaco-editor" class="monaco-editor"></div>
            <div class="editor-actions">
                <button id="btn-submit">提交代码</button>
                <button id="btn-reset">重置</button>
            </div>
            <div id="test-result" class="test-result hidden"></div>
        </section>
    </main>
    
    <script>
        /* 见 §5-§7 JS 逻辑 */
    </script>
</body>
</html>
```

---

## 3. 样式规范

### 3.1 设计原则

- **双栏布局**：`display: flex`，左 40% / 右 60%
- **配色方案**：VSCode Dark+ 风格（暗色主题，护眼）
- **响应式**：MVP 暂不支持移动端，最小宽度 1024px

### 3.2 关键样式

```css
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
    background: #1e1e1e;
    color: #d4d4d4;
    height: 100vh;
    display: flex;
    flex-direction: column;
}

.app-header {
    background: #252526;
    padding: 12px 24px;
    border-bottom: 1px solid #3c3c3c;
    display: flex;
    align-items: center;
    gap: 16px;
}

.state-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    background: #007acc;
    color: white;
}

.state-badge.practice { background: #f9a825; }
.state-badge.ecosystem { background: #4caf50; }

.workspace {
    flex: 1;
    display: flex;
    overflow: hidden;
}

.chat-panel {
    width: 40%;
    border-right: 1px solid #3c3c3c;
    display: flex;
    flex-direction: column;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
}

.chat-message {
    margin-bottom: 12px;
    padding: 12px;
    border-radius: 8px;
    max-width: 90%;
}

.chat-message.agent {
    background: #2d2d30;
    border-left: 3px solid #007acc;
}

.chat-message.user {
    background: #2d4a2d;
    margin-left: auto;
    border-left: 3px solid #4caf50;
}

.chat-actions {
    padding: 12px;
    border-top: 1px solid #3c3c3c;
    display: flex;
    gap: 8px;
}

.editor-panel {
    width: 60%;
    display: flex;
    flex-direction: column;
}

.monaco-editor {
    flex: 1;
}

.editor-actions {
    padding: 12px;
    border-top: 1px solid #3c3c3c;
    display: flex;
    gap: 8px;
}

.test-result {
    padding: 12px;
    border-top: 1px solid #3c3c3c;
    max-height: 200px;
    overflow-y: auto;
}

.test-result.passed { background: #1e3a1e; color: #4caf50; }
.test-result.failed { background: #3a1e1e; color: #f44336; }

.hidden { display: none; }

button {
    padding: 8px 16px;
    background: #0e639c;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
}

button:hover { background: #1177bb; }
button:disabled { background: #555; cursor: not-allowed; }
```

---

## 4. Monaco Editor 初始化

### 4.1 初始化代码

```javascript
let editor = null;

require.config({
    paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
});

require(['vs/editor/editor.main'], function () {
    editor = monaco.editor.create(document.getElementById('monaco-editor'), {
        value: '// 等待加载练习题...',
        language: 'python',
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        readOnly: true,  // 初始只读，加载题目后可编辑
        tabSize: 4,
    });
});
```

### 4.2 编辑器操作 API

```javascript
// 设置编辑器内容
function setEditorContent(code) {
    if (editor) {
        editor.setValue(code);
    }
}

// 获取编辑器内容
function getEditorContent() {
    return editor ? editor.getValue() : '';
}

// 设置只读模式
function setReadOnly(readonly) {
    if (editor) {
        editor.updateOptions({ readOnly: readonly });
    }
}
```

---

## 5. 与 FastAPI 后端的 fetch 通信封装

### 5.1 通用请求函数

```javascript
const API_BASE = '';  // 同源，无需指定 host

async function apiRequest(endpoint, payload) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || `HTTP ${response.status}`);
        }
        
        return data;
    } catch (error) {
        showErrorMessage(`请求失败: ${error.message}`);
        throw error;
    }
}
```

### 5.2 四个 API 调用封装

```javascript
// 1. 触发 TeachMode
async function fetchTeachContent(nodeId) {
    return apiRequest('/api/teach', {
        node_id: nodeId,
        action: 'start',
    });
}

// 2. 触发 PracticeMode（双 Agent 出题）
async function fetchGenerateExercise(nodeId) {
    return apiRequest('/api/generate_exercise', {
        node_id: nodeId,
    });
}

// 3. 提交用户代码判题
async function fetchSubmitCode(exerciseId, userCode) {
    return apiRequest('/api/submit_code', {
        exercise_id: exerciseId,
        user_code: userCode,
    });
}

// 4. 触发 EcosystemMode
async function fetchEcosystemSummary(nodeId) {
    return apiRequest('/api/ecosystem_summary', {
        node_id: nodeId,
    });
}
```

---

## 6. 状态机驱动的 UI 切换

### 6.1 全局状态

```javascript
const AppState = {
    current: 'TeachMode',  // TeachMode | PracticeMode | EcosystemMode
    nodeId: 'python.advanced.decorator',
    exerciseId: null,
    starterCode: '',
};

function setState(newState) {
    AppState.current = newState;
    const badge = document.getElementById('state-badge');
    badge.textContent = newState;
    badge.className = 'state-badge ' + newState.toLowerCase().replace('mode', '');
}
```

### 6.2 状态流转与 UI 响应

```javascript
// TeachMode → PracticeMode
async function startPractice() {
    setState('PracticeMode');
    appendAgentMessage('正在生成练习题，请稍候...');
    
    const result = await fetchGenerateExercise(AppState.nodeId);
    AppState.exerciseId = result.exercise_id;
    AppState.starterCode = result.starter_code;
    
    appendAgentMessage(result.problem_statement);  // Markdown 渲染
    setEditorContent(result.starter_code);
    setReadOnly(false);
}

// PracticeMode → 提交代码
async function submitCode() {
    const userCode = getEditorContent();
    appendUserMessage('提交代码进行判题...');
    
    const result = await fetchSubmitCode(AppState.exerciseId, userCode);
    
    showTestResult(result);
    
    if (result.passed) {
        appendAgentMessage(`🎉 全部通过！得分: ${result.score}\n点击"查看生态总结"进入下一阶段。`);
        setState('EcosystemMode');
    } else {
        appendAgentMessage(`未通过。${result.pytest_output}\n请修改后重新提交。`);
    }
}

// EcosystemMode
async function showEcosystem() {
    const result = await fetchEcosystemSummary(AppState.nodeId);
    appendAgentMessage(renderEcosystem(result));
    setState('EcosystemMode');
}
```

---

## 7. 4 个 API 调用流程（匹配 Demo设计.md §4 序列图）

### 7.1 端到端流程

```text
1. 页面加载
   → fetchTeachContent('python.advanced.decorator')
   ← Markdown 教学内容渲染到左侧 Chat
   ← next_actions 显示为按钮

2. 用户点击「开始练习」
   → fetchGenerateExercise('python.advanced.decorator')
   ← 后端调用 Generator + Validator 双 Agent
   ← exercise_id, problem_statement, starter_code
   → Monaco Editor 加载 starter_code（只读解除）

3. 用户编写代码后点击「提交代码」
   → fetchSubmitCode(exercise_id, user_code)
   ← passed, score, pytest_output, next_state
   → 显示测试结果
   → 若 passed: 显示「查看生态总结」按钮
   → 若 failed: 保持 PracticeMode，允许重试

4. 用户点击「查看生态总结」
   → fetchEcosystemSummary('python.advanced.decorator')
   ← stack_summary, cross_language_equivalent, next_node_recommendation
   → 渲染生态总结到左侧 Chat
```

### 7.2 初始化触发

```javascript
// 页面加载完成后自动触发 TeachMode
document.addEventListener('DOMContentLoaded', async () => {
    await initMonacoEditor();  // 等待 Monaco 加载
    await loadTeachContent();  // 触发 /api/teach
});

async function loadTeachContent() {
    const result = await fetchTeachContent(AppState.nodeId);
    appendAgentMessage(result.markdown_content);
    appendAgentMessage(`**基准源**: ${result.grounding_source}\n**历史演进**: ${result.history_notes}`);
    renderNextActions(result.next_actions);
}
```

---

## 8. 用户交互流程

### 8.1 按钮事件绑定

```javascript
document.getElementById('btn-practice').addEventListener('click', startPractice);
document.getElementById('btn-more-examples').addEventListener('click', loadMoreExamples);
document.getElementById('btn-ecosystem').addEventListener('click', showEcosystem);
document.getElementById('btn-submit').addEventListener('click', submitCode);
document.getElementById('btn-reset').addEventListener('click', resetEditor);
```

### 8.2 Chat 消息渲染

```javascript
function appendAgentMessage(markdownContent) {
    const messages = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = 'chat-message agent';
    msg.innerHTML = marked.parse(markdownContent);  // Markdown → HTML
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;  // 自动滚动到底部
}

function appendUserMessage(text) {
    const messages = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = 'chat-message user';
    msg.textContent = text;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
}
```

### 8.3 测试结果展示

```javascript
function showTestResult(result) {
    const resultDiv = document.getElementById('test-result');
    resultDiv.classList.remove('hidden', 'passed', 'failed');
    
    if (result.passed) {
        resultDiv.classList.add('passed');
        resultDiv.innerHTML = `
            <strong>✓ 全部通过</strong><br>
            得分: ${result.score}/100<br>
            <pre>${result.pytest_output}</pre>
        `;
    } else {
        resultDiv.classList.add('failed');
        resultDiv.innerHTML = `
            <strong>✗ 未通过</strong><br>
            得分: ${result.score}/100<br>
            <pre>${result.pytest_output}</pre>
        `;
    }
}
```

---

## 9. 错误处理与 Loading 状态

### 9.1 错误提示

```javascript
function showErrorMessage(message) {
    const messages = document.getElementById('chat-messages');
    const msg = document.createElement('div');
    msg.className = 'chat-message error';
    msg.style.background = '#3a1e1e';
    msg.style.borderLeft = '3px solid #f44336';
    msg.innerHTML = `<strong>错误:</strong> ${message}`;
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
}
```

### 9.2 Loading 状态

```javascript
function setLoading(buttonId, loading) {
    const btn = document.getElementById(buttonId);
    if (loading) {
        btn.disabled = true;
        btn.dataset.originalText = btn.textContent;
        btn.textContent = '处理中...';
    } else {
        btn.disabled = false;
        btn.textContent = btn.dataset.originalText || btn.textContent;
    }
}
```

### 9.3 网络错误处理

```javascript
async function apiRequest(endpoint, payload) {
    try {
        // ... 请求逻辑
    } catch (error) {
        if (error.message.includes('Failed to fetch')) {
            showErrorMessage('无法连接到服务器，请检查后端服务是否启动');
        } else {
            showErrorMessage(error.message);
        }
        throw error;
    }
}
```

---

## 10. 验收清单

- [ ] `static/index.html` 单文件包含 HTML + CSS + JS
- [ ] 双栏布局正确显示（左 Chat 40% / 右 Editor 60%）
- [ ] Monaco Editor 通过 CDN 加载成功
- [ ] Monaco Editor 初始只读，加载题目后可编辑
- [ ] 状态徽章随状态切换变色（TeachMode 蓝 / PracticeMode 黄 / EcosystemMode 绿）
- [ ] 4 个 API 调用流程完整实现
- [ ] Markdown 内容正确渲染（使用 marked.js）
- [ ] 错误场景显示友好提示（不显示原始 Traceback）
- [ ] Loading 状态按钮禁用并显示「处理中...」
- [ ] 测试结果正确区分 passed/failed 样式
- [ ] 页面加载自动触发 TeachMode
- [ ] 提交通过后显示「查看生态总结」入口

---

## 11. 依赖关系

- **上游依赖**：
  - DOC-01（后端路由）：前端 fetch 调用 4 个 API 端点
  - DOC-03（Agent 工作流）：前端通过 API 间接触发 Agent 工作流
- **外部依赖**（CDN）：
  - Monaco Editor 0.45.0
  - marked.js 11.1.1
- **部署**：
  - 通过 FastAPI `StaticFiles` 挂载在 `/static` 路径
  - 访问地址：`http://localhost:8000/static/index.html`
