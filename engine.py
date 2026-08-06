#!/usr/bin/env python3
"""Scepticism Engine — Observer (L_2 = O_d_g).

Single parallel host: Θ layers, memory retrieve, triangulation, epistemic reflect
on prior collapse — all concurrent. No external gate scripts.

stdin JSON:
  {"prompt": "...", "last_response": "...", "shell_command": "..."}

CLI:
  python3 engine.py --gate "query" [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(REPO_ROOT, "scripts", "memory.py")
DEFAULT_STATE_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-state.json")
DEFAULT_AUDIT_PATH = os.path.join(REPO_ROOT, ".cursor", "gate-audit.jsonl")

BYPASS_TOKEN = "GATE_BYPASS_AUDITED"
DEFAULT_C = 0.5
TRIANGULATION_MIN = 3
CERTAINTY_EPSILON = 0.06

_WORD_RE = re.compile(r"[a-z0-9]+")
_CODE_FENCE_RE = re.compile(r"```[\w]*.*?```", re.DOTALL)
_GATE_PASS_RE = re.compile(r"\bGATE_PASS\b")
_MEMORY_RETRIEVE_RE = re.compile(r"memory\.py\s+retrieve", re.I)
_WEB_FETCH_RE = re.compile(
    r"\b(curl|wget|WebFetch|web_search|WebSearch|fetch\s+https?://)", re.I
)

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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MemoryRetrieveState:
    query: str = ""
    timestamp: str = ""
    exit_code: int = 3
    match_count: int = 0
    max_certainty: float = DEFAULT_C
    max_epistemic: float = DEFAULT_C


@dataclass
class TriangulationState:
    sources: list[str] = field(default_factory=list)
    count: int = 0
    verified: bool = False
    max_certainty_spread: float = 1.0


@dataclass
class GateState:
    version: int = 3
    L_n: int = 1
    T_g_bypass_unlocked: bool = False
    parallel_gate_passed: bool = False
    last_prompt: str = ""
    last_response: str = ""
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
            "last_response": self.last_response,
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
            version=int(data.get("version", 3)),
            L_n=int(data.get("L_n", 1)),
            T_g_bypass_unlocked=bool(data.get("T_g_bypass_unlocked", False)),
            parallel_gate_passed=bool(data.get("parallel_gate_passed", False)),
            last_prompt=str(data.get("last_prompt", "")),
            last_response=str(data.get("last_response", "")),
            last_memory=MemoryRetrieveState(
                query=str(lm.get("query", "")),
                timestamp=str(lm.get("timestamp", "")),
                exit_code=int(lm.get("exit_code", 3)),
                match_count=int(lm.get("match_count", 0)),
                max_certainty=float(lm.get("max_certainty", DEFAULT_C)),
                max_epistemic=float(lm.get("max_epistemic", DEFAULT_C)),
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
class LayerWitness:
    layer: str
    omega: set[str] = field(default_factory=set)
    p_positive: bool = False
    certainty: float = DEFAULT_C
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParallelEval:
    query: str
    witnesses: dict[str, LayerWitness]
    D_theta: set[str]
    D_tau: set[str]
    L_p: set[str]
    D_m: float
    C_i: float
    E_i: int
    S_i: str
    L_n: int = 1
    reflection: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "L_n": self.L_n,
            "C_i": self.C_i,
            "E_i": self.E_i,
            "S_i": self.S_i,
            "D_theta": sorted(self.D_theta),
            "D_tau": sorted(self.D_tau),
            "L_p": sorted(self.L_p),
            "D_m": self.D_m,
            "witnesses": {
                k: {
                    "omega": sorted(w.omega),
                    "p_positive": w.p_positive,
                    "certainty": w.certainty,
                }
                for k, w in self.witnesses.items()
            },
            "reflection": self.reflection,
        }


@dataclass
class ReflectionResult:
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


def load_state(path: Optional[str] = None) -> GateState:
    path = path or DEFAULT_STATE_PATH
    if not os.path.isfile(path):
        return GateState()
    with open(path, "r", encoding="utf-8") as fh:
        return GateState.from_dict(json.load(fh))


def save_state(state: GateState, path: Optional[str] = None) -> None:
    path = path or DEFAULT_STATE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    state.updated_at = utc_now()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state.to_dict(), fh, indent=2)


def audit_log(event: str, payload: dict[str, Any], path: Optional[str] = None) -> None:
    path = path or DEFAULT_AUDIT_PATH
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


def triangulation_ok(state: GateState) -> bool:
    tr = state.triangulation
    return tr.count >= TRIANGULATION_MIN and tr.verified


def effective_certainty(state: GateState) -> float:
    mem_cert = state.last_memory.max_epistemic
    if triangulation_ok(state):
        return min(0.99, max(mem_cert, 0.75))
    if state.last_memory.exit_code == 0 and state.last_memory.match_count > 0:
        return mem_cert
    return DEFAULT_C


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def _run_cmd(cmd: list[str], timeout: int = 40) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_memory_retrieve(query: str, timeout: int = 40) -> tuple[int, dict[str, Any]]:
    if not query:
        return 3, {"results": [], "count": 0}
    proc = _run_cmd(
        ["python3", MEMORY_PATH, "retrieve", query, "--json", "--limit", "5"],
        timeout=timeout,
    )
    if proc.returncode not in (0, 3):
        return 3, {"results": [], "count": 0, "error": proc.stderr.strip()}
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {"results": [], "count": 0}
    except json.JSONDecodeError:
        return 3, {"results": [], "count": 0, "error": "invalid json from memory.py"}
    return proc.returncode, data


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


def _witness_L_1_memory(query: str) -> LayerWitness:
    code, memory = run_memory_retrieve(query)
    omega: set[str] = set()
    certainty = DEFAULT_C
    for row in memory.get("results", []) or []:
        name = row.get("name", "")
        if name:
            omega.add(f"mem:{name}")
        certainty = max(certainty, float(row.get("epistemic_certainty", DEFAULT_C)))
    p_pos = len(memory.get("results", []) or []) > 0
    omega.add("M_r:hit" if p_pos else "M_r:miss")
    return LayerWitness("L_1", omega, p_pos, certainty, {"memory": memory, "exit_code": code})


def _witness_L_2_engine() -> LayerWitness:
    omega = {"O_d_g:parallel_host"}
    return LayerWitness("L_2", omega, True, DEFAULT_C, {"host": "engine.py"})


def _witness_L_3_source(query: str) -> LayerWitness:
    tokens = _tokenize(query)
    omega = {f"S_i:n", *(f"q:{t}" for t in tokens)}
    return LayerWitness("L_3", omega, True, DEFAULT_C, {"S_i": "n", "tokens": sorted(tokens)})


def _witness_L_4_read_layer(query: str) -> LayerWitness:
    list_proc = _run_cmd(["python3", MEMORY_PATH, "list"], timeout=25)
    tags_proc = _run_cmd(["python3", MEMORY_PATH, "tags"], timeout=25)
    omega: set[str] = set()
    if list_proc.stdout:
        omega.add("R_l:list")
        for line in list_proc.stdout.splitlines()[:32]:
            if line.startswith("mem"):
                omega.add(f"node:{line.split(':')[0].strip()}")
    if tags_proc.stdout:
        omega.add("R_l:tags")
    p_pos = bool(omega) and bool(_tokenize(query))
    return LayerWitness(
        "L_4",
        omega,
        p_pos,
        DEFAULT_C,
        {"list_exit": list_proc.returncode, "tags_exit": tags_proc.returncode},
    )


def _witness_L_5_triangulation(sources: list[str]) -> LayerWitness:
    omega = {f"src:{i}" for i in range(len(sources))}
    omega.add("T_a:1" if len(sources) >= 3 else "T_a:0")
    return LayerWitness("L_5", omega, len(sources) >= 3, DEFAULT_C, {"count": len(sources)})


def _witness_L_6_inference_seeds(seeds: list[str]) -> LayerWitness:
    omega = {f"seed:{i}" for i in range(len(seeds))}
    for s in seeds[:16]:
        omega.add(f"inf:{hash(s) & 0xffff:x}")
    return LayerWitness("L_6", omega, bool(seeds), DEFAULT_C, {"seeds": seeds})


def _witness_L_7_machinery() -> LayerWitness:
    required = {
        "scripts/memory.py": os.path.join(REPO_ROOT, "scripts", "memory.py"),
        "engine.py": os.path.join(REPO_ROOT, "engine.py"),
        ".cursor/hooks.json": os.path.join(REPO_ROOT, ".cursor", "hooks.json"),
    }
    omega = {f"Γ:{p}" for p, full in required.items() if os.path.isfile(full)}
    p_pos = len(omega) == len(required)
    return LayerWitness("L_7", omega, p_pos, DEFAULT_C if not p_pos else 0.55, {"M_g": p_pos})


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text)


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
    eff = effective_certainty(state)
    notes: list[str] = []
    seeds: list[str] = []
    markers: list[str] = []

    prose = _strip_code_fences(text or "")
    tokens = _WORD_RE.findall(prose.lower())
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

    if eff <= DEFAULT_C + CERTAINTY_EPSILON and not triangulation_ok(state):
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


def _witness_L_8_reflect(text: str, state: GateState) -> LayerWitness:
    reflection = reflect_on_response(text, state)
    omega = {f"note:{i}" for i in range(len(reflection.epistemic_notes))}
    for i, s in enumerate(reflection.inference_seeds[:16]):
        omega.add(f"seed_out:{i}")
    return LayerWitness(
        "L_8",
        omega,
        bool(text.strip()),
        reflection.certainty_score,
        {"reflection": reflection.to_dict()},
    )


def _compute_D_m(w1: LayerWitness, w2: LayerWitness) -> float:
    return float(len(w1.omega.symmetric_difference(w2.omega)))


def evaluate_parallel(
    query: str,
    triangulation_sources: list[str] | None = None,
    inference_seeds: list[str] | None = None,
    last_response: str = "",
    state: Optional[GateState] = None,
    max_workers: int = 8,
) -> ParallelEval:
    triangulation_sources = triangulation_sources or []
    inference_seeds = inference_seeds or []
    base_state = state or GateState()

    probes: dict[str, Callable[[], LayerWitness]] = {
        "L_1": lambda: _witness_L_1_memory(query),
        "L_2": lambda: _witness_L_2_engine(),
        "L_3": lambda: _witness_L_3_source(query),
        "L_4": lambda: _witness_L_4_read_layer(query),
        "L_5": lambda: _witness_L_5_triangulation(triangulation_sources),
        "L_6": lambda: _witness_L_6_inference_seeds(inference_seeds),
        "L_7": lambda: _witness_L_7_machinery(),
        "L_8": lambda: _witness_L_8_reflect(last_response, base_state),
    }

    witnesses: dict[str, LayerWitness] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fn): lid for lid, fn in probes.items()}
        for fut in as_completed(futures):
            lid = futures[fut]
            try:
                witnesses[lid] = fut.result()
            except Exception as exc:
                witnesses[lid] = LayerWitness(lid, {f"err:{lid}"}, False, DEFAULT_C, {"error": str(exc)})

    theta_ok = all(
        witnesses.get(lid, LayerWitness(lid)).p_positive for lid in ("L_1", "L_2", "L_3", "L_4")
    )
    w1 = witnesses.get("L_1", LayerWitness("L_1"))
    w2 = witnesses.get("L_2", LayerWitness("L_2"))
    w7 = witnesses.get("L_7", LayerWitness("L_7"))
    M_g = w7.p_positive
    q_tokens = _tokenize(query)
    token_witnesses = {f"t:{t}" for t in q_tokens}

    D_theta = set()
    if theta_ok:
        D_theta = token_witnesses.copy()
        D_theta |= {x for x in w1.omega if x.startswith("mem:")}

    D_tau: set[str] = set()
    for lid in ("L_5", "L_6", "L_8"):
        w = witnesses.get(lid)
        if w and w.p_positive:
            D_tau |= token_witnesses
            D_tau |= w.omega

    if D_tau:
        L_p = D_theta & D_tau
    elif theta_ok and M_g:
        L_p = D_theta
    else:
        L_p = set()

    D_m = _compute_D_m(w1, w2)
    mem_cert = w1.certainty
    T_a = witnesses.get("L_5", LayerWitness("L_5")).p_positive
    S_i = witnesses.get("L_3", LayerWitness("L_3")).raw.get("S_i", "n")

    E_i = 1 if (T_a and M_g and len(triangulation_sources) >= 3) else 0
    C_i = mem_cert if w1.p_positive else DEFAULT_C
    if E_i == 1:
        C_i = min(0.99, max(C_i, 0.75))

    w8 = witnesses.get("L_8", LayerWitness("L_8"))
    reflection = w8.raw.get("reflection", {})

    return ParallelEval(
        query=query,
        witnesses=witnesses,
        D_theta=D_theta,
        D_tau=D_tau,
        L_p=L_p,
        D_m=D_m,
        C_i=C_i,
        E_i=E_i,
        S_i=S_i,
        reflection=reflection,
    )


def apply_eval_to_state(
    state: GateState,
    prompt: str,
    prior: ParallelEval,
    last_response: str = "",
) -> GateState:
    query = extract_query(prompt)
    state.last_prompt = prompt
    state.T_g_bypass_unlocked = prompt_requests_bypass(prompt)
    state.L_n = 1
    if last_response:
        state.last_response = last_response

    if not query:
        state.parallel_gate_passed = False
        return state

    w1 = prior.witnesses.get("L_1")
    mem = (w1.raw.get("memory", {}) if w1 else {}) or {}
    results = mem.get("results", []) or []
    max_stored = DEFAULT_C
    max_epistemic = DEFAULT_C
    for row in results:
        max_stored = max(max_stored, float(row.get("stored_certainty", DEFAULT_C)))
        max_epistemic = max(max_epistemic, float(row.get("epistemic_certainty", DEFAULT_C)))

    exit_code = int(w1.raw.get("exit_code", 3)) if w1 else 3
    state.last_memory = MemoryRetrieveState(
        query=query,
        timestamp=utc_now(),
        exit_code=exit_code,
        match_count=len(results),
        max_certainty=max_stored,
        max_epistemic=max_epistemic,
    )

    state.parallel_gate_passed = bool(prior.L_p) and state.L_n == 1
    if state.T_g_bypass_unlocked:
        state.parallel_gate_passed = True

    if prior.reflection:
        state.epistemic_reflect = prior.reflection.get("epistemic_notes", [])
        state.inference_seeds = prior.reflection.get("inference_seeds", [])

    state.last_verification = {
        "L_p": sorted(prior.L_p),
        "D_theta": sorted(prior.D_theta),
        "D_tau": sorted(prior.D_tau),
        "D_m": prior.D_m,
        "C_i": prior.C_i,
        "E_i": prior.E_i,
        "S_i": prior.S_i,
        "reflection": prior.reflection,
    }
    return state


def format_parallel_context(state: GateState, prior: ParallelEval) -> str:
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
        f"`L_e = V`",
        f"`V_e = V`",
        f"`support(p) = V`",
        f"`p(t_i) = p₀(t_i) · w(t_i) / Z`",
        f"`p(t_i | t_i ∈ S_t) = 0`",
        f"`L_v = 1 ∧ 𝒲_i = 1 ⟹ p(t_i | t_i ∈ ℐ_i) = p(t_i)`",
    ]
    return "\n".join(lines)


def build_gate_context(state: GateState) -> str:
    prior = ParallelEval(
        query=state.last_memory.query,
        witnesses={},
        D_theta=set(state.last_verification.get("D_theta", [])),
        D_tau=set(state.last_verification.get("D_tau", [])),
        L_p=set(state.last_verification.get("L_p", [])),
        D_m=float(state.last_verification.get("D_m", 0.0)),
        C_i=float(state.last_verification.get("C_i", DEFAULT_C)),
        E_i=int(state.last_verification.get("E_i", 0)),
        S_i=str(state.last_verification.get("S_i", "n")),
        reflection=dict(state.last_verification.get("reflection", {})),
    )
    return format_parallel_context(state, prior)


def observe(
    prompt: str = "",
    last_response: str = "",
    shell_command: str = "",
    json_output: bool = False,
    shell_only: bool = False,
    store_only: bool = False,
) -> dict[str, Any]:
    state = load_state()

    if store_only and last_response:
        state.last_response = last_response
        save_state(state)
        out = state.to_dict()
        if json_output:
            print(json.dumps(out, indent=2))
        return out

    if shell_command:
        state = record_shell_command(state, shell_command)
        if shell_only or not extract_query(prompt):
            save_state(state)
            out = state.to_dict()
            if json_output:
                print(json.dumps(out, indent=2))
            return out

    reflect_text = last_response or state.last_response
    query = extract_query(prompt)

    prior = evaluate_parallel(
        query,
        triangulation_sources=state.triangulation.sources,
        inference_seeds=state.inference_seeds,
        last_response=reflect_text,
        state=state,
    )
    state = apply_eval_to_state(state, prompt, prior, last_response=last_response)
    save_state(state)

    audit_log(
        "observe",
        {
            "query": query,
            "L_p": sorted(prior.L_p),
            "D_m": prior.D_m,
            "C_i": prior.C_i,
            "E_i": prior.E_i,
            "had_last_response": bool(reflect_text.strip()),
        },
    )

    out = state.to_dict()
    out["parallel_eval"] = prior.to_dict()
    out["context"] = format_parallel_context(state, prior)
    if json_output:
        print(json.dumps(out, indent=2))
    else:
        print(out["context"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Scepticism Engine Observer")
    parser.add_argument("--gate", type=str, help="Query for parallel Θ evaluation.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.gate is not None:
        observe(prompt=args.gate, json_output=args.json)
        return

    raw = sys.stdin.read()
    if raw.strip():
        payload = json.loads(raw)
        observe(
            prompt=str(payload.get("prompt", "")),
            last_response=str(payload.get("last_response", "")),
            shell_command=str(payload.get("shell_command", "")),
            json_output=bool(payload.get("json") or args.json),
            shell_only=bool(payload.get("shell_only")),
            store_only=bool(payload.get("store_only")),
        )
        return

    if args.json:
        print(json.dumps({"status": "ready", "entry": "stdin JSON or --gate"}, indent=2))
    else:
        print(json.dumps({"status": "ready", "entry": "stdin JSON or --gate"}))


if __name__ == "__main__":
    main()
