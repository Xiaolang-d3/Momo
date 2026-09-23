# Momo

> 品牌名：**Momo**（会思考、会判断、会执行的 Agent 原型）

**Momo** 最小 LangGraph Agent 原型：接收任务 → 推理规划 → 决定是否调用工具 → 执行工具 → 多步循环。\
内置插件式工具注册表，以及 **HITL（Human-in-the-Loop）** 确认中断。

> 本项目为全新实现，不依赖其他仓库代码。默认 `--demo` 离线模式，**无需任何 LLM API Key**。

## 功能概览

- **Agent 循环**：`reason` → `decide` → `confirm`(HITL) → `execute` → 回到 `decide`
- **工具注册表**：`register(name, fn, description, requires_confirmation=False)`
- **内置工具**
  - `echo`：回显文本
  - `add`：两数相加
  - `propose_action`：敏感动作（**强制 HITL 确认**）
- **HITL**：使用 LangGraph `interrupt` + `Command(resume=...)` + `MemorySaver` 检查点
- **离线 Demo**：确定性规划器，开箱即用

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
    graph.py
    cli.py
    tools/
      __init__.py
      registry.py
      builtin.py
```

## 安装

```bash
cd /Users/kkxny/Desktop/momo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

在项目根目录、已激活 venv 的前提下：

```bash
# 方式 A：模块入口（推荐）
PYTHONPATH=src python -m momo --demo

# 方式 B：根目录启动脚本
PYTHONPATH=src python run.py --demo

# 非交互验证（自动同意 HITL）
PYTHONPATH=src python -m momo --demo --auto-approve
```

自定义任务文案：

```bash
PYTHONPATH=src python -m momo --demo "帮我演示多步工具调用"
```

### HITL 交互说明

当执行到 `propose_action`（或其它 `requires_confirmation=True` 的工具）时，图会 **暂停** 并提示：

1. 同意执行
2. 跳过
3. 取消任务

输入编号或全文后，通过 `Command(resume=choice)` 恢复执行。

## 可选：真实 LLM

复制 `.env.example` 为 `.env` 并填写 `OPENAI_API_KEY`。当前版本规划器以离线 Demo 为主；LLM 规划可后续接入 `reason` 节点。无 Key 时仍可完整跑通 Demo。

## 许可

原型代码，按需使用。
