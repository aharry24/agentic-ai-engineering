# LinkedIn Content Automation with n8n + AutoGen

> **Status:** Not started

An n8n workflow calls an AutoGen microservice in which agents draft and review LinkedIn posts.

## What I built

- _Fill in: what you built and anything you changed or extended from the starter material._

## How to run

1. Run n8n locally: `docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n`
2. In n8n, **Import from file** and choose `workflow/workflow.json`.
3. Re-create the credentials in n8n (they are never exported with the workflow).

## Files

| File | What it is |
|---|---|
| `workflow/workflow.json` | Exported n8n workflow, **without credentials** |
| `screenshots/` | Workflow canvas and a sample run |

## Results

_Fill in: a screenshot, sample output, or a short table of results._

## Key takeaways

- _Fill in: 2–4 things you learned or would do differently._

## Architecture

_Fill in: n8n trigger → AutoGen service (draft → review) → approved post._

| Folder | Contents |
|---|---|
| [`autogen-service/`](autogen-service) | The AutoGen microservice (API) |
| [`n8n-workflow/`](n8n-workflow) | Exported workflow JSON (no credentials) and screenshots |
