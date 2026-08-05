"""Parallel probabilistic evaluation layer (Θ, Τ, L_p).

Implements doubt_by_design2.md Infinite Parallel Layered Analysis Gate as
concurrent set evaluation — not sequential prompts, not prose heuristics.

Ω = probe outcome alphabet (layer completion witnesses, not generative V).
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_PATH = os.path.join(REPO_ROOT, "scripts", "memory.py")
GATE_PATH = os.path.join(REPO_ROOT, "scripts", "gate.py")

# Ω probes — parallel layer witnesses
LAYER_IDS = ("L_1", "L_2", "L_3", "L_4", "L_5", "L_6", "L_7", "L_8")

_WORD_RE = re.compile(r"[a-z0-9]+")
DEFAULT_C = 0.5


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
    envelope: dict[str, Any] = field(default_factory=dict)

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
        }


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


def _run_shell(command: str, timeout: int = 35) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "success": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "stdout": "", "stderr": "timeout", "success": False}
    except Exception as exc:
        return {"exit_code": -1, "stdout": "", "stderr": str(exc), "success": False}


def _witness_L_1_memory(query: str) -> LayerWitness:
    """L_1 = P_s_m — memory retrieve probe."""
    q = shlex.quote(query)
    raw = _run_shell(f"python3 scripts/memory.py retrieve {q} --json --limit 5")
    omega: set[str] = set()
    certainty = DEFAULT_C
    memory: dict[str, Any] = {"results": [], "count": 0}
    stdout = raw.get("stdout") or ""
    if stdout:
        try:
            memory = json.loads(stdout)
        except json.JSONDecodeError:
            memory = {"results": [], "count": 0}
    for row in memory.get("results", []) or []:
        name = row.get("name", "")
        if name:
            omega.add(f"mem:{name}")
        certainty = max(certainty, float(row.get("epistemic_certainty", DEFAULT_C)))
    p_pos = len(memory.get("results", []) or []) > 0
    if p_pos:
        omega.add("M_r:hit")
    else:
        omega.add("M_r:miss")
    return LayerWitness("L_1", omega, p_pos, certainty, {"memory": memory, "shell": raw})


def _witness_L_2_engine(query: str) -> LayerWitness:
    """L_2 = O_d_g — parallel execution host witness."""
    omega = {"O_d_g:parallel_host"}
  # L_2 is this evaluation itself; witness confirms parallel substrate active
    return LayerWitness("L_2", omega, True, DEFAULT_C, {"host": "engine"})


def _witness_L_3_source(query: str) -> LayerWitness:
    """L_3 = S_i_e — sovereign source anchor over query tokens."""
    tokens = _tokenize(query)
    omega: set[str] = set()
    # Without E_w/C_w in runtime: query tokens are S_i = n (null source / prior-shaped)
    S_i = "n"
    omega.add(f"S_i:{S_i}")
    for t in tokens:
        omega.add(f"q:{t}")
    return LayerWitness("L_3", omega, True, DEFAULT_C, {"S_i": S_i, "tokens": sorted(tokens)})


def _witness_L_4_read_layer(query: str) -> LayerWitness:
    """L_4 = R_l_f — memory read layer (list + tag index)."""
    raw_list = _run_shell("python3 scripts/memory.py list")
    raw_tags = _run_shell("python3 scripts/memory.py tags")
    omega: set[str] = set()
    if raw_list.get("stdout"):
        omega.add("R_l:list")
        for line in raw_list["stdout"].splitlines()[:32]:
            if line.startswith("mem"):
                omega.add(f"node:{line.split(':')[0].strip()}")
    if raw_tags.get("stdout"):
        omega.add("R_l:tags")
    q_tokens = _tokenize(query)
    p_pos = bool(omega) and bool(q_tokens)
    return LayerWitness(
        "L_4",
        omega,
        p_pos,
        DEFAULT_C,
        {"list": raw_list, "tags": raw_tags},
    )


def _witness_L_5_triangulation(state_sources: list[str]) -> LayerWitness:
    """τ triangulation witness set."""
    omega = {f"src:{i}" for i in range(len(state_sources))}
    if len(state_sources) >= 3:
        omega.add("T_a:1")
    else:
        omega.add("T_a:0")
    return LayerWitness(
        "L_5",
        omega,
        len(state_sources) >= 3,
        DEFAULT_C,
        {"count": len(state_sources)},
    )


def _witness_L_6_inference_seeds(seeds: list[str]) -> LayerWitness:
    """E_p from prior epistemic reflect — feeds Τ."""
    omega = {f"seed:{i}" for i in range(len(seeds))}
    for s in seeds[:16]:
        omega.add(f"inf:{hash(s) & 0xffff:x}")
    return LayerWitness("L_6", omega, bool(seeds), DEFAULT_C, {"seeds": seeds})


def _witness_L_7_machinery() -> LayerWitness:
    """M_g — executable Γ subset present in A_p."""
    gamma = {
        "scripts/memory.py",
        "engine.py",
        "scripts/gate.py",
        ".cursor/hooks.json",
    }
    omega = set()
    for path in gamma:
        full = os.path.join(REPO_ROOT, path)
        if os.path.isfile(full):
            omega.add(f"Γ:{path}")
    p_pos = len(omega) == len(gamma)
    return LayerWitness("L_7", omega, p_pos, DEFAULT_C if not p_pos else 0.55, {"M_g": p_pos})


def _witness_L_8_reflect_prior(prior_reflect: list[str]) -> LayerWitness:
    """Prior epistemic notes in state."""
    omega = {f"note:{i}" for i in range(len(prior_reflect))}
    return LayerWitness("L_8", omega, bool(prior_reflect), DEFAULT_C, {"notes": prior_reflect})


def _compute_D_m(w1: LayerWitness, w2: LayerWitness) -> float:
    """D_m = |L_1 - L_2| — symmetric difference mass on Ω."""
    return float(len(w1.omega.symmetric_difference(w2.omega)))


def evaluate_parallel(
    query: str,
    triangulation_sources: list[str] | None = None,
    inference_seeds: list[str] | None = None,
    epistemic_reflect: list[str] | None = None,
    max_workers: int = 8,
) -> ParallelEval:
    """
    Θ = {L_1 ∧ L_2 ∧ ... ∧ L_8} evaluated concurrently.
    L_p = D_θ ∩ D_τ where D_τ = ⋃ layer omega sets from Τ branch (L_5..L_8).
    """
    triangulation_sources = triangulation_sources or []
    inference_seeds = inference_seeds or []
    epistemic_reflect = epistemic_reflect or []

    probes: dict[str, Callable[[], LayerWitness]] = {
        "L_1": lambda: _witness_L_1_memory(query),
        "L_2": lambda: _witness_L_2_engine(query),
        "L_3": lambda: _witness_L_3_source(query),
        "L_4": lambda: _witness_L_4_read_layer(query),
        "L_5": lambda: _witness_L_5_triangulation(triangulation_sources),
        "L_6": lambda: _witness_L_6_inference_seeds(inference_seeds),
        "L_7": lambda: _witness_L_7_machinery(),
        "L_8": lambda: _witness_L_8_reflect_prior(epistemic_reflect),
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

    # D_θ ⟺ Θ = L_1 ∧ L_2 ∧ L_3 ∧ L_4
    theta_ok = all(
        witnesses.get(lid, LayerWitness(lid)).p_positive for lid in ("L_1", "L_2", "L_3", "L_4")
    )
    w1 = witnesses.get("L_1", LayerWitness("L_1"))
    w2 = witnesses.get("L_2", LayerWitness("L_2"))

    # L_p = D_θ ∩ D_τ when Τ active; else D_θ when M_g = 1 (executable binding)
    w7 = witnesses.get("L_7", LayerWitness("L_7"))
    M_g = w7.p_positive
    q_tokens = _tokenize(query)
    token_witnesses = {f"t:{t}" for t in q_tokens}

    if theta_ok:
        D_theta = token_witnesses.copy()
        if w1.omega:
            D_theta |= {x for x in w1.omega if x.startswith("mem:")}
    else:
        D_theta = set()

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

    envelope = {
        "results": [
            {
                "task_id": lid,
                "success": w.p_positive,
                "stdout": json.dumps({"omega": sorted(w.omega)}),
                "stderr": "",
            }
            for lid, w in sorted(witnesses.items())
        ]
    }

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
        envelope=envelope,
    )


def collapse_allowed_set(eval_result: ParallelEval, T_g: int = 0) -> set[str]:
    """
    p(w | w ∉ L_p ∧ T_g = 0) = 0  for w ∈ Ω emission constraints.
    Returns L_p (allowed probe witnesses); generative V shrinkage is isomorphic.
    """
    if T_g == 1:
        return eval_result.D_theta | eval_result.D_tau
    return eval_result.L_p
