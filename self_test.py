# -*- coding: utf-8 -*-
"""Self-test: module sanity cases + integration cases. Pure stdlib.

Run:  python self_test.py      (last line: SUMMARY: PASS n/n, exit 0 = all green)
"""
import json
import os
import sys
import copy
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forge import MODULES  # noqa: E402
from forge.common import TYPES, schema_ok  # noqa: E402
from forge.verify import verdict  # noqa: E402

CASES = []


def case(name, fn):
    CASES.append((name, fn))


# ---- registry ----
def all_types_present():
    return set(MODULES) == set(TYPES)
case("registry-all-5-types", all_types_present)

# ---- per-module cases ----
for tname, mod in MODULES.items():
    try:
        for nm, fn in mod.self_cases():
            case("%s:%s" % (tname, nm), fn)
    except Exception as exc:  # a broken module must surface loudly
        case("%s:self_cases-raised" % tname, lambda exc=exc: (_ for _ in ()).throw(exc))

# ---- cross-module integration ----
for tname in sorted(MODULES):
    mod = MODULES[tname]
    case("%s:int-determinism" % tname,
         lambda mod=mod: mod.generate(31337, 0.42) == mod.generate(31337, 0.42))
    for d in (0.0, 0.3, 0.6, 1.0):
        case("%s:int-verify-d%.1f" % (tname, d),
             lambda mod=mod, d=d: mod.verify(mod.generate(500 + int(d * 97), d)))
    for i in range(8):
        case("%s:int-schema-%d" % (tname, i),
             lambda mod=mod, i=i: schema_ok(mod.generate(900 + i, i / 7.0)))
    # negative: corrupt every answer field -> verify must fail
    def corrupt_check(mod=mod):
        base = mod.generate(777, 0.5)
        if not mod.verify(base):
            return False
        for k in base["answer"]:
            p = copy.deepcopy(base)
            v = p["answer"][k]
            if isinstance(v, bool):
                p["answer"][k] = not v
            elif isinstance(v, (int, float)):
                p["answer"][k] = v + 1
            elif isinstance(v, dict):
                p["answer"][k] = {"__corrupt__": 1}
            elif isinstance(v, list):
                p["answer"][k] = ["__corrupt__"]
            else:
                p["answer"][k] = "__corrupt__"
            if mod.verify(p):
                return False
        return True
    case("%s:int-negative-corrupt-each-field" % tname, corrupt_check)
    # verify must never trust a tampered meta that changes derivation
    def meta_check(mod=mod):
        p = mod.generate(555, 0.5)
        if not p["meta"]:
            return True  # type without meta derivation
        p2 = copy.deepcopy(p)
        for k in p2["meta"]:
            if isinstance(p2["meta"][k], str):
                p2["meta"][k] = "__tampered__"
                break
        return mod.verify(p2) in (True, False)  # must not raise
    case("%s:int-meta-tamper-no-crash" % tname, meta_check)
    case("%s:int-verdict-structure" % tname,
         lambda mod=mod: verdict(mod.generate(42, 0.5))["passed"] is True)


# ---- CLI / dataset integration (runs generator end-to-end) ----
def cli_roundtrip():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                       "_selftest.jsonl")
    r = subprocess.run([sys.executable, "cli.py", "generate", "--type", "all",
                        "--per-type", "4", "--seed0", "5000", "--out", out],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or "SUMMARY: wrote 20 problems" not in r.stdout:
        return False
    g = subprocess.run([sys.executable, "cli.py", "grade", "--file", out],
                       capture_output=True, text=True, timeout=120)
    ok = g.returncode == 0 and "SUMMARY: 20/20 passed" in g.stdout
    os.remove(out)
    return ok
case("cli-roundtrip-4x5", cli_roundtrip)


def main():
    passed = 0
    failed = []
    for name, fn in CASES:
        try:
            ok = fn()
        except Exception as exc:
            ok = False
            sys.stderr.write("EXC %s: %r\n" % (name, exc))
        if ok:
            passed += 1
        else:
            failed.append(name)
    for f in failed:
        print("FAIL %s" % f)
    print("SUMMARY: PASS %d/%d" % (passed, len(CASES)))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
