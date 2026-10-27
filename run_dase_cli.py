"""Press Run Python File to test DASE with local MLX in the terminal, without a GUI."""
import argparse
from contextlib import nullcontext
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
import traceback

from run_dase import ROOT, local_server


def report_error(error, debug=False):
    print(f"\nInference failed: {error}", file=sys.stderr)
    print("The failed turn was not added to the exercise. Use /retry or enter another action.",
          file=sys.stderr)
    if debug:
        traceback.print_exception(type(error), error, error.__traceback__)
        cause = error.__cause__
        response = getattr(cause, "response", None)
        if response is not None:
            print(f"Local server response (up to 2000 characters):\n{response.text[:2000]}",
                  file=sys.stderr)


def chat(session, debug=False):
    from dase import utils

    failed_input = None
    saved_turns = 0
    print("\nEnter an attack type to begin, then enter defender actions.")
    print("Commands: /retry, /save, /quit, /help. Ctrl+C also exits.")
    try:
        while True:
            try:
                user_input = input("\nYou> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user_input:
                continue
            if user_input.lower() in {"/quit", "/exit"}:
                break
            if user_input.lower() == "/help":
                print("/retry repeats the last failed action; /save exports JSON; /quit exits.")
                continue
            if user_input.lower() == "/save":
                try:
                    print(f"Saved: {utils.save_session(session.log)}")
                    saved_turns = len(session.log.turns)
                except OSError as exc:
                    print(f"Could not save: {exc}", file=sys.stderr)
                continue
            if user_input.lower() == "/retry":
                if failed_input is None:
                    print("No failed action to retry.")
                    continue
                user_input = failed_input
            elif user_input.startswith("/"):
                print("Unknown command. Type /help for commands.")
                continue
            print("DASE is generating... (first inference may download/load the model)", flush=True)
            try:
                response = session.send(user_input)
            except Exception as exc:
                failed_input = user_input
                report_error(exc, debug)
                continue
            failed_input = None
            print(f"\nDASE> {response}")
            metrics = session.log.turns[-1].raw_chunks
            if metrics:
                print(f"[Elapsed: {metrics[0].get('elapsed_seconds', '?')}s; "
                      f"usage: {metrics[0].get('usage', {})}]")
    finally:
        # Preserve completed turns even when Ctrl+C interrupts an inference request.
        if len(session.log.turns) > saved_turns:
            try:
                print(f"Session saved: {utils.save_session(session.log)}")
            except OSError as exc:
                print(f"Could not save session: {exc}", file=sys.stderr)


def parse_args(argv=None):
    from dase import utils

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", choices=list(utils.COMPANY_MAP), default="Well Connect")
    parser.add_argument("--difficulty", choices=["low", "medium", "high"], default="low")
    parser.add_argument("--reactions", type=int, choices=range(1, 11), default=3)
    parser.add_argument("--model", help="Override MLX_MODEL for this run")
    parser.add_argument("--timeout", type=float, help="Override MLX_TIMEOUT in seconds")
    parser.add_argument("--max-tokens", type=int, help="Override MLX_MAX_TOKENS")
    parser.add_argument("--max-history-chars", type=int,
                        help="Override MLX_MAX_HISTORY_CHARS (characters, not tokens)")
    parser.add_argument("--connect-only", action="store_true",
                        help="Connect to your existing server without starting or stopping one")
    parser.add_argument("--debug", action="store_true",
                        help="Print full Python tracebacks and local HTTP error response bodies")
    return parser.parse_args(argv)


def main():
    venv = ROOT / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    try:
        if python.is_file() and Path(sys.prefix).resolve() != venv.resolve():
            return subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
                                   cwd=ROOT)
        from dotenv import load_dotenv
        from dase.paths import ENV_PATH
        from dase.providers.mlx import MLXConfig, MLXProvider
        from dase.simulation import SimulationSession
        from dase import utils

        load_dotenv(ENV_PATH)
        args = parse_args()
        config = MLXConfig.from_env(args.model)
        if args.timeout is not None:
            config = replace(config, timeout=args.timeout)
        if args.max_tokens is not None:
            config = replace(config, max_tokens=args.max_tokens)
        if args.max_history_chars is not None:
            config = replace(config, max_history_chars=args.max_history_chars)
        profile = Path(utils.COMPANY_MAP[args.company]).read_text(encoding="utf-8")
        session = SimulationSession("Apple MLX (local)", profile, args.company,
                                    args.difficulty, args.reactions,
                                    local_provider=MLXProvider(config))
        print(f"DASE CLI | {args.company} | {args.difficulty} | {args.reactions} reactions")
        print(f"Model: {config.model}\nEndpoint: {config.base_url}")
        print(f"Timeout: {config.timeout}s | Output limit: {config.max_tokens} tokens | "
              f"Initial context: {len(session.context)}/{config.max_history_chars} characters")
        if len(session.context) >= config.max_history_chars:
            print("The initial context already exceeds the history guard. No model request can "
                  "succeed with this limit. Restart with --max-history-chars 64000 (or another "
                  "deliberate limit), or shorten data/prompts/prompt.txt.", file=sys.stderr)
            return 1
        if not args.debug:
            print("Tip: run with --debug for full error details.")
        with nullcontext() if args.connect_only else local_server(config):
            chat(session, args.debug)
        return 0
    except KeyboardInterrupt:
        print("\nDASE CLI stopped.")
        return 130
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Could not run DASE CLI: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
