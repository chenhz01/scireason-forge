# -*- coding: utf-8 -*-
"""CLI: generate verifiable problems / grade a JSONL file.

    python cli.py generate --type all --per-type 50 --seed0 1000 --out data/w1.jsonl
    python cli.py grade --file data/w1.jsonl
"""
import argparse
import json
import os
import sys

from forge import MODULES
from forge.verify import grade_file


def _difficulty_for(i, n):
    """Deterministic spread of difficulties across [0, 1]."""
    if n <= 1:
        return 0.5
    return round((i % n) / float(n - 1), 3)


def cmd_generate(args):
    types = list(MODULES) if args.type == "all" else [args.type]
    for t in types:
        if t not in MODULES:
            print("unknown type: %s (have: %s)" % (t, ", ".join(sorted(MODULES))))
            return 2
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    n_rows = 0
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        for t in sorted(types):
            m = MODULES[t]
            for i in range(args.per_type):
                seed = args.seed0 + i + (100000 * sorted(MODULES).index(t))
                p = m.generate(seed, _difficulty_for(i, args.per_type))
                if not m.verify(p):
                    print("FAIL self-check at generation: %s seed=%d" % (t, seed))
                    return 3
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")
                n_rows += 1
    print("SUMMARY: wrote %d problems -> %s" % (n_rows, args.out))
    return 0


def cmd_grade(args):
    total, passed, failures = grade_file(args.file)
    for f in failures[:10]:
        print("FAIL %s (%s) %s" % (f["id"], f["type"], f["reason"]))
    print("SUMMARY: %d/%d passed, %d failed" % (passed, total, len(failures)))
    return 0 if passed == total else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="forge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--type", default="all")
    g.add_argument("--per-type", type=int, default=50)
    g.add_argument("--seed0", type=int, default=1000)
    g.add_argument("--out", required=True)
    g.set_defaults(fn=cmd_generate)
    d = sub.add_parser("grade")
    d.add_argument("--file", required=True)
    d.set_defaults(fn=cmd_grade)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
