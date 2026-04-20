# AI Dev Squad

AI Dev Squad is a local-first MVP for a Human-in-the-Loop AI coding system.

The project uses:
- **LangGraph** for the workflow and agent orchestration.
- **Local tools** for coding and testing.
- **Codex CLI** as the default coding provider.
- **A local model provider placeholder** as the second provider for offline mode later.
- **Streamlit** as the future chat UI, included but not active yet.

## Goal

Build a small agent squad with three roles:

1. **Orchestrator Agent**
   - Understands the user task.
   - Builds a simple execution plan.
   - Decides whether the next step is approval, development, or testing.

2. **Developer Agent**
   - Uses a coding provider to create or update code.
   - Starts with **Codex CLI** as the default provider.
   - Can later switch to a local model provider without changing the orchestration logic.

3. **Tester Agent**
   - Runs local test commands.
   - Returns a simple test summary and status.

## Current MVP scope

This repository contains a clean starter scaffold with:

- LangGraph workflow
- Agent classes
- Model router
- Codex provider wrapper
- Local provider placeholder
- Tool layer
- Inactive Streamlit UI
- Unit tests
- Extra project docs

## Architecture overview

```text
User / Future Chat UI
        |
        v
  Orchestrator Agent
        |
        v
   Approval Step
        |
        v
   Developer Agent ----> Model Router ----> Codex Provider (default)
        |                                  Local Provider (placeholder)
        v
   Tester Agent ----> Test Runner
        |
        v
     Final Result
```

## Project structure

```text
ai-dev-squad/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── logging_config.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── developer.py
│   │   └── tester.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py
│   │   ├── nodes.py
│   │   ├── edges.py
│   │   └── workflow.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base_provider.py
│   │   ├── model_router.py
│   │   ├── codex_provider.py
│   │   └── local_provider.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── codex_tool.py
│   │   ├── test_runner.py
│   │   ├── file_tool.py
│   │   └── approval_tool.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_service.py
│   │   └── execution_service.py
│   ├── prompts/
│   │   ├── orchestrator_prompt.txt
│   │   ├── developer_prompt.txt
│   │   └── tester_prompt.txt
│   └── ui/
│       ├── __init__.py
│       ├── streamlit_app.py
│       └── components.py
├── tests/
│   ├── __init__.py
│   ├── test_orchestrator.py
│   ├── test_developer.py
│   ├── test_tester.py
│   ├── test_model_router.py
│   └── test_workflow.py
├── docs/
│   ├── architecture.md
│   ├── flow.md
│   ├── folder-structure.md
│   └── roadmap.md
└── scripts/
    ├── run_local.py
    ├── run_streamlit.py
    └── demo_task.py
```

## Folder descriptions

### `app/`
Main application package.

### `app/config/`
Configuration and logging setup.

### `app/agents/`
Agent logic for Orchestrator, Developer, and Tester.

### `app/graph/`
LangGraph state, nodes, edge routing, and workflow creation.

### `app/models/`
Model provider interface, router, Codex provider, and local model placeholder.

### `app/tools/`
Low-level tool wrappers for approvals, file actions, Codex execution, and test execution.

### `app/services/`
Small helper services to keep the agent files clean.

### `app/prompts/`
Prompt templates. These are simple text files now, but they give you a clean place to keep agent instructions.

### `app/ui/`
Future Streamlit UI layer. It is included in the project, but not active yet.

### `tests/`
Unit tests for the main flow and components.

### `docs/`
Extra documentation for architecture, flow, roadmap, and folder descriptions.

### `scripts/`
Convenience scripts for local runs.

## How the model routing works

The Developer Agent never talks directly to a specific provider.  
Instead it calls the **Model Router**.

This keeps the design clean:

- `CodexProvider` is the default provider.
- `LocalProvider` is the offline placeholder.
- You can add new providers later without changing the graph flow.

## Default provider

The default provider is **Codex**.

The Codex provider assumes:
- Codex CLI is installed
- You are already signed in
- The `codex` command is available on your machine

If not, the provider returns a safe error message instead of changing files.

## Local model placeholder

The project also includes a local provider placeholder.  
The code comments mention a future option such as:

- `qwen2.5-coder:7b` via Ollama

This provider is intentionally simple for now. It is here to make the switch easy later.

## Human-in-the-Loop

This MVP is designed with a hard approval gate:

- no development step without approval
- no test step without approval

For now the approval value is passed in state.  
Later the Streamlit UI can collect it from the user.

## Quick start

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install packages

```bash
pip install -r requirements.txt
```

### 3. Copy the environment file

```bash
cp .env.example .env
```

### 4. Run the local demo

```bash
python scripts/run_local.py
```

### 5. Run tests

```bash
pytest
```

## Streamlit UI

The Streamlit UI files are included but not active yet.

When you want to explore them later:

```bash
streamlit run app/ui/streamlit_app.py
```

## Notes

- This scaffold is intentionally simple.
- The graph works with mock-friendly logic.
- Real Codex use depends on local CLI setup.
- The local model path is a placeholder for the next phase.

## Next steps

1. Replace mock developer execution with stricter Codex task handling.
2. Add real approval capture from Streamlit.
3. Add richer test result parsing.
4. Add persistent task history.
5. Add ChatGPT + MCP integration later.

