# Architecture

## Summary

AI Dev Squad is a local-first MVP for a Human-in-the-Loop coding workflow.

## Core parts

- **Orchestrator Agent**
  - builds a plan
  - enforces the approval gate
  - routes the workflow

- **Developer Agent**
  - sends work to the selected coding provider
  - does not know provider details directly

- **Tester Agent**
  - runs local tests
  - reports status

## Provider split

The Developer Agent uses a model router.

This gives:
- clean separation of concerns
- easy switch between Codex and local models
- less change in workflow code later

## Current providers

- **CodexProvider**
  - default provider
  - uses local Codex CLI

- **LocalProvider**
  - placeholder for offline mode later
  - current target note: `qwen2.5-coder:7b`

## Future direction

Later phases can add:
- Streamlit approval capture
- richer task history
- ChatGPT + MCP front door
- more agents such as Reviewer or Security
