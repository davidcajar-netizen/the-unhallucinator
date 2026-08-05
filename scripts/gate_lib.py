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

_HEDGE_RE = re.compile(
    r"\b(may|might|could|possibly|perhaps|uncertain|unverified|unknown|"
    r"not sure|don't know|cannot verify|can't verify|i don't have|"
    r"0\.5|maximum uncertainty|training data|prior)\b",
    re.I,
)
_HIGH_CONFIDENCE_RE = re.compile(
    r"\b(definitely|certainly|always|never|proven|undeniably|"
    r"it is true that|the fact is|without doubt|100%)\b",
    re.I,
)
_FACT_ASSERTION_RE = re.compile(
    r"(?<![\w/])(?:the |this |that )?[A-Z][\w\s,'-]{2,40}\s+"
    r"(?:is|are|was|were|has|have|will)\s+[^.\n]{5,80}",
)
_CODE_FENCE_RE = re.compile(r"```[\w]*.*?```", re.DOTALL)
_GATE_PASS_RE = re.compile(r"\bGATE_PASS\b")
_MEMORY_RETRIEVE_RE = re.compile(r"memory\.py\s+retrieve", re.I)
_WEB_FETCH_RE = re.compile(
    r"\b(curl|wget|WebFetch|web_search|WebSearch|fetch\s+https?://)", re.I
)


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


def apply_parallel_eval(state: GateState, prompt: str) -> GateState:
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

    parallel = run_parallel_gate(query)
    mem = parallel.get("memory", {})
    results = mem.get("results", []) or []
    exit_code = int(parallel.get("memory_exit_code", 3))

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

  # Parallel gate passes when L_n active and we completed eval (memory is optional)
    state.parallel_gate_passed = state.L_n == 1 and bool(query)
    if state.T_g_bypass_unlocked:
        state.parallel_gate_passed = True

    return state


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


def reflect_on_response(text: str, state: GateState) -> ReflectionResult:
    """Record what collapsed at what C_i; derive inference seeds for the next pass.

    L_v (logical inference exemption): knowing you do not know at C_i=0.5 is valid
    substrate for inference — not abstention, not stop-and-correct.
    """
    eff = effective_certainty(state)
    notes: list[str] = []
    seeds: list[str] = []
    markers: list[str] = []

    prose = _strip_code_fences(text or "")
    if not prose.strip():
        seeds.append(
            "Empty or code-only collapse: infer structural constraints only; "
            "world facts remain S_i=n, C_i=0.5 until evidenced."
        )
        return ReflectionResult(eff, notes, seeds, markers)

    notes.append(f"Post-collapse epistemic workspace: C_i={eff:.2f}, E_i={1 if triangulation_ok(state) else 0}.")

    if eff <= DEFAULT_CERTAINTY + CERTAINTY_EPSILON and not triangulation_ok(state):
        seeds.append(
            "Known unknown (C_i=0.5): training prior is not observation. "
            "Infer: what would verify this? what follows logically without claiming sight?"
        )
        if state.last_memory.exit_code == 3 and state.last_memory.query:
            seeds.append(
                f"No local memory for {state.last_memory.query!r}: "
                "infer retrieval paths or triangulation needs — do not fabricate recall."
            )
        elif state.last_memory.exit_code == 0:
            seeds.append(
                f"Memory matched ({state.last_memory.match_count} nodes) at "
                f"epistemic {state.last_memory.max_epistemic:.2f}: infer from stored nodes, not beyond them."
            )

    if _HIGH_CONFIDENCE_RE.search(prose):
        markers.append("collapse_used_high_confidence_lexicon")
        if eff <= DEFAULT_CERTAINTY + CERTAINTY_EPSILON:
            notes.append(
                "Collapse carried definitely/certainly/always lexicon while C_i≈0.5 — "
                "treat apparent certainty as rhetorical collapse, not E_i=1."
            )
            seeds.append(
                "Infer: high-confidence tokens at baseline C_i are prior-shaped, not verified. "
                "Separate logical structure from unverified world claims."
            )

    for match in _FACT_ASSERTION_RE.finditer(prose):
        snippet = match.group(0).strip()
        window = prose[max(0, match.start() - 40): match.end() + 40]
        if _HEDGE_RE.search(window):
            markers.append(f"hedged_assertion: {snippet[:80]}")
            seeds.append(
                f"From hedged claim '{snippet[:60]}…': infer conditional implications, not fact."
            )
            continue
        if eff <= DEFAULT_CERTAINTY + CERTAINTY_EPSILON and not triangulation_ok(state):
            markers.append(f"unhedged_world_assertion: {snippet[:80]}")
            notes.append(f"World-shaped collapse without hedge: {snippet[:100]}")
            seeds.append(
                "Infer epistemic gap: assertion collapsed without hedge at C_i=0.5 — "
                "what evidence would move C_i? what remains unknowable without instruments?"
            )

    if not state.parallel_gate_passed and not state.T_g_bypass_unlocked:
        notes.append("Parallel gate was not run before this collapse; L_p intersection unknown.")

    seeds.append(
        "L_v=1: logical inference from known uncertainty is permitted — "
        "reason about ignorance, implications, and verification paths; do not stop."
    )

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


def build_gate_context(state: GateState) -> str:
    eff = effective_certainty(state)
    lines = [
        "## Scepticism Engine Gate State (inference from uncertainty — not abstention)",
        f"- L_n (parallel analysis): {state.L_n}",
        f"- parallel_gate_passed: {state.parallel_gate_passed}",
        f"- effective_certainty C_i: {eff:.2f} — workspace for inference, not silence",
        f"- memory_query: {state.last_memory.query!r}",
        f"- memory_exit_code: {state.last_memory.exit_code} (0=match, 3=no match)",
        f"- memory_matches: {state.last_memory.match_count}",
        f"- triangulation_count: {state.triangulation.count} (need {TRIANGULATION_MIN})",
        f"- triangulation_verified T_a: {triangulation_ok(state)}",
        "",
        "Doctrine:",
        "- Knowing you do not know (C_i=0.5, S_i=n) is valid — infer FROM that.",
        "- L_v=1: logical inference exempt; reason about gaps, verification, implications.",
        "- Do not abstain. Do not stop-and-correct loops. Collapse once; reflect; infer next.",
        "- E_i=1 only after memory gate + triangulation; prior alone is not observation.",
    ]
    if state.epistemic_reflect:
        lines.append("")
        lines.append("Epistemic reflect (last collapse):")
        for note in state.epistemic_reflect:
            lines.append(f"- {note}")
    if state.inference_seeds:
        lines.append("")
        lines.append("Inference seeds (carry into next parallel pass):")
        for seed in state.inference_seeds:
            lines.append(f"- {seed}")
    lines.extend(
        [
            "",
            "Commands:",
            "- `python3 scripts/gate.py parallel-eval \"<query>\"`",
            "- `python3 scripts/memory.py retrieve \"<query>\" --json`",
            f"- Audited bypass: {BYPASS_TOKEN}",
        ]
    )
    return "\n".join(lines)
