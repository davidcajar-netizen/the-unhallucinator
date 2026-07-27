#!/usr/bin/env python3
"""LLM-Memory-Core: Parallel memory retrieval and creation for the Scepticism Engine.

This is the executable half of the memory system. The Scepticism Engine's Memory
Gate evaluates it concurrently with every token stream.

  * `retrieve` loads and scores all nodes in parallel. Linked memories are
    fetched concurrently. Confidence values are propagated through links.
    Exit code 0: local memory answered. Exit code 3: no local match.
  * `remember` (alias `ledger`) writes a new atomic `memN.md` node with YAML
    frontmatter when a durable insight is learned, auto-assigning the next number.

Only the Python standard library is used. No package manager. No dependencies.
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
                    current_link["file"] = file_match.group(1).strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                current_link[key.strip()] = value.strip()
        if current_link:
            links.append(current_link)
    return links

def _extract_frontmatter_certainty(fm: str) -> float:
    """Extract stored_certainty from frontmatter, defaulting to 0.5."""
    cert_str = _extract_frontmatter_field(fm, "stored_certainty")
    if cert_str:
        try:
            return float(cert_str)
        except ValueError:
            pass
    return DEFAULT_CERTAINTY

def _extract_frontmatter_created_at(fm: str) -> Optional[_dt.datetime]:
    """Extract created_at from frontmatter."""
    date_str = _extract_frontmatter_field(fm, "created_at")
    if date_str:
        try:
            return _dt.datetime.fromisoformat(date_str)
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
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    name = os.path.basename(path)
    mm = _MEM_FILE_RE.match(name)
    number = int(mm.group(1)) if mm else None

    tags = []
    links = []
    stored_certainty = DEFAULT_CERTAINTY
    created_at = None

    if text.startswith("---"):
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            tags = _extract_frontmatter_tags(fm)
            links = _extract_frontmatter_links(fm)
            stored_certainty = _extract_frontmatter_certainty(fm)
            created_at = _extract_frontmatter_created_at(fm)

    if not tags:
        tags = _extract_inline_tags(text)

    return Node(
        path=path,
        name=name,
        number=number,
        tags=tags,
        title=_extract_title(text),
        body=text,
        links=links,
        stored_certainty=stored_certainty,
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

def next_number(directory: str) -> int:
    highest = 0
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            mm = _MEM_FILE_RE.match(name)
            if mm:
                highest = max(highest, int(mm.group(1)))
    return highest + 1

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

def _recency_decay(created_at: Optional[_dt.datetime]) -> float:
    """Decay certainty based on age. Newer memories retain higher confidence."""
    if not created_at:
        return 0.5  # Unknown age -> maximum uncertainty
    age_days = (_dt.datetime.now() - created_at).days
    # Decay: 0% at 0 days, 50% at 30 days, asymptotic to 0
    decay = 1.0 / (1.0 + (age_days / 30.0))
    return decay

def _reevaluate_node(node: Node) -> tuple[Node, float]:
    """Continuous re-evaluation: apply recency decay.
    
    The script provides the raw stored_certainty adjusted for recency.
    The Engine's parallel evaluation field is responsible for detecting
    absolute claims and directional violations (semantic analysis).
    """
    adjusted_certainty = node.stored_certainty * _recency_decay(node.created_at)
    return node, adjusted_certainty

def _traverse_links_parallel(
    node: Node,
    all_nodes: dict[str, Node],
    visited: set,
    depth: int = 0,
    max_depth: int = 3,
) -> tuple[list[Node], float]:
    """Traverse links in parallel and compute combined certainty.
    
    Combined confidence for the cluster = minimum(stored_certainty_of_each_link),
    adjusted for Recency. Any link lacking stored certainty contributes 0.5.
    """
    if depth >= max_depth or node.name in visited:
        return [], node.stored_certainty

    visited.add(node.name)

    linked_nodes = []
    min_certainty = node.stored_certainty

    # Fetch all links at this depth concurrently
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
                min_certainty = min(min_certainty, deeper_cert)
            except Exception:
                pass

    return linked_nodes, min_certainty

def cmd_retrieve(args: argparse.Namespace) -> int:
    directory = nodes_dir(args.nodes_dir)
    required_tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    query_tokens = tokenize(args.query or "")

    all_nodes = load_nodes(directory)
    if not all_nodes:
        print(f"[memory] no local nodes found in {directory}")

    nodes_by_name = {node.name: node for node in all_nodes}

    scored = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(all_nodes)))) as executor:
        score_futures = {
            executor.submit(score_node, node, query_tokens, required_tags): node
            for node in all_nodes
        }

        reeval_futures = {
            executor.submit(_reevaluate_node, node): node
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
        for future in as_completed(reeval_futures):
            node = reeval_futures[future]
            try:
                _, adjusted_cert = future.result()
                certainties[node.name] = adjusted_cert
            except Exception as e:
                print(f"[memory] error re-evaluating {node.name}: {e}", file=sys.stderr)
                certainties[node.name] = DEFAULT_CERTAINTY

    for node in all_nodes:
        s, reason = scores.get(node.name, (0, ""))
        if s > 0:
            linked_nodes, cluster_certainty = _traverse_links_parallel(node, nodes_by_name, set())
            certainties[node.name] = min(
                certainties.get(node.name, DEFAULT_CERTAINTY),
                cluster_certainty,
            )

    for node in all_nodes:
        s, reason = scores.get(node.name, (0, ""))
        if s > 0:
            certainty = certainties.get(node.name, DEFAULT_CERTAINTY)
            scored.append((s, node, reason, certainty))

    scored.sort(key=lambda x: (-x[0], x[1].name))
    scored = scored[: args.limit]

    if not scored:
        print(f"[memory] no local match for {args.query!r} -> fall back to web search")
        return 3

    if args.json:
        results = []
        for s, node, reason, certainty in scored:
            results.append({
                "name": node.name,
                "title": node.title or "(untitled)",
                "tags": node.tags,
                "score": s,
                "reason": reason,
                "stored_certainty": node.stored_certainty,
                "adjusted_certainty": certainty,
                "body": node.body if args.show_body else None,
            })
        print(json.dumps({"results": results, "count": len(results)}, indent=2))
        return 0

    print(f"[memory] {len(scored)} local match(es) for {args.query!r} (search web only if insufficient):\n")
    for s, node, reason, certainty in scored:
        tags = ", ".join(node.tags) if node.tags else "(no tags)"
        print(f"  {node.name}  [score {s}]  [certainty {certainty:.2f}]  {reason}")
        print(f"    title: {node.title or '(untitled)'}")
        print(f"    tags:  {tags}")
        print(f"    certainty: {certainty:.2f} (stored: {node.stored_certainty:.2f})")
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

def build_node_markdown(
    title: str,
    tags: list[str],
    links: list[tuple[str, str]],
    content: str,
    certainty: float = DEFAULT_CERTAINTY,
) -> str:
    tag_line = "[" + ", ".join(tags) + "]" if tags else "[]"
    lines = ["---", f"tags: {tag_line}"]
    if links:
        lines.append("links:")
        for target, relation in links:
            lines.append(f"  - file: {target}")
            lines.append(f"    relation: {relation}")
    else:
        lines.append("links: []")
    lines.append(f"stored_certainty: {certainty}")
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
    certainty = args.certainty if args.certainty is not None else DEFAULT_CERTAINTY

    # Warn (do not block) if a node with the same title already exists
    for node in load_nodes(directory):
        if node.title.strip().lower() == args.title.strip().lower():
            print(f"[memory] warning: a node with this title already exists: {node.name}", file=sys.stderr)

    number = next_number(directory)
    filename = f"mem{number}.md"
    markdown = build_node_markdown(args.title, tags, links, content, certainty)

    if args.dry_run:
        print(f"[memory] dry-run: would write {filename}\n")
        print(markdown)
        return 0

    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(markdown)
    print(f"[memory] wrote {os.path.relpath(path, REPO_ROOT)} (tags: {', '.join(tags) or 'none'}, certainty: {certainty:.2f})")
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
        print(f"{node.name}: {node.title or '(untitled)'}  [{', '.join(node.tags)}]  [certainty: {node.stored_certainty:.2f}]")
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
        w.add_argument("--certainty", type=float, default=DEFAULT_CERTAINTY, help=f"stored certainty (default: {DEFAULT_CERTAINTY})")
        g = w.add_mutually_exclusive_group()
        g.add_argument("--content", help="node body text")
        g.add_argument("--content-file", help="read body from a file")
        w.add_argument("----dry-run", action="store_true", help="print instead of writing")
        w.set_defaults(func=cmd_remember)

    sub.add_parser("tags", help="list tags with counts").set_defaults(func=cmd_tags)
    sub.add_parser("list", help="list nodes with certainty").set_defaults(func=cmd_list)
    return p

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
