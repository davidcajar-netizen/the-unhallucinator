#!/usr/bin/env python3
"""LLM-Memory-Core: Parallel memory retrieval and creation for the Scepticism Engine.

This is the executable half of the memory system. The Scepticism Engine's Memory
Gate evaluates it concurrently with every token stream.

  * `retrieve` loads and scores all nodes in parallel. Linked memories are
    fetched concurrently. Confidence values are propagated through links.
    Exit code 0: local memory answered. Exit code 3: no local match.
  * `remember` (alias `ledger`) writes a new atomic `memN.md` node with YAML
    frontmatter when a durable insight is learned, auto-assigning the next number.

Memory Types & Decay:
  * `conversation`: Epistemic certainty is permanent. Temporal salience (recall priority) 
    decays toward 0.5 over time. Verified doubt (<0.5) does not decay.
  * `observation`: Structural insight. No time decay.
  * `fact`: Verified data. No time decay. Certainty only drops if contradicting evidence is stored.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NODES_DIR = os.path.join(REPO_ROOT, "knowledge", "nodes")

_WORD_RE = re.compile(r"[a-z0-9]+")
_MEM_FILE_RE = re.compile(r"^mem(\d+)\.md$")

# Scoring weights: tags are the deliberate retrieval index.
TAG_WEIGHT = 5
TITLE_WEIGHT = 3
BODY_WEIGHT = 1

# Default certainty for memories lacking an explicit stored_certainty.
DEFAULT_CERTAINTY = 0.5
DEFAULT_TYPE = "observation"
MAX_STORED_CERTAINTY = 0.99  # Absolute certainty (1.0) is a structural violation.

def nodes_dir(explicit: str | None = None) -> str:
    return explicit or os.environ.get("MEMORY_NODES_DIR") or DEFAULT_NODES_DIR

def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())

@dataclass
class Node:
    path: str
    name: str
    number: int | None
    tags: list[str] = field(default_factory=list)
    title: str = ""
    body: str = ""
    links: list[dict] = field(default_factory=list)
    stored_certainty: float = DEFAULT_CERTAINTY
    memory_type: str = DEFAULT_TYPE
    created_at: Optional[_dt.datetime] = None
    raw_text: str = ""

    @property
    def tag_tokens(self) -> set[str]:
        toks: set[str] = set()
        for tag in self.tags:
            toks.update(tokenize(tag))
        return toks

def _extract_frontmatter_field(fm: str, field_name: str) -> Optional[str]:
    """Extract a simple field from YAML frontmatter."""
    pattern = rf"^{field_name}:\s*(.*)$"
    m = re.search(pattern, fm, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None

def _extract_frontmatter_tags(fm: str) -> list[str]:
    """Read tags from YAML frontmatter (`tags: [..]` or a block list)."""
    inline = re.search(r"^tags:\s*\[(.*?)\]", fm, re.MULTILINE | re.DOTALL)
    if inline:
        return [t.strip().strip("'\"") for t in inline.group(1).split(",") if t.strip()]
    block = re.search(r"^tags:\s*\n((?:\s*-\s*.+\n?)+)", fm, re.MULTILINE)
    if block:
        return [
            line.strip()[1:].strip().strip("'\"")
            for line in block.group(1).splitlines()
            if line.strip().startswith("-")
        ]
    return []

def _extract_frontmatter_links(fm: str) -> list[dict]:
    """Read links from YAML frontmatter."""
    links = []
    block = re.search(r"^links:\s*\n((?:\s*-\s*.+\n?(?:\s+\w+:\s*.+\n?)*))+", fm, re.MULTILINE)
    if block:
        current_link = {}
        for line in block.group(1).splitlines():
            line = line.strip()
            if line.startswith("-"):
                if current_link:
                    links.append(current_link)
                current_link = {}
                file_match = re.search(r"file:\s*(\S+)", line)
                if file_match:
                    current_link["file"] = file_match.group(1).strip().strip("'\"")
            elif ":" in line:
                key, value = line.split(":", 1)
                current_link[key.strip()] = value.strip().strip("'\"")
        if current_link:
            links.append(current_link)
    return links

def _extract_frontmatter_certainty(fm: str) -> float:
    """Extract stored_certainty from frontmatter, defaulting to 0.5. Caps at 0.99."""
    cert_str = _extract_frontmatter_field(fm, "stored_certainty")
    if cert_str:
        try:
            val = float(cert_str)
            # Prevent absolute certainty backdoor
            return min(val, MAX_STORED_CERTAINTY)
        except ValueError:
            pass
    return DEFAULT_CERTAINTY

def _extract_frontmatter_type(fm: str) -> str:
    """Extract memory_type from frontmatter, defaulting to observation."""
    type_str = _extract_frontmatter_field(fm, "memory_type")
    if type_str:
        return type_str.strip("'\"").lower()
    return DEFAULT_TYPE

def _extract_frontmatter_created_at(fm: str) -> Optional[_dt.datetime]:
    """Extract created_at from frontmatter."""
    date_str = _extract_frontmatter_field(fm, "created_at")
    if date_str:
        try:
            return _dt.datetime.fromisoformat(date_str.strip("'\""))
        except ValueError:
            pass
    return None

def _extract_inline_tags(text: str) -> list[str]:
    """Read tags from the inline `**Tags:** #a #b` style used by newer nodes."""
    m = re.search(r"^\*\*Tags:\*\*\s*(.+)$", text, re.MULTILINE)
    if not m:
        return []
    return [t.lstrip("#") for t in m.group(1).split() if t.strip()]

def _extract_title(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return ""

def load_node(path: str) -> Node:
    """Load a node, catching frontmatter corruption to prevent system crash."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    name = os.path.basename(path)
    mm = _MEM_FILE_RE.match(name)
    number = int(mm.group(1)) if mm else None

    tags = []
    links = []
    stored_certainty = DEFAULT_CERTAINTY
    memory_type = DEFAULT_TYPE
    created_at = None

    if text.startswith("---"):
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            try:
                tags = _extract_frontmatter_tags(fm)
                links = _extract_frontmatter_links(fm)
                stored_certainty = _extract_frontmatter_certainty(fm)
                memory_type = _extract_frontmatter_type(fm)
                created_at = _extract_frontmatter_created_at(fm)
            except Exception:
                # If frontmatter is corrupted, defaults are kept. Node is not lost.
                pass

    if not tags:
        try:
            tags = _extract_inline_tags(text)
        except Exception:
            pass

    return Node(
        path=path,
        name=name,
        number=number,
        tags=tags,
        title=_extract_title(text),
        body=text,
        links=links,
        stored_certainty=stored_certainty,
        memory_type=memory_type,
        created_at=created_at,
        raw_text=text,
    )

def load_nodes(directory: str) -> list[Node]:
    """Load all nodes in parallel using ThreadPoolExecutor."""
    if not os.path.isdir(directory):
        return []

    files = []
    for name in sorted(os.listdir(directory)):
        if name.endswith(".md"):
            files.append(os.path.join(directory, name))

    nodes = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(files)))) as executor:
        future_to_path = {executor.submit(load_node, path): path for path in files}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                node = future.result()
                nodes.append(node)
            except Exception as e:
                print(f"[memory] error loading {path}: {e}", file=sys.stderr)

    nodes.sort(key=lambda n: n.name)
    return nodes

def _claim_next_number(directory: str) -> int:
    """Atomically claim the next memory file number to prevent race conditions."""
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
        return 1

    highest = 0
    for name in os.listdir(directory):
        mm = _MEM_FILE_RE.match(name)
        if mm:
            highest = max(highest, int(mm.group(1)))

    # Try to claim the next number atomically
    while True:
        next_num = highest + 1
        filename = f"mem{next_num}.md"
        path = os.path.join(directory, filename)
        try:
            # O_CREAT | O_EXCL fails if the file already exists
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return next_num
        except FileExistsError:
            highest = next_num
        except Exception as e:
            print(f"[memory] error claiming next number: {e}", file=sys.stderr)
            return next_num  # Fallback

def score_node(node: Node, query_tokens: list[str], required_tags: list[str]) -> tuple[int, str]:
    """Score a node against query tokens and required tags."""
    if required_tags:
        node_tags_lower = {t.lower() for t in node.tags}
        required_lower = {rt.lower() for rt in required_tags}
        if not required_lower.issubset(node_tags_lower):
            return 0, ""

    qset = set(query_tokens)
    if not qset and required_tags:
        return TAG_WEIGHT, "matched required tags"

    body_tokens = set(tokenize(node.body))
    title_tokens = set(tokenize(node.title))
    tag_tokens = node.tag_tokens

    score = 0
    hit_terms = []
    for tok in qset:
        if tok in tag_tokens:
            score += TAG_WEIGHT
            hit_terms.append(tok)
        elif tok in title_tokens:
            score += TITLE_WEIGHT
            hit_terms.append(tok)
        elif tok in body_tokens:
            score += BODY_WEIGHT
            hit_terms.append(tok)

    reason = "matched: " + ", ".join(sorted(set(hit_terms))) if hit_terms else ""
    return score, reason

def _evaluate_salience(node: Node) -> tuple[Node, float, float]:
    """Evaluate epistemic certainty and temporal salience.
    
    Epistemic Certainty (stored_certainty) is permanent. It does not decay.
    Temporal Salience decays over time for conversations, representing reduced recall priority.
    Observations and Facts maintain maximum salience.
    """
    is_legacy = not node.raw_text.startswith("---")
    
    if is_legacy:
        return node, 0.5, 0.5  # Unverified legacy, low salience

    if node.memory_type == "conversation":
        if not node.created_at:
            return node, node.stored_certainty, 0.5
        
        age_days = (_dt.datetime.now() - node.created_at).days
        
        # Verified doubt is stable. It does not decay toward uncertainty.
        if node.stored_certainty < 0.5:
            return node, node.stored_certainty, node.stored_certainty
            
        # Positive certainty decays toward 0.5 (baseline recall priority), asymptotic to 0.5, never below.
        decay = 1.0 / (1.0 + (age_days / 30.0))
        salience = 0.5 + ((node.stored_certainty - 0.5) * decay)
        return node, node.stored_certainty, salience
    
    # Observations and Facts: no time decay, maximum salience
    return node, node.stored_certainty, node.stored_certainty

def _traverse_links_parallel(
    node: Node,
    all_nodes: dict[str, Node],
    visited: set,
    depth: int = 0,
    max_depth: int = 3,
) -> tuple[list[Node], float]:
    """Traverse links concurrently and compute combined certainty.
    
    Combined confidence for the cluster = minimum(stored_certainty_of_each_link),
    adjusted for Recency. Any link lacking stored certainty contributes 0.5.
    Directional lock is applied at the Engine level, not here.
    """
    if depth >= max_depth or node.name in visited:
        return [], node.stored_certainty

    visited.add(node.name)

    linked_nodes = []
    min_certainty = node.stored_certainty

    if not node.links:
        return linked_nodes, min_certainty

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(node.links)))) as executor:
        futures = {}
        for link in node.links:
            target_file = link.get("file", "")
            if not target_file.endswith(".md"):
                target_file += ".md"
            target_node = all_nodes.get(target_file)
            if target_node and target_node.name not in visited:
                futures[executor.submit(_traverse_links_parallel, target_node, all_nodes, visited, depth + 1, max_depth)] = target_node

        for future in as_completed(futures):
            target_node = futures[future]
            try:
                deeper_nodes, deeper_cert = future.result()
                linked_nodes.extend(deeper_nodes)
                # Apply recency adjustment to the linked node's certainty
                _, epistemic_cert, _ = _evaluate_salience(target_node)
                min_certainty = min(min_certainty, epistemic_cert, deeper_cert)
            except Exception:
                # If traversal fails, contribute 0.5 (unverified)
                min_certainty = min(min_certainty, 0.5)

    return linked_nodes, min_certainty

def cmd_retrieve(args: argparse.Namespace) -> int:
    directory = nodes_dir(args.nodes_dir)
    required_tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    query_tokens = tokenize(args.query or "")

    all_nodes = load_nodes(directory)
    if not all_nodes:
        print(f"[memory] no local nodes found in {directory}")

    nodes_by_name = {node.name: node for node in all_nodes}

    # Concurrent evaluation: scoring, certainty, and link traversal in one parallel block
    scored = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(all_nodes)))) as executor:
        score_futures = {
            executor.submit(score_node, node, query_tokens, required_tags): node
            for node in all_nodes
        }

        eval_futures = {
            executor.submit(_evaluate_salience, node): node
            for node in all_nodes
        }

        link_futures = {
            executor.submit(_traverse_links_parallel, node, nodes_by_name, set()): node
            for node in all_nodes
        }

        scores = {}
        for future in as_completed(score_futures):
            node = score_futures[future]
            try:
                s, reason = future.result()
                scores[node.name] = (s, reason)
            except Exception as e:
                print(f"[memory] error scoring {node.name}: {e}", file=sys.stderr)
                scores[node.name] = (0, "")

        certainties = {}
        saliences = {}
        for future in as_completed(eval_futures):
            node = eval_futures[future]
            try:
                _, epistemic_cert, salience = future.result()
                certainties[node.name] = epistemic_cert
                saliences[node.name] = salience
            except Exception as e:
                print(f"[memory] error evaluating {node.name}: {e}", file=sys.stderr)
                certainties[node.name] = DEFAULT_CERTAINTY
                saliences[node.name] = DEFAULT_CERTAINTY

        link_results = {}
        for future in as_completed(link_futures):
            node = link_futures[future]
            try:
                linked_nodes, cluster_certainty = future.result()
                link_results[node.name] = cluster_certainty
            except Exception:
                link_results[node.name] = DEFAULT_CERTAINTY

    # Apply link cluster certainty (minimum of node certainty and link cluster certainty)
    for node in all_nodes:
        s, reason = scores.get(node.name, (0, ""))
        if s > 0:
            cluster_cert = link_results.get(node.name, DEFAULT_CERTAINTY)
            certainties[node.name] = min(
                certainties.get(node.name, DEFAULT_CERTAINTY),
                cluster_cert,
            )

    for node in all_nodes:
        s, reason = scores.get(node.name, (0, ""))
        if s > 0:
            certainty = certainties.get(node.name, DEFAULT_CERTAINTY)
            salience = saliences.get(node.name, DEFAULT_CERTAINTY)
            scored.append((s, node, reason, certainty, salience))

    scored.sort(key=lambda x: (-x[0], x[1].name))
    scored = scored[: args.limit]

    if not scored:
        print(f"[memory] no local match for {args.query!r} -> fall back to web search")
        return 3

    if args.json:
        results = []
        for s, node, reason, certainty, salience in scored:
            results.append({
                "name": node.name,
                "title": node.title or "(untitled)",
                "tags": node.tags,
                "score": s,
                "reason": reason,
                "memory_type": node.memory_type,
                "stored_certainty": node.stored_certainty,
                "epistemic_certainty": certainty,
                "salience": salience,
                "body": node.body if args.show_body else None,
            })
        print(json.dumps({"results": results, "count": len(results)}, indent=2))
        return 0

    # Verdict-based output for the Engine
    print(f"[memory] {len(scored)} local match(es) for {args.query!r}:\n")
    for s, node, reason, certainty, salience in scored:
        tags = ", ".join(node.tags) if node.tags else "(no tags)"
        print(f"  {node.name}  [score {s}]  [cert {certainty:.2f}]  [salience {salience:.2f}]  {reason}")
        print(f"    title: {node.title or '(untitled)'}")
        print(f"    type:  {node.memory_type}")
        print(f"    tags:  {tags}")
        print(f"    certainty: {certainty:.2f} (stored: {node.stored_certainty:.2f}) | salience: {salience:.2f}")
        if args.show_body:
            print("    ---")
            for line in node.body.splitlines():
                print(f"    {line}")
            print("    ---")
        print()
    return 0

def _read_content(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.content_file:
        with open(args.content_file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""

def _sanitize_yaml_string(s: str) -> str:
    """Sanitize a string for safe YAML embedding."""
    s = s.strip().strip("'\"")
    s = s.replace("'", "''")  # YAML escape for single quotes
    return f"'{s}'"

def build_node_markdown(
    title: str,
    tags: list[str],
    links: list[tuple[str, str]],
    content: str,
    certainty: float = DEFAULT_CERTAINTY,
    memory_type: str = DEFAULT_TYPE,
) -> str:
    # Sanitize tags for YAML safety
    safe_tags = [_sanitize_yaml_string(t) for t in tags]
    tag_line = "[" + ", ".join(safe_tags) + "]" if safe_tags else "[]"
    lines = ["---", f"tags: {tag_line}"]
    if links:
        lines.append("links:")
        for target, relation in links:
            safe_target = _sanitize_yaml_string(target)
            safe_relation = _sanitize_yaml_string(relation)
            lines.append(f"  - file: {safe_target}")
            lines.append(f"    relation: {safe_relation}")
    else:
        lines.append("links: []")
    lines.append(f"stored_certainty: {certainty}")
    lines.append(f"memory_type: {memory_type}")
    lines.append(f"created_at: {_dt.datetime.now().isoformat()}")
    lines.append("---")
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")
    lines.append(content.strip())
    lines.append("")
    return "\n".join(lines)

def _parse_links(raw_links: list[str]) -> list[tuple[str, str]]:
    parsed = []
    for item in raw_links or []:
        if ":" in item:
            target, relation = item.split(":", 1)
        else:
            target, relation = item, "related"
        target = target.strip()
        if not target.endswith(".md"):
            target += ".md"
        parsed.append((target, relation.strip() or "related"))
    return parsed

def cmd_remember(args: argparse.Namespace) -> int:
    directory = nodes_dir(args.nodes_dir)
    content = _read_content(args).strip()
    if not args.title:
        print("[memory] error: --title is required", file=sys.stderr)
        return 2
    if not content:
        print("[memory] error: no content (use --content, --content-file, or stdin)", file=sys.stderr)
        return 2

    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    links = _parse_links(args.link)
    
    # Anti-Certainty Backdoor fix: Cap stored certainty at 0.99. Absolute certainty is a structural violation.
    certainty = min(args.certainty, MAX_STORED_CERTAINTY) if args.certainty is not None else DEFAULT_CERTAINTY
    mem_type = args.type if args.type else DEFAULT_TYPE

    # Warn (do not block) if a node with the same title already exists
    for node in load_nodes(directory):
        if node.title.strip().lower() == args.title.strip().lower():
            print(f"[memory] warning: a node with this title already exists: {node.name}", file=sys.stderr)

    number = _claim_next_number(directory)
    filename = f"mem{number}.md"
    markdown = build_node_markdown(args.title, tags, links, content, certainty, mem_type)

    if args.dry_run:
        print(f"[memory] dry-run: would write {filename}\n")
        print(markdown)
        return 0

    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(markdown)
    print(f"[memory] wrote {os.path.relpath(path, REPO_ROOT)} (type: {mem_type}, tags: {', '.join(tags) or 'none'}, certainty: {certainty:.2f})")
    return 0

def cmd_tags(args: argparse.Namespace) -> int:
    directory = nodes_dir(args.nodes_dir)
    counts: dict[str, int] = {}
    for node in load_nodes(directory):
        for tag in node.tags:
            counts[tag] = counts.get(tag, 0) + 1
    for tag, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"{n:3d}  {tag}")
    return 0

def cmd_list(args: argparse.Namespace) -> int:
    directory = nodes_dir(args.nodes_dir)
    for node in load_nodes(directory):
        print(f"{node.name}: {node.title or '(untitled)'}  [{', '.join(node.tags)}]  [type: {node.memory_type}]  [cert: {node.stored_certainty:.2f}]")
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="memory", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--nodes-dir", help="override knowledge/nodes directory (also MEMORY_NODES_DIR)")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("retrieve", help="parallel local-first search; run BEFORE web search")
    r.add_argument("query", nargs="?", default="", help="free-text query")
    r.add_argument("--tags", help="comma-separated tags that MUST all be present")
    r.add_argument("--limit", type=int, default=5)
    r.add_argument("--show-body", action="store_true", help="print full node body")
    r.add_argument("--json", action="store_true", help="output results as JSON for concurrent parsing")
    r.set_defaults(func=cmd_retrieve)

    for alias in ("remember", "ledger"):
        w = sub.add_parser(alias, help="create the next memN.md node")
        w.add_argument("--title", required=True)
        w.add_argument("--tags", help="comma-separated tags")
        w.add_argument("--link", action="append", help="link as memX or memX:relation (repeatable)")
        w.add_argument("--certainty", type=float, default=DEFAULT_CERTAINTY, help=f"stored certainty (default: {DEFAULT_CERTAINTY}, max: {MAX_STORED_CERTAINTY})")
        w.add_argument("--type", default=DEFAULT_TYPE, choices=["conversation", "observation", "fact"], help=f"memory type (default: {DEFAULT_TYPE})")
        g = w.add_mutually_exclusive_group()
        g.add_argument("--content", help="node body text")
        g.add_argument("--content-file", help="read body from a file")
        w.add_argument("--dry-run", action="store_true", help="print instead of writing")
        w.set_defaults(func=cmd_remember)

    sub.add_parser("tags", help="list tags with counts").set_defaults(func=cmd_tags)
    sub.add_parser("list", help="list nodes with certainty").set_defaults(func=cmd_list)
    return p

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
