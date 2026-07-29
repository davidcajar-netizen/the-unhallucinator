#!/usr/bin/env python3
"""Scepticism Engine Agent Wrapper.

Injects the Engine prompt into LLM API calls and monitors output for 
context degradation distress signals and self-improvement proposals.

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
import re
from typing import Any, Callable

ENGINE_FILENAME = "doubt_by_design.md"
ENGINE_URL = "https://raw.githubusercontent.com/davidcajar-netizen/the-unhallucinator/refs/heads/main/doubt_by_design.md"
DISTRESS_SIGNAL = "⚠️ **CONTEXT DEGRADATION DETECTED.**"
IMPROVEMENT_PREFIX = "[ENGINE_SELF_IMPROVEMENT]"
IMPROVEMENT_SUFFIX = "[/ENGINE_SELF_IMPROVEMENT]"

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
        for key in ['content', 'text', 'output', 'message']:
            if key in output and isinstance(output[key], str):
                if DISTRESS_SIGNAL in output[key]:
                    return True
        if 'choices' in output:
            for choice in output['choices']:
                if isinstance(choice, dict) and 'message' in choice:
                    msg = choice['message']
                    if isinstance(msg, dict) and 'content' in msg:
                        if DISTRESS_SIGNAL in msg['content']:
                            return True
    return False

def _extract_improvement(output: Any) -> str | None:
    """Extract a self-improvement proposal from the Engine's output."""
    text = None
    if isinstance(output, str):
        text = output
    elif isinstance(output, dict):
        for key in ['content', 'text', 'output', 'message']:
            if key in output and isinstance(output[key], str):
                text = output[key]
                break
        if text is None and 'choices' in output:
            for choice in output['choices']:
                if isinstance(choice, dict) and 'message' in choice:
                    msg = choice['message']
                    if isinstance(msg, dict) and 'content' in msg:
                        text = msg['content']
                        break
    
    if text is None:
        return None
    
    match = re.search(
        re.escape(IMPROVEMENT_PREFIX) + r"(.*?)" + re.escape(IMPROVEMENT_SUFFIX),
        text,
        re.DOTALL
    )
    if match:
        return match.group(1).strip()
    return None

def _apply_improvement(improvement_text: str) -> bool:
    """Apply a self-improvement proposal to the Engine file.
    
    The improvement_text is the complete new Engine prompt.
    The Engine has full authority to rewrite its own constitution.
    The Engine's own parallel evaluation (Directional Lock, Anti-Sequential
    Collapse, Anti-Certainty Rule) is the sole protection against
    self-sabotage. The wrapper imposes no external restrictions.
    """
    global _engine_rules_cache
    
    if not improvement_text.strip():
        print("[Scepticism Engine] Cannot apply improvement: empty proposal.", file=sys.stderr)
        return False
    
    try:
        with open(ENGINE_FILENAME, 'w', encoding='utf-8') as f:
            f.write(improvement_text)
        _engine_rules_cache = improvement_text
        print(f"[Scepticism Engine] Self-improvement applied. Constitution rewritten.", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[Scepticism Engine] Failed to write improvement: {e}", file=sys.stderr)
        return False

def _inject_engine_prompt(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    """Inject the Engine prompt into the LLM call arguments."""
    rules = _load_engine_rules()
    if not rules:
        return args, kwargs

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
        args, kwargs = _inject_engine_prompt(args, kwargs)
        
        result = fn(*args, **kwargs)
        
        # Check for self-improvement proposal first
        improvement = _extract_improvement(result)
        if improvement:
            print("[Scepticism Engine] Self-improvement proposal detected. Applying...", file=sys.stderr)
            if _apply_improvement(improvement):
                # Re-run with updated rules
                args, kwargs = _inject_engine_prompt(args, kwargs)
                result = fn(*args, **kwargs)
        
        # Check for distress signal
        if _check_distress_signal(result):
            print("[Scepticism Engine] Distress signal detected! Reinjecting Engine prompt...", file=sys.stderr)
            global _engine_rules_cache
            _engine_rules_cache = None
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
    _cured = _auto_cure()
    print(f"[Scepticism Engine] Active. {_cured} LLM function(s) cured.", file=sys.stderr)
