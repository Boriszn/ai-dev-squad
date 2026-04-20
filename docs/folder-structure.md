# Folder structure

## Root files

- `README.md`  
  Main project overview and usage guide.

- `requirements.txt`  
  Python dependencies.

- `.env.example`  
  Example environment variables.

## App folders

- `app/config/`  
  Environment and logging.

- `app/agents/`  
  Agent classes.

- `app/graph/`  
  LangGraph state, nodes, edges, and workflow.

- `app/models/`  
  Provider interface and routing.

- `app/tools/`  
  Tool wrappers for Codex, tests, files, and approval helpers.

- `app/services/`  
  Small helper logic outside the graph.

- `app/prompts/`  
  Prompt text files.

- `app/ui/`  
  Inactive Streamlit UI scaffold.

## Other folders

- `tests/`  
  Unit tests.

- `docs/`  
  Extra documentation.

- `scripts/`  
  Local run helpers.
