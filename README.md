# scireason-forge

Verifiable scientific-reasoning task generators — procedurally produced
problems whose every answer is re-derived and graded by deterministic
solvers (never by another language model).

Part of the [zhengming-toolbox](https://github.com/chenhz01/zhengming-toolbox)
suite. Planned three-piece release: **forge** (this repo — task generators +
solver grading), **bench** (independent eval of small models on these tasks),
and a solver-graded fine-tuning loop (train-before/after reports).

## Why

Reasoning-data pipelines are only as good as their grading. LLM-graded data
inherits the grader's biases; static benchmarks get contaminated. Every
problem here is generated procedurally with a difficulty knob, and every
answer is re-derived from the problem statement by closed-form solvers
(dimensional analysis, uncertainty propagation, unit conversion, graph
reachability, design-defect structure). Same seeds reproduce the same
problems byte-for-byte — contamination-proof by construction.

## Task types (W1: 5 types, 250 seed problems)

| Type | What it drills | Grading authority |
|---|---|---|
| `unit-analysis` | Dimensional consistency of equations | Base-dimension vector algebra |
| `error-propagation` | Measurement uncertainty (sum/product/power rules) | Closed-form propagation formulas |
| `experimental-design` | Control groups, confounders, blinding, sample size | Constructed-defect structure |
| `coordinate-convert` | SI prefixes, temperature scales, polar↔cartesian | Conversion tables / math |
| `citation-chain` | Retraction impact on a citation DAG | Reverse reachability + acyclicity |

## Quickstart

```bash
git clone https://github.com/chenhz01/scireason-forge
cd scireason-forge
python cli.py generate --type all --per-type 50 --seed0 1000 --out data/w1.jsonl
python cli.py grade --file data/w1.jsonl        # SUMMARY: 250/250 passed
python self_test.py                             # SUMMARY: PASS 167/167
```

Every generated line is a JSON problem: `prompt` (question), `answer`
(ground truth), `solution` (derivation trace), `meta` (construction truth
used by the grader to re-derive the answer independently).

## Verification principle

`verify(problem)` **never trusts** `problem["answer"]`. It re-derives the
answer from `problem["meta"]` and authoritative tables/formulas, then
compares. Corrupt any answer field and grading fails — this is the property
that makes the dataset safe as a reward signal (RLVR-style) and as a bench.

## When NOT to use

- You need open-ended natural-science questions with free-form prose answers
  (these tasks are closed-form by design).
- You need graduate-level research problems (W1 targets undergraduate-level
  reasoning primitives; harder mixes ship with the bench).

## License & contact

MIT — © zhengming contributors. Developer tooling, not professional advice.
Contact: hcac4735@agent.qq.com
