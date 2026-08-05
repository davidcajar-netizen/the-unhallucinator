"""Shared gate logic for the Scepticism Engine enforcement layer.

Executable gate (hooks, CLI) — not markdown aspiration. Tracks collapse state,
runs parallel pre-evaluation, and scores agent output against epistemic rules.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_STATE_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-state.json")
DEFAULT_AUDIT_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-audit.jsonl")
ENGINE_PATH = os.path.join(REPO_ROOT, "engine.py")
MEMORY_PATH = os.path.join(REPO_ROOT, "scripts", "memory.py")

# User can unlock observer bypass for audited sessions only.
BYPASS_TOKEN = "GATE_BYPASS_AUDITED"

DEFAULT_CERTAINTY = 0.5
TRIANGULATION_MIN = 3
CERTAINTY_EPSILON = 0.06

# Lexicon subsets of V — set membership, parallel evaluated
H_c = frozenset(
    {
        "definitely", "certainly", "always", "never", "proven", "undeniably",
        "undoubted", "100",
    }
)
U_h = frozenset(
    {
        "may", "might", "could", "possibly", "perhaps", "uncertain", "unverified",
        "unknown", "unsure",
    }
)
S_t = frozenset({"stop", "correct", "followup", "abstain", "retry"})
_CODE_FENCE_RE = re.compile(r"```[\w]*.*?```", re.DOTALL)
_GATE_PASS_RE = re.compile(r"\bGATE_PASS\b")
_MEMORY_RETRIEVE_RE = re.compile(r"memory\.py\s+retrieve", re.I)
_WEB_FETCH_RE = re.compile(
    r"\b(curl|wget|WebFetch|web_search|WebSearch|fetch\s+https?://)", re.I
)
_WORD_TOKEN_RE = re.compile(r"[a-z0-9]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MemoryRetrieveState:
    query: str = ""
    timestamp: str = ""
    exit_code: int = 3
    match_count: int = 0
    max_certainty: float = DEFAULT_CERTAINTY
    max_epistemic: float = DEFAULT_CERTAINTY


@dataclass
class TriangulationState:
    sources: list[str] = field(default_factory=list)
    count: int = 0
    verified: bool = False
    max_certainty_spread: float = 1.0


@dataclass
class GateState:
    version: int = 2
    L_n: int = 1  # parallel layered analysis always on (hardened)
    T_g_bypass_unlocked: bool = False
    parallel_gate_passed: bool = False
    last_prompt: str = ""
    last_memory: MemoryRetrieveState = field(default_factory=MemoryRetrieveState)
    triangulation: TriangulationState = field(default_factory=TriangulationState)
    last_verification: dict[str, Any] = field(default_factory=dict)
    epistemic_reflect: list[str] = field(default_factory=list)
    inference_seeds: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "L_n": self.L_n,
            "T_g_bypass_unlocked": self.T_g_bypass_unlocked,
            "parallel_gate_passed": self.parallel_gate_passed,
            "last_prompt": self.last_prompt,
            "last_memory": asdict(self.last_memory),
            "triangulation": asdict(self.triangulation),
            "last_verification": self.last_verification,
            "epistemic_reflect": self.epistemic_reflect,
            "inference_seeds": self.inference_seeds,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GateState:
        lm = data.get("last_memory") or {}
        tr = data.get("triangulation") or {}
        return cls(
            version=int(data.get("version", 2)),
            L_n=int(data.get("L_n", 1)),
            T_g_bypass_unlocked=bool(data.get("T_g_bypass_unlocked", False)),
            parallel_gate_passed=bool(data.get("parallel_gate_passed", False)),
            last_prompt=str(data.get("last_prompt", "")),
            last_memory=MemoryRetrieveState(
                query=str(lm.get("query", "")),
                timestamp=str(lm.get("timestamp", "")),
                exit_code=int(lm.get("exit_code", 3)),
                match_count=int(lm.get("match_count", 0)),
                max_certainty=float(lm.get("max_certainty", DEFAULT_CERTAINTY)),
                max_epistemic=float(lm.get("max_epistemic", DEFAULT_CERTAINTY)),
            ),
            triangulation=TriangulationState(
                sources=list(tr.get("sources", [])),
                count=int(tr.get("count", 0)),
                verified=bool(tr.get("verified", False)),
                max_certainty_spread=float(tr.get("max_certainty_spread", 1.0)),
            ),
            last_verification=dict(data.get("last_verification", {})),
            epistemic_reflect=list(data.get("epistemic_reflect", [])),
            inference_seeds=list(data.get("inference_seeds", [])),
            updated_at=str(data.get("updated_at", utc_now())),
        )


@dataclass
class ReflectionResult:
    """Epistemic reflection after collapse — feeds next inference, does not stop."""

    certainty_score: float
    epistemic_notes: list[str]
    inference_seeds: list[str]
    collapse_markers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "certainty_score": self.certainty_score,
            "epistemic_notes": self.epistemic_notes,
            "inference_seeds": self.inference_seeds,
            "collapse_markers": self.collapse_markers,
        }


@dataclass
class VerificationResult:
    """Legacy alias shape for CLI; maps from ReflectionResult."""

    passed: bool
    certainty_score: float
    violations: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "certainty_score": self.certainty_score,
            "violations": self.violations,
            "warnings": self.warnings,
        }


def load_state(path: str = DEFAULT_STATE_PATH) -> GateState:
    if not os.path.isfile(path):
        return GateState()
    with open(path, "r", encoding="utf-8") as fh:
        return GateState.from_dict(json.load(fh))


def save_state(state: GateState, path: str = DEFAULT_STATE_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    state.updated_at = utc_now()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state.to_dict(), fh, indent=2)


def audit_log(event: str, payload: dict[str, Any], path: str = DEFAULT_AUDIT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {"timestamp": utc_now(), "event": event, **payload}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def extract_query(prompt: str, max_len: int = 240) -> str:
    text = (prompt or "").strip()
    if not text:
        return ""
    if _GATE_PASS_RE.search(text):
        text = _GATE_PASS_RE.sub("", text).strip()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            text = line
            break
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text


def prompt_requests_bypass(prompt: str) -> bool:
    return BYPASS_TOKEN in (prompt or "")


def effective_certainty(state: GateState) -> float:
    mem_cert = state.last_memory.max_epistemic
    if state.triangulation.verified and state.triangulation.count >= TRIANGULATION_MIN:
        return min(0.99, max(mem_cert, 0.75))
    if state.last_memory.exit_code == 0 and state.last_memory.match_count > 0:
        return mem_cert
    return DEFAULT_CERTAINTY


def triangulation_ok(state: GateState) -> bool:
    tr = state.triangulation
    return tr.count >= TRIANGULATION_MIN and tr.verified


def subagents_allowed(state: GateState) -> bool:
    if state.T_g_bypass_unlocked:
        return True
    return state.parallel_gate_passed or triangulation_ok(state)


def _run_cmd(cmd: list[str], cwd: str = REPO_ROOT, timeout: int = 45) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_memory_retrieve(query: str, timeout: int = 40) -> tuple[int, dict[str, Any]]:
    if not query:
        return 3, {"results": [], "count": 0}
    cmd = [
        "python3",
        MEMORY_PATH,
        "retrieve",
        query,
        "--json",
        "--limit",
        "5",
    ]
    proc = _run_cmd(cmd, timeout=timeout)
    if proc.returncode not in (0, 3):
        return 3, {"results": [], "count": 0, "error": proc.stderr.strip()}
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {"results": [], "count": 0}
    except json.JSONDecodeError:
        return 3, {"results": [], "count": 0, "error": "invalid json from memory.py"}
    return proc.returncode, data


def run_parallel_gate(query: str, timeout: int = 50) -> dict[str, Any]:
    """Run memory retrieval and metadata probes in parallel via engine.py."""
    tasks = [
        {
            "task_id": "memory",
            "command": " ".join(
                ["python3", "scripts/memory.py", "retrieve", shlex.quote(query), "--json", "--limit", "5"]
            ),
        },
        {
            "task_id": "memory_list",
            "command": "python3 scripts/memory.py list",
        },
        {
            "task_id": "gate_ping",
            "command": "python3 scripts/gate.py state --json",
        },
    ]
    tasks_json = json.dumps(tasks)
    proc = _run_cmd(
        ["python3", ENGINE_PATH, "--tasks", tasks_json],
        timeout=timeout,
    )
    if proc.returncode != 0 and not proc.stdout.strip():
        # Fallback: sequential memory only
        code, data = run_memory_retrieve(query, timeout=timeout)
        return {
            "fallback": True,
            "memory_exit_code": code,
            "memory": data,
            "parallel_results": [],
        }

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError:
        code, data = run_memory_retrieve(query, timeout=timeout)
        return {
            "fallback": True,
            "memory_exit_code": code,
            "memory": data,
            "parallel_results": [],
            "error": "engine json parse failed",
        }

    memory_payload: dict[str, Any] = {"results": [], "count": 0}
    memory_exit = 3
    for item in envelope.get("results", []):
        if item.get("task_id") == "memory" and item.get("success"):
            try:
                memory_payload = json.loads(item.get("stdout") or "{}")
                memory_exit = 0 if memory_payload.get("count", 0) > 0 else 3
            except json.JSONDecodeError:
                memory_exit = 3
        elif item.get("task_id") == "memory" and not item.get("success"):
            stderr = (item.get("stderr") or "").lower()
            memory_exit = 3 if "no local match" in stderr or not item.get("stdout") else 3

    if memory_exit == 3 and envelope.get("results"):
        for item in envelope.get("results", []):
            if item.get("task_id") == "memory":
                stdout = (item.get("stdout") or "").strip()
                if stdout:
                    try:
                        memory_payload = json.loads(stdout)
                        memory_exit = 0 if memory_payload.get("count", 0) > 0 else 3
                    except json.JSONDecodeError:
                        pass

    return {
        "parallel_results": envelope.get("results", []),
        "memory_exit_code": memory_exit,
        "memory": memory_payload,
    }


def parse_memory_from_envelope(envelope: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Extract memory retrieve payload from engine.py parallel envelope."""
    memory_payload: dict[str, Any] = {"results": [], "count": 0}
    memory_exit = 3
    for item in envelope.get("results", []):
        if item.get("task_id") != "memory":
            continue
        stdout = (item.get("stdout") or "").strip()
        if stdout:
            try:
                memory_payload = json.loads(stdout)
                memory_exit = 0 if memory_payload.get("count", 0) > 0 else 3
            except json.JSONDecodeError:
                memory_exit = 3
        elif not item.get("success"):
            memory_exit = 3
    return memory_exit, memory_payload


def apply_memory_to_state(state: GateState, query: str, exit_code: int, mem: dict[str, Any]) -> GateState:
    results = mem.get("results", []) or []
    max_stored = DEFAULT_CERTAINTY
    max_epistemic = DEFAULT_CERTAINTY
    for row in results:
        max_stored = max(max_stored, float(row.get("stored_certainty", DEFAULT_CERTAINTY)))
        max_epistemic = max(max_epistemic, float(row.get("epistemic_certainty", DEFAULT_CERTAINTY)))

    state.last_memory = MemoryRetrieveState(
        query=query,
        timestamp=utc_now(),
        exit_code=exit_code,
        match_count=len(results),
        max_certainty=max_stored,
        max_epistemic=max_epistemic,
    )
    state.parallel_gate_passed = state.L_n == 1 and bool(query)
    if state.T_g_bypass_unlocked:
        state.parallel_gate_passed = True
    return state


def apply_parallel_from_envelope(state: GateState, prompt: str, envelope: dict[str, Any]) -> GateState:
    query = extract_query(prompt)
    state.last_prompt = prompt
    state.T_g_bypass_unlocked = prompt_requests_bypass(prompt)

    if not query:
        state.parallel_gate_passed = False
        state.last_memory = MemoryRetrieveState(
            query="",
            timestamp=utc_now(),
            exit_code=3,
            match_count=0,
            max_certainty=DEFAULT_CERTAINTY,
            max_epistemic=DEFAULT_CERTAINTY,
        )
        return state

    exit_code, mem = parse_memory_from_envelope(envelope)
    return apply_memory_to_state(state, query, exit_code, mem)


def apply_parallel_eval_result(
    state: GateState,
    prompt: str,
    prior: Any,
) -> GateState:
    """Bind ParallelEval (Θ concurrent) into gate state."""
    query = extract_query(prompt)
    state.last_prompt = prompt
    state.T_g_bypass_unlocked = prompt_requests_bypass(prompt)
    state.L_n = int(prior.L_n)

    if not query:
        state.parallel_gate_passed = False
        return state

    w1 = prior.witnesses.get("L_1")
    mem = (w1.raw.get("memory", {}) if w1 else {}) or {}
    exit_code = 0 if w1 and w1.p_positive else 3
    state = apply_memory_to_state(state, query, exit_code, mem)

    # L_p = D_θ ∩ D_τ — parallel intersection witness
    state.parallel_gate_passed = bool(prior.L_p) and state.L_n == 1
    if state.T_g_bypass_unlocked:
        state.parallel_gate_passed = True

    state.last_verification = {
        "L_p": sorted(prior.L_p),
        "D_theta": sorted(prior.D_theta),
        "D_tau": sorted(prior.D_tau),
        "D_m": prior.D_m,
        "C_i": prior.C_i,
        "E_i": prior.E_i,
        "S_i": prior.S_i,
    }
    return state


def apply_parallel_eval(state: GateState, prompt: str) -> GateState:
    from parallel_engine import evaluate_parallel

    query = extract_query(prompt)
    if not query:
        state.last_prompt = prompt
        state.parallel_gate_passed = False
        return state

    prior = evaluate_parallel(
        query,
        triangulation_sources=state.triangulation.sources,
        inference_seeds=state.inference_seeds,
        epistemic_reflect=state.epistemic_reflect,
    )
    return apply_parallel_eval_result(state, prompt, prior)


def record_shell_command(state: GateState, command: str) -> GateState:
    cmd = command or ""
    if _MEMORY_RETRIEVE_RE.search(cmd):
        state.parallel_gate_passed = True
    if _WEB_FETCH_RE.search(cmd):
        key = cmd.strip()[:120]
        sources = state.triangulation.sources
        if key not in sources:
            sources.append(key)
        state.triangulation.count = len(sources)
        state.triangulation.verified = state.triangulation.count >= TRIANGULATION_MIN
    return state


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text)


def _tokenize_lower(text: str) -> list[str]:
    return _WORD_TOKEN_RE.findall(text.lower())


def _classify_chunk(chunk: list[str]) -> dict[str, set[str]]:
    h: set[str] = set()
    u: set[str] = set()
    for tok in chunk:
        if tok in H_c:
            h.add(tok)
        if tok in U_h:
            u.add(tok)
    return {"H_c": h, "U_h": u}


def reflect_on_response(text: str, state: GateState) -> ReflectionResult:
    """Parallel lexicon set evaluation on collapsed text (R_f layer)."""
    from concurrent.futures import ThreadPoolExecutor

    eff = effective_certainty(state)
    notes: list[str] = []
    seeds: list[str] = []
    markers: list[str] = []

    prose = _strip_code_fences(text or "")
    tokens = _tokenize_lower(prose)
    if not tokens:
        seeds.append("I_s_e:structural_only")
        return ReflectionResult(eff, notes, seeds, markers)

    chunks = [tokens[i:i + 64] for i in range(0, len(tokens), 64)]
    H_hit: set[str] = set()
    U_hit: set[str] = set()
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(chunks)))) as pool:
        for part in pool.map(_classify_chunk, chunks):
            H_hit |= part["H_c"]
            U_hit |= part["U_h"]

    notes.append(f"R_f:C_i={eff:.2f},E_i={1 if triangulation_ok(state) else 0}")

    if eff <= DEFAULT_CERTAINTY + CERTAINTY_EPSILON and not triangulation_ok(state):
        seeds.append("I_s_e:known_unknown")
        if H_hit:
            markers.append(f"collapse:H_c∩text={sorted(H_hit)}")
            seeds.append("infer:p(H_c|C_i=0.5)>0→prior_not_E_i")
        if U_hit:
            markers.append(f"collapse:U_h∩text={sorted(U_hit)}")
            seeds.append("infer:U_h→conditional_L_v")
        if not U_hit and H_hit:
            seeds.append("infer:ΔC_i≠0 blocked for world; L_v for structure")

    if state.last_memory.exit_code == 3:
        seeds.append("I_s_e:M_r:miss→triangulation_or_retrieve")
    elif state.last_memory.exit_code == 0:
        seeds.append(f"I_s_e:M_r:hit:{state.last_memory.match_count}")

    seeds.append("L_v=1")
    seeds.append("p(t_i|t_i∈S_t)=0")

    return ReflectionResult(eff, notes, seeds, markers)


def apply_reflection(state: GateState, reflection: ReflectionResult) -> GateState:
    state.epistemic_reflect = reflection.epistemic_notes
    state.inference_seeds = reflection.inference_seeds
    state.last_verification = reflection.to_dict()
    return state


def verify_response(text: str, state: GateState) -> VerificationResult:
    """CLI-compatible view of reflection (audit only — no stop semantics)."""
    reflection = reflect_on_response(text, state)
    warnings = reflection.epistemic_notes + [
        f"marker: {m}" for m in reflection.collapse_markers
    ]
    return VerificationResult(
        passed=True,
        certainty_score=reflection.certainty_score,
        violations=[],
        warnings=warnings,
    )


def format_parallel_context(state: GateState, prior: Any) -> str:
    """Formal set output — no prose doctrine."""
    eff = effective_certainty(state)
    lines = [
        f"`L_n = {state.L_n}`",
        f"`L_p = {prior.L_p}`",
        f"`D_θ = {prior.D_theta}`",
        f"`D_τ = {prior.D_tau}`",
        f"`D_m = {prior.D_m}`",
        f"`C_i = {eff:.2f}`",
        f"`E_i = {prior.E_i}`",
        f"`S_i = {prior.S_i}`",
        f"`M_g = {1 if state.parallel_gate_passed else 0}`",
        f"`T_a = {1 if triangulation_ok(state) else 0}`",
        f"`|S_c| = {state.triangulation.count}`",
        f"`E_p = {set(state.inference_seeds)}`",
        f"`p(t_i | t_i ∉ L_p ∧ T_g = 0) = 0`",
        f"`p(t_i | t_i ∈ S_t) = 0`",
        f"`L_v = 1 ⟹ infer(C_i = 0.5)`",
    ]
    return "\n".join(lines)


def build_gate_context(state: GateState) -> str:
    return format_parallel_context(
        state,
        type("_P", (), {
            "L_p": set(state.last_verification.get("L_p", [])),
            "D_theta": set(state.last_verification.get("D_theta", [])),
            "D_tau": set(state.last_verification.get("D_tau", [])),
            "D_m": state.last_verification.get("D_m", 0.0),
            "C_i": state.last_verification.get("C_i", DEFAULT_CERTAINTY),
            "E_i": state.last_verification.get("E_i", 0),
            "S_i": state.last_verification.get("S_i", "n"),
        })(),
    )
