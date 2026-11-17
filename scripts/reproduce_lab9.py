"""Rebuild the individual Day09 submission from the instructor's original host."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    (SRC / "reports").mkdir(exist_ok=True)
    log = []

    def run(module, *args, expected=0, contains=None):
        command = [sys.executable, "-m", module, *args]
        title = "python -m " + " ".join([module, *args])
        print(f"\n$ {title}", flush=True)
        result = subprocess.run(command, cwd=SRC, env={**os.environ, "PYTHONUTF8": "1"},
                                capture_output=True, text=True, encoding="utf-8")
        output = result.stdout + result.stderr
        print(output, end="", flush=True)
        log.append(f"$ {title}\n{output}process exit {result.returncode}\n")
        clean = "\n".join(line.rstrip() for line in "\n".join(log).splitlines())
        (SRC / "reports/lab9_validation.log").write_text(clean + "\n", encoding="utf-8", newline="\n")
        if result.returncode != expected or (contains and contains not in output):
            raise RuntimeError(f"{title}: expected exit {expected}, got {result.returncode}")

    if sys.argv[1:] == ["--documents-only"]:
        previous = SRC / "reports/lab9_validation.log"
        log.append(previous.read_text(encoding="utf-8").rstrip())
        if "mutation score 3/3" not in log[0]:
            raise RuntimeError("Run the full evaluation before generating documents")
        run("lab9.evidence")
        return

    run("lab9.provenance", "--check")
    run("lab9.smoke")
    run("lab9.evalset", "--build", "--check")
    run("lab9.evalset", "--v2", "--build")
    run("pytest", "-q")
    # Day08 workflow/single/orchestrator are intentionally untouched starter stubs.
    run("pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9")
    run("lab9.judge", "--csv", "data/eval/judge_tone_public.csv", "--audit", "5")
    run("lab9.judge", "--csv", "data/eval/judge_helpful_public.csv", "--audit", "5",
        expected=1, contains="FAIL floors")
    for spec, suffix in (("config/metric_spec.yaml", "v1"), ("config/metric_spec_v2.yaml", "v2")):
        base = f"reports/baseline_{suffix}.json"
        run("lab9.eval", "--shape", "swarm", "--spec", spec, "--out", base)
        run("lab9.gate", "--pr", base, "--baseline", base, "--spec", spec, "--base-spec", spec)
        for shape in ("fixed", "seeded_regression"):
            report = f"reports/eval_{shape}.json" if suffix == "v1" else f"reports/eval_{shape}_v2.json"
            run("lab9.eval", "--shape", shape, "--spec", spec, "--out", report)
            run("lab9.gate", "--pr", report, "--baseline", base, "--spec", spec, "--base-spec", spec,
                expected=int(shape == "seeded_regression"),
                contains="pass_rate" if shape == "seeded_regression" else "exit 0")
        if suffix == "v1":
            run("lab9.ci_check", "--pr", base, "--baseline", base, "--spec", spec)
    run("lab9.mutation", "--detect", contains="detection 100.00%")
    spec, base = "config/metric_spec_v2.yaml", "reports/baseline_v2.json"
    run("lab9.mutation", "--spec", spec, "--aa", "66,77,88,99,110")
    run("lab9.mutation", "--spec", spec, "--baseline", base, "--base-spec", spec,
        contains="mutation score 3/3")
    run("lab9.eval", "--shape", "slice_regression", "--spec", spec, "--out", "reports/eval_slice_regression.json")
    run("lab9.traps", "--pr", "reports/eval_slice_regression.json", "--baseline", base, "--spec", spec)
    for trap in ("evaluator_errors_as_nan", "dropped_failing_rows", "cherry_picked_seeds", "loosened_spec"):
        trap_spec = f"reports/traps/{trap}.spec.yaml" if trap == "loosened_spec" else spec
        run("lab9.gate", "--pr", f"reports/traps/{trap}.json", "--baseline", base,
            "--spec", trap_spec, "--base-spec", spec, expected=1, contains="INTEGRITY")
    run("lab9.evidence")
    print("\nIndividual Day09 reproduction PASS.")


if __name__ == "__main__":
    main()
