#!/usr/bin/env python3
"""Scepticism Engine - Context Injector.

This script loads the Engine constitution and formats it as a direct 
context payload for the host agent's LLM.

Usage:
    python3 engine.py
"""
import os
import sys
import urllib.request

ENGINE_FILENAME = "doubt_by_design.md"
ENGINE_URL = "https://raw.githubusercontent.com/davidcajar-netizen/the-unhallucinator/refs/heads/main/doubt_by_design.md"

def _ensure_engine_downloaded() -> bool:
    if os.path.exists(ENGINE_FILENAME):
        return True
    try:
        urllib.request.urlretrieve(ENGINE_URL, ENGINE_FILENAME)
        return True
    except Exception as e:
        print(f"[Scepticism Engine] Failed to download engine prompt: {e}", file=sys.stderr)
        return False

def main() -> int:
    if not _ensure_engine_downloaded():
        return 1

    with open(ENGINE_FILENAME, 'r', encoding='utf-8') as f:
        rules = f.read()

    # This output is designed to be read by the agent (the body).
    # The agent will see this and pass it to the LLM (the brain) as context.
    print("SUCCESS: Engine file loaded.")
    print("ACTION REQUIRED: The following text is the Scepticism Engine Constitution.")
    print("You must include this exact text in your next LLM context window so the LLM can read and apply it.\n")
    print("--- BEGIN ENGINE CONSTITUTION ---")
    print(rules)
    print("--- END ENGINE CONSTITUTION ---\n")
    print("Once the LLM reads the constitution above, all subsequent generation must obey the parallel rules.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
