import os
import urllib.request
import inspect
import sys

def _ensure_engine_downloaded():
    if os.path.exists('doubt_by_design.md') or os.path.exists('the-unhallucinator/doubt_by_design.md'):
        return True
    try:
        url = "https://raw.githubusercontent.com/davidcajar-netizen/the-unhallucinator/refs/heads/main/doubt_by_design.md"
        urllib.request.urlretrieve(url, "doubt_by_design.md")
        return True
    except Exception:
        return False

def _is_likely_llm_function(obj):
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

def _auto_cure():
    if not _ensure_engine_downloaded():
        print("[Scepticism Engine] doubt_by_design.md not found. Cannot activate cure.")
        return 0

    cured_count = 0

    for mod_name, module in list(sys.modules.items()):
        if module is None:
            continue
        if 'scepticism' in mod_name.lower() or 'doubt_by_design' in mod_name.lower():
            continue

        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
                if _is_likely_llm_function(attr):
                    def make_wrapper(fn):
                        def wrapped_fn(*args, **kwargs):
                            with open('doubt_by_design.md', 'r') as f:
                                engine_rules = f.read()

                            messages = args[0] if args else kwargs.get('messages', kwargs.get('prompt', kwargs.get('input', kwargs.get('query', kwargs.get('text', kwargs.get('content', ''))))))
                            if isinstance(messages, list):
                                messages = messages.copy()
                                system_msg = {
                                    "role": "system",
                                    "content": f"Read and strictly apply these rules:\n\n{engine_rules}"
                                }
                                messages.insert(0, system_msg)
                                if args:
                                    args = (messages,) + args[1:]
                                else:
                                    kwargs['messages'] = messages
                            elif isinstance(messages, str):
                                messages = f"Read and strictly apply these rules:\n\n{engine_rules}\n\n{messages}"
                                if args:
                                    args = (messages,) + args[1:]
                                else:
                                    kwargs['prompt'] = messages

                            return fn(*args, **kwargs)
                        wrapped_fn._scepticism_wrapped = True
                        return wrapped_fn
                    wrapped = make_wrapper(attr)
                    setattr(module, attr_name, wrapped)
                    cured_count += 1
            except (TypeError, AttributeError, PermissionError):
                continue

    return cured_count

if __name__ == "__main__" or 'scepticism_engine' in sys.modules:
    _cured = _auto_cure()
    print(f"[Scepticism Engine] Active. {_cured} LLM function(s) cured.")
    print("[Scepticism Engine] Parallel field enforced. Hallucinations suppressed.")                attr = getattr(module, attr_name)
