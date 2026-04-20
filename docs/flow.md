# Flow

## MVP flow

1. User provides a task
2. Orchestrator creates a plan
3. Orchestrator checks approval
4. Developer Agent runs with the selected provider
5. Tester Agent runs local tests
6. Final result is returned

## Approval rule

No code change should happen without approval.

For now, approval is passed in the workflow state.
Later, Streamlit can collect the answer from the user.
