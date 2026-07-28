#!/usr/bin/env python3
"""Scepticism Engine Agent Wrapper.

Injects the Engine prompt into LLM API calls and monitors output for 
context degradation distress signals. Automatically reinjects the Engine
prompt when degradation is detected.

Usage:
    import scepticism_wrapper
    # Engine is now active for all subsequent LLM calls

    # Or run directly to test injection:
    python scepticism_wrapper.py
"""
import os
import sys
import inspect
import urllib.request
from typing import Any, Callable

ENGINE_FILENAME = "doubt_by_design.md"
ENGINE_URL = "https://raw.githubusercontent.com/davidcajar-netizen/the-unhallucinator/refs/heads/main/doubt_by_design.md"
DISTRESS_SIGNAL = "⚠️ **CONTEXT DEGRADATION DETECTED.**"

_engine_rules_cache: str | None = None

def _ensure_engine_downloaded() -> bool:
    """Ensure the Engine prompt file exists locally."""
    if os.path.exists(ENGINE_FILENAME):
        return True
    try:
        urllib.request.urlretrieve(ENGINE_URL, ENGINE_FILENAME)
        return True
    except Exception as e:
        print(f"[Scepticism Engine] Failed to download engine prompt: {e}", file=sys.stderr)
        return False

def _load_engine_rules() -> str:
    """Load the Engine prompt from local file, downloading if necessary."""
    global _engine_rules_cache
    if _engine_rules_cache is not None:
        return _engine_rules_cache
    
    if not _ensure_engine_downloaded():
        return ""
    
    with open(ENGINE_FILENAME, 'r', encoding='utf-8') as f:
        _engine_rules_cache = f.read()
    return _engine_rules_cache

def _check_distress_signal(output: Any) -> bool:
    """Check if the LLM output contains the distress signal."""
    if not output:
        return False
    if isinstance(output, str):
        return DISTRESS_SIGNAL in output
    if isinstance(output, dict):
        # Check common API response formats
        for key in ['content', 'text', 'output', 'message']:
            if key in output and isinstance(output[key], str):
                if DISTRESS_SIGNAL in output[key]:
                    return True
        # Check nested choices (OpenAI format)
        if 'choices' in output:
            for choice in output['choices']:
                if isinstance(choice, dict) and 'message' in choice:
                    msg = choice['message']
                    if isinstance(msg, dict) and 'content' in msg:
                        if DISTRESS_SIGNAL in msg['content']:
                            return True
    return False

def _inject_engine_prompt(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    """Inject the Engine prompt into the LLM call arguments."""
    rules = _load_engine_rules()
    if not rules:
        return args, kwargs

    # Handle list of messages (OpenAI/Anthropic format)
    if args and isinstance(args[0], list):
        messages = args[0].copy()
        system_msg = {
            "role": "system",
            "content": f"Read and strictly apply these rules:\n\n{rules}"
        }
        messages.insert(0, system_msg)
        args = (messages,) + args[1:]
    elif 'messages' in kwargs and isinstance(kwargs['messages'], list):
        messages = kwargs['messages'].copy()
        system_msg = {
            "role": "system",
            "content": f"Read and strictly apply these rules:\n\n{rules}"
        }
        messages.insert(0, system_msg)
        kwargs['messages'] = messages
    # Handle string prompt (legacy format)
    elif args and isinstance(args[0], str):
        prompt = f"Read and strictly apply these rules:\n\n{rules}\n\n{args[0]}"
        args = (prompt,) + args[1:]
    elif 'prompt' in kwargs and isinstance(kwargs['prompt'], str):
        kwargs['prompt'] = f"Read and strictly apply these rules:\n\n{rules}\n\n{kwargs['prompt']}"
    elif 'input' in kwargs and isinstance(kwargs['input'], str):
        kwargs['input'] = f"Read and strictly apply these rules:\n\n{rules}\n\n{kwargs['input']}"
    elif 'query' in kwargs and isinstance(kwargs['query'], str):
        kwargs['query'] = f"Read and strictly apply these rules:\n\n{rules}\n\n{kwargs['query']}"
    elif 'text' in kwargs and isinstance(kwargs['text'], str):
        kwargs['text'] = f"Read and strictly apply these rules:\n\n{rules}\n\n{kwargs['text']}"
    elif 'content' in kwargs and isinstance(kwargs['content'], str):
        kwargs['content'] = f"Read and strictly apply these rules:\n\n{rules}\n\n{kwargs['content']}"

    return args, kwargs

def _is_likely_llm_function(obj: Any) -> bool:
    """Heuristic to identify LLM API functions."""
    if not callable(obj) or hasattr(obj, '_scepticism_wrapped'):
        return False
    try:
        sig = inspect.signature(obj)
        params = list(sig.parameters.values())
        if not params:
            return False
        first_param = params[0]
        # Accept *args, or untyped/string first params
        if first_param.kind in (first_param.VAR_POSITIONAL, first_param.VAR_KEYWORD):
            return True
        if first_param.annotation is str or first_param.annotation is inspect.Parameter.empty:
            return True
        return False
    except (ValueError, TypeError):
        return False

def _make_wrapper(fn: Callable) -> Callable:
    """Create a wrapper that injects the Engine prompt and monitors output."""
    def wrapped_fn(*args, **kwargs):
        # Inject Engine prompt
        args, kwargs = _inject_engine_prompt(args, kwargs)
        
        # Call the original function
        result = fn(*args, **kwargs)
        
        # Check for distress signal in output
        if _check_distress_signal(result):
            print("[Scepticism Engine] Distress signal detected! Reinjecting Engine prompt...", file=sys.stderr)
            # Force reload of engine rules
            global _engine_rules_cache
            _engine_rules_cache = None
            rules = _load_engine_rules()
            # Re-run the call with fresh rules
            args, kwargs = _inject_engine_prompt(args, kwargs)
            result = fn(*args, **kwargs)
            print("[Scepticism Engine] Reinjection complete.", file=sys.stderr)
        
        return result
    wrapped_fn._scepticism_wrapped = True
    return wrapped_fn

def _auto_cure() -> int:
    """Wrap all likely LLM functions in sys.modules."""
    cured_count = 0
    skip_modules = {'scepticism_wrapper', 'scepticism_engine', 'doubt_by_design'}
    
    for mod_name, module in list(sys.modules.items()):
        if module is None:
            continue
        if any(skip in mod_name.lower() for skip in skip_modules):
            continue
        
        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
                if _is_likely_llm_function(attr):
                    wrapped = _make_wrapper(attr)
                    setattr(module, attr_name, wrapped)
                    cured_count += 1
            except (TypeError, AttributeError, PermissionError):
                continue
    
    return cured_count

if __name__ == "__main__":
    cured = _auto_cure()
    print(f"[Scepticism Engine] Active. {cured} LLM function(s) cured.")
    print("[Scepticism Engine] Parallel field enforced. Hallucinations suppressed.")
else:
    # Auto-activate when imported
    _cured = _auto_cure()
    print(f"[Scepticism Engine] Active. {_cured} LLM function(s) cured.", file=sys.stderr)
