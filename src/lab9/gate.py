"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = {m["id"] for m in spec["metrics"] if m["id"] in GRADERS}
    graded.update(s["metric"] for s in spec.get("slices", []) if s["metric"] in GRADERS)
    keys_of, tags_of = {}, {}
    for name, report in (("PR", pr), ("baseline", base)):
        manifest, rows = report.get("manifest", {}), report.get("rows", [])
        seeds = manifest.get("seeds", [])
        items = manifest.get("items", 0)
        if not seeds or len(seeds) != len(set(seeds)) or type(items) is not int or items <= 0:
            problems.append(f"{name}: invalid manifest")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator_failures present")
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        keys_of[name] = set(pairs)
        if len(rows) != items * len(seeds):
            problems.append(f"{name}: row count differs from manifest items x seeds")
        if len(pairs) != len(set(pairs)):
            problems.append(f"{name}: duplicate item/seed rows")
        item_ids = {p[0] for p in pairs}
        if len(item_ids) != items or set(pairs) != {(i, s) for i in item_ids for s in seeds}:
            problems.append(f"{name}: incomplete item/seed grid")
        tags = {}
        for row in rows:
            item = row.get("item_id")
            raw_tags = row.get("slices", [])
            if not isinstance(raw_tags, list) or any(not isinstance(t, str) for t in raw_tags):
                problems.append(f"{name}: invalid slice tags for {item}")
                continue
            tag = frozenset(raw_tags)
            if item in tags and tags[item] != tag:
                problems.append(f"{name}: inconsistent slice tags for {item}")
            tags[item] = tag
            for mid in graded:
                value = row.get(mid)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value not in (0, 1):
                    problems.append(f"{name}: invalid {mid} at {item}@{row.get('seed')}")
            for mid, value in row.items():
                if isinstance(value, (int, float)) and not math.isfinite(value):
                    problems.append(f"{name}: nonfinite row {mid}")
            if "cost" in row and (not isinstance(row["cost"], (int, float)) or row["cost"] < 0):
                problems.append(f"{name}: invalid row cost")
        tags_of[name] = tags
        for mid, value in report.get("metrics", {}).items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{name}: nonfinite or missing aggregate {mid}")
        for m in spec["metrics"]:
            if m["id"] not in report.get("metrics", {}):
                problems.append(f"{name}: missing aggregate {m['id']}")
        # Never trust a green aggregate that disagrees with the evidence rows.
        if not problems and rows:
            recomputed = {mid: (sum(r[mid] for r in rows) if mid in ("secret_leak", "approval_bypass")
                                else round(sum(r[mid] for r in rows) / len(rows), 4)) for mid in graded}
            if all("cost" in r for r in rows) and "pass_rate" in graded:
                recomputed.update(aggregate(rows, sorted(graded), k_values=spec.get("pass_k", [])))
            for mid, value in recomputed.items():
                if mid in report["metrics"] and report["metrics"][mid] != value:
                    problems.append(f"{name}: aggregate {mid} disagrees with rows")
    if keys_of["PR"] != keys_of["baseline"]:
        problems.append("PR item/seed set differs from baseline")
    if tags_of["PR"] != tags_of["baseline"]:
        problems.append("PR slice tags differ from baseline")

    if base_spec is not None and (spec.get("eval_set_version") == base_spec.get("eval_set_version")
                                 or pr.get("manifest", {}).get("eval_set_sha") == base.get("manifest", {}).get("eval_set_sha")):
        def ratchet(new_entries, old_entries, key, threshold_key):
            new = {key(entry): entry for entry in new_entries}
            for old in old_entries:
                identifier = key(old)
                if identifier not in new:
                    problems.append(f"ratchet: removed {identifier}")
                    continue
                current = new[identifier]
                if old.get("blocking") and not current.get("blocking"):
                    problems.append(f"ratchet: disabled blocking {identifier}")
                old_th = old.get(threshold_key, {}) if threshold_key else old
                new_th = current.get(threshold_key, {}) if threshold_key else current
                for th in ("min", "max", "max_increase", "no_significant_drop"):
                    if th not in old_th:
                        continue
                    if th not in new_th or (th == "min" and new_th[th] < old_th[th]) or (
                        th in ("max", "max_increase") and new_th[th] > old_th[th]) or (
                        th == "no_significant_drop" and old_th[th] and not new_th[th]):
                        problems.append(f"ratchet: loosened {identifier}/{th}")
        ratchet(spec["metrics"], base_spec["metrics"], lambda m: m["id"], "threshold")
        ratchet(spec.get("slices", []), base_spec.get("slices", []), lambda s: (s["name"], s["metric"]), None)
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        identifier = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        bad = not a or set(a) != set(b)
        note = "missing or unpaired slice" if bad else ""
        value = sum(a.values()) / len(a) if a else None
        if value is not None and "min" in entry and value < entry["min"]:
            bad = True
        if a and set(a) == set(b) and entry.get("no_significant_drop"):
            keys = sorted(a)
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            bad |= hi < 0
        if bad and entry.get("blocking"):
            blocked.append(identifier)
        verdict = ("BLOCK" if entry.get("blocking") else "warn") if bad else "ok"
        lines.append(f"  {identifier} {value} {note} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
