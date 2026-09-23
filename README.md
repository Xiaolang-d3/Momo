# Momo

> 品牌名：**Momo**（会思考、会判断、会执行的 Agent）

**Momo Agent 底座（kernel）**：薄内核 + 后续厚插件。  
接收任务 → 推理规划 → 决定工具 → HITL 确认 → 执行（失败可重试，耗尽则 `blocked`）。

> 本项目为全新实现。默认 `--demo` 离线模式，**无需任何 LLM API Key**。  
> 会议插件 / FastAPI UI 为下一阶段，本仓库当前只交付 runtime 底座。

## 功能概览

- **Agent 循环**：`reason` → `decide` → `confirm`(HITL) → `execute` →（重试或回 `decide`）
- **状态**：`running` | `awaiting_confirm` | `done` | `cancelled` | `error` | `blocked`
- **工具失败策略**：可配置重试（默认额外 1 次），仍失败则 `status=blocked` + `block_reason`（不静默成泛化 error）
- **HITL**：LangGraph `interrupt` + `Command(resume=...)` + `MemorySaver`
- **Model Provider**（`src/momo/provider/`）
  - `DemoProvider`：确定性离线
  - `OpenAICompatibleProvider`：`OPENAI_API_KEY` + `OPENAI_BASE_URL`
  - `OllamaProvider`：`OLLAMA_BASE_URL` + 模型名
  - 工厂：`get_provider()` / 环境变量 `MOMO_PROVIDER=demo|openai|ollama`（默认 demo）
  - `reason` 在非 demo 计划模式下会调用 provider；失败或 demo 则回退 `build_demo_plan`
- **库工具**（内存原型）
  - `search_library(query)`：关键词搜索
  - `get_library_context(doc_id)`：取单篇文档
- **其它内置工具**：`echo` / `add` / `propose_action`(HITL) / `flaky_once`(演示重试) / `always_fail`(演示 blocked)
- **插件契约 stub**：`src/momo/plugins/` — 场景能力（会议等）在此挂载；`load_plugins(registry)` 当前为空操作

## 目录结构

```
momo/
  README.md
  requirements.txt
  .env.example
  run.py
  src/momo/
    __init__.py
    __main__.py
    state.py
    demo_plan.py       # 离线演示规划 + provider 尝试
    nodes.py           # reason/decide/confirm/execute
    graph.py           # StateGraph 装配与路由
    cli.py
    provider/          # Model Provider 骨架
    plugins/           # 场景插件契约（stub）
    tools/
      registry.py
      builtin.py
      library.py       # 内存文档库工具
```

## 安装

```bash
cd momo   # 或 Desktop/momo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

```bash
# 模块入口（推荐）
PYTHONPATH=src python -m momo --demo

# 非交互验证（自动同意 HITL；覆盖多步 + 库工具 + 重试 + HITL）
PYTHONPATH=src python -m momo --demo --auto-approve

# 调整工具重试次数
PYTHONPATH=src python -m momo --demo --auto-approve --max-tool-retries 1
```

### HITL 交互

执行到 `propose_action`（或其它 `requires_confirmation=True`）时图会暂停：

1. 同意执行  
2. 跳过  
3. 取消任务  

### Provider 切换

复制 `.env.example` → `.env`：

```bash
export MOMO_PROVIDER=demo     # 默认，无需 Key
# export MOMO_PROVIDER=openai
# export OPENAI_API_KEY=...
# export OPENAI_BASE_URL=https://api.openai.com/v1
# export MOMO_PROVIDER=ollama
# export OLLAMA_BASE_URL=http://127.0.0.1:11434
```

`--demo` **从不要求** API Key。`--no-demo` 时走 provider；若 provider 失败仍回退演示规划。

## 插件扩展点

场景（会议纪要、日程等）应实现 `momo.plugins.base.BasePlugin` / `Plugin`，并在 `load_plugins(registry)` 中注册工具。  
**内核保持精简**；业务能力放进 plugins，不要塞进 `graph.py`。

## 许可

原型代码，按需使用。
