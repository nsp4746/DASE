# DASE

Dynamic Adversary Simulation Engine: fictional cybersecurity tabletop exercises
that adapt to defender decisions. Supports Google Gemini, OpenAI, and local
Apple MLX inference through a Dear PyGui desktop interface.

## Run the desktop app

For local MLX, open **`run_dase.py`** in VS Code and press **Run Python File** (▶).
It uses this repo's `.venv`, starts the local server, and opens DASE with MLX
selected. Closing DASE stops the server it started; an already-running server is
reused and left running. Install MLX-LM once with
`.venv/bin/python -m pip install 'mlx-lm==0.32.2'`.
The first inference can download the selected model. Launcher/server output appears
in the terminal; Stop with Ctrl+C there to clean up both processes.

For a terminal-only exercise, press **Run Python File** on **`run_dase_cli.py`**.
It starts or reuses the same local server, uses the same scenario/session logic,
and opens no GUI. Defaults are Well Connect, low difficulty, and three reactions.
Use `/save` to export, `/retry` after a failed request, or `/quit` to exit.
Completed turns are also saved on exit. To diagnose local inference errors:

```bash
.venv/bin/python run_dase_cli.py --debug
# Use a server you started separately and leave its lifecycle untouched:
.venv/bin/python run_dase_cli.py --connect-only --debug
# Deliberately increase output and history limits for a test run:
.venv/bin/python run_dase_cli.py --debug --max-tokens 1536 --max-history-chars 64000
```

`--max-tokens` limits each response; `--max-history-chars` limits all input text,
including the prompt and profile. These are different limits. Increasing either
can require more memory and time. Use `--help` for company, difficulty, model,
reaction-count, and timeout options. Debug mode prints tracebacks and local HTTP
error bodies in your terminal. Failed/partial turns never enter session history.

Use Python 3.12 or 3.13 from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m dase
```

Use `.env.example` as the template for a root `.env` file, preserving any existing
configuration. Cloud providers require their respective API keys. Local MLX
requires a running localhost server and no cloud credentials; follow the
[MLX setup guide](docs/mlx-integration.md).

## Repository map

```text
dase/                    Application code
  providers/             Gemini, OpenAI, and local MLX clients
data/
  company_profiles/      Fictional company JSON profiles
  prompts/               Active scenario prompt
docs/
  mlx-integration.md     Architecture assessment and MLX setup
  archive/               Academic report and reference material
  images/                Documentation images
tests/                   Offline provider, session, and GUI callback tests
run_dase.py              Start local MLX and the desktop with one Run button
run_dase_cli.py          Test local MLX exercises in the terminal without a GUI
requirements.txt         Current application dependencies
requirements/legacy.txt  Historical dependency list
mlx-dase/                Local MLX server environment and scratch script
```

`.venv/`, `mlx-dase/.venv/`, `.env`, and `session_logs/` stay local and are ignored
by Git. Virtual environments stay in their original locations.

## Test

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Tests do not download models or contact cloud APIs.

## Other entry points

```bash
.venv/bin/python -m dase.providers.gemini
.venv/bin/python -m dase.providers.openai_cli
.venv/bin/python -m dase.utils
```

The [original project description](docs/archive/README-academic.md) and
[academic report](docs/archive/DASE_Report.pdf) are retained for reference.
Development work is on `mac-development`; `main` preserves the academic version.
