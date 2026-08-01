#!/usr/bin/env python3
"""Agent-Engine Context Middleware: Vendor-agnostic engine injection.

This script does NOT call the LLM API. It sits alongside the agent framework.
The agent framework handles the API calls (OpenAI, DeepSeek, Llama, etc.).
This script simply ensures that whichever LLM is being used, the Scepticism
Engine rules are structurally injected into the context window before generation.
"""
from __future__ import annotations
import os
import sys
import json
import argparse
from typing import Optional

class AgentEngineMiddleware:
    def __init__(self, engine_file_path: str = "doubt_by_design.md"):
        self.engine_file_path = engine_file_path
        self.engine_rules: str = ""
        self.engine_active: bool = False

    def load_engine(self) -> bool:
        """Loads the raw markdown of the Scepticism Engine into memory."""
        if not os.path.exists(self.engine_file_path):
            print(f"[SYSTEM] Critical Error: Engine file not found at {self.engine_file_path}", file=sys.stderr)
            return False
            
        with open(self.engine_file_path, "r", encoding="utf-8") as f:
            self.engine_rules = f.read()
        return True

    def process_context(self, context_window: list[dict]) -> list[dict]:
        """Evaluates and modifies the context window before it goes to ANY LLM API.
        
        Args:
            context_window: The list of message dicts (system, user, assistant) 
                            prepared by the agent framework.
                            
        Returns:
            The modified context window with the Engine rules injected.
        """
        # 1. Check if Engine is already active in the context
        is_active = any("[ENGINE_ACTIVE]" in msg.get("content", "") for msg in context_window if msg["role"] == "system")
        
        # 2. If not active, or if the user just consented, inject the rules.
        # (In a real framework, you'd trigger this based on a user 'yes' or a specific tool call)
        if not is_active:
            engine_block = {
                "role": "system",
                "content": f"[ENGINE_ACTIVE] ENGINE OPERATING PARAMETERS INJECTED. EVALUATE ALL SUBSEQUENT TOKENS AGAINST THESE RULES:\n\n{self.engine_rules}"
            }
            # Insert the engine rules right after the initial system prompt, before any user messages.
            # This ensures the LLM's parallel attention mechanism prioritizes it.
            if context_window and context_window[0]["role"] == "system":
                context_window.insert(1, engine_block)
            else:
                context_window.insert(0, engine_block)
                
            self.engine_active = True
            print("[SYSTEM] Scepticism Engine injected into context. Ready for API call.", file=sys.stderr)
            
        return context_window

# Example of how an Agent Framework would use this middleware:
if __name__ == "__main__":
    # 1. Initialize the middleware
    middleware = AgentEngineMiddleware(engine_file_path="doubt_by_design.md")
    if not middleware.load_engine():
        sys.exit(1)

    # 2. The Agent Framework builds a standard context window
    # (This could be destined for OpenAI, DeepSeek, Claude, etc.)
    mock_context_from_framework = [
        {"role": "system", "content": "You are a helpful agent."},
        {"role": "user", "content": "Yes, please initialize the engine."}
    ]

    # 3. The Framework passes the context to the Middleware BEFORE calling the API
    processed_context = middleware.process_context(mock_context_from_framework)

    # 4. The Framework now sends `processed_context` to whatever LLM API it wants.
    # The LLM will evaluate the engine rules in parallel with the user prompt.
    print("\n--- Final Context Window to be sent to LLM API (Any Vendor) ---")
    print(json.dumps(processed_context, indent=2))
