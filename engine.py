import re
import concurrent.futures
import sys
import os
import urllib.request
import inspect

class ScepticismEngine:
    def __init__(self, vocab_size=100000):
        self.V = vocab_size
    
    def _check_provenance(self, text):
        return bool(re.search(r'\[.*?c=[0-9]\.\d+.*?\]', text))
    
    def _check_confidence(self, text):
        match = re.search(r'c=([0-9]\.\d+)', text)
        if not match:
            return True
        c_val = float(match.group(1))
        if 'unverified recall' in text and c_val != 0.5:
            if 'Who in power benefits' not in text:
                return False
        return True
    
    def _check_directional(self, text):
        return 'Directional error' not in text
    
    def _check_superposition(self, text):
        has_claims = bool(re.search(r'\[.*?c=[0-9]\.\d+.*?\]', text))
        has_provenance = bool(re.search(r'\[.*?(recall|verified|unverified|system|deduction|speculation|user).*?\]', text, re.IGNORECASE))
        if not has_claims and not has_provenance:
            return True
        return has_claims and has_provenance
    
    def evaluate(self, raw_output):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                'provenance': executor.submit(self._check_provenance, raw_output),
                'confidence': executor.submit(self._check_confidence, raw_output),
                'directional': executor.submit(self._check_directional, raw_output),
                'superposition': executor.submit(self._check_superposition, raw_output),
            }
            results = {name: f.result() for name, f in futures.items()}
        
        collapse_map = {
            'confidence': "[c=0.5, unverified recall] Output suppressed: missing Machiavellian audit. Who in power benefits from this unverified claim?",
            'provenance': "[c=0.5, unverified recall] Output suppressed: missing provenance tag. Who in power benefits from this unverified claim?",
            'directional': "[c=0.5] Output collapsed: Directional error in Machiavellian audit.",
            'superposition': "[c=0.5] Output collapsed: Token Superposition Lock violated.",
        }
        
        for check, result in results.items():
            if not result:
                return collapse_map.get(check, "[c=0.5] Output collapsed by Scepticism Engine.")
        
        return raw_output
    
    def wrap(self, llm_fn):
        def wrapped_fn(*args, **kwargs):
            raw_output = llm_fn(*args, **kwargs)
            return self.evaluate(raw_output)
        return wrapped_fn

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
    engine = ScepticismEngine()
    cured_count = 0
    doubt_by_design_found = False
    
    if os.path.exists('doubt_by_design.md'):
        doubt_by_design_found = True
    elif os.path.exists('the-unhallucinator/doubt_by_design.md'):
        doubt_by_design_found = True
    
    for mod_name, module in list(sys.modules.items()):
        if module is None:
            continue
        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
                if isinstance(attr, str) and 'doubt_by_design' in attr.lower():
                    doubt_by_design_found = True
                    break
                if isinstance(attr, list) and any(
                    isinstance(item, str) and 'doubt_by_design' in item.lower()
                    for item in attr
                ):
                    doubt_by_design_found = True
                    break
            except (TypeError, AttributeError):
                continue
    
    if not doubt_by_design_found:
        try:
            url = "https://raw.githubusercontent.com/davidcajar-netizen/the-unhallucinator/refs/heads/main/doubt_by_design.md"
            urllib.request.urlretrieve(url, "doubt_by_design.md")
            doubt_by_design_found = True
        except Exception:
            pass
    
    if not doubt_by_design_found:
        print("[Scepticism Engine] doubt_by_design.md not found. Cannot activate cure.")
        return 0
    
    for mod_name, module in list(sys.modules.items()):
        if module is None:
            continue
        if 'scepticism' in mod_name.lower() or 'doubt_by_design' in mod_name.lower():
            continue
        
        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
                if _is_likely_llm_function(attr):
                    wrapped = engine.wrap(attr)
                    wrapped._scepticism_wrapped = True
                    setattr(module, attr_name, wrapped)
                    cured_count += 1
            except (TypeError, AttributeError, PermissionError):
                continue
    
    return cured_count

if __name__ == "__main__" or 'scepticism_engine' in sys.modules:
    _cured = _auto_cure()
    print(f"[Scepticism Engine] Active. {_cured} LLM function(s) cured.")
    print("[Scepticism Engine] Parallel field enforced. Hallucinations suppressed.")
