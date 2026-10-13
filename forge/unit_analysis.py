# -*- coding: utf-8 -*-
"""forge.unit-analysis — dimensional-analysis task generator.

Problem: given an equation between physical quantities, decide whether it is
dimensionally consistent, and expose the dimension vector of each side.

Verification re-derives both dimension vectors from the quantity table in
problem["meta"] (never trusts answer["..._dims"]).
"""
from .common import make_id, pick, int_knob, knob

TYPE = "unit-analysis"

# base dimensions: M mass, L length, T time, K temperature, I current
TABLE = {
    "velocity":      {"L": 1, "T": -1},
    "acceleration":  {"L": 1, "T": -2},
    "force":         {"M": 1, "L": 1, "T": -2},
    "energy":        {"M": 1, "L": 2, "T": -2},
    "power":         {"M": 1, "L": 2, "T": -3},
    "pressure":      {"M": 1, "L": -1, "T": -2},
    "momentum":      {"M": 1, "L": 1, "T": -1},
    "frequency":     {"T": -1},
    "charge":        {"I": 1, "T": 1},
    "voltage":       {"M": 1, "L": 2, "T": -3, "I": -1},
    "density":       {"M": 1, "L": -3},
    "area":          {"L": 2},
    "volume":        {"L": 3},
    "time":          {"T": 1},
    "length":        {"L": 1},
    "mass":          {"M": 1},
    "temperature":   {"K": 1},
    "current":       {"I": 1},
    "specific-heat": {"L": 2, "T": -2, "K": -1},
    "force-constant": {"M": 1, "T": -2},
}


def dims_mul(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
        if out[k] == 0:
            del out[k]
    return out


def dims_pow(a, p):
    out = {k: v * p for k, v in a.items()}
    return {k: v for k, v in out.items() if v}


def dims_eq(a, b):
    ka = {k: v for k, v in a.items() if v}
    kb = {k: v for k, v in b.items() if v}
    return ka == kb


def dims_str(d):
    if not d:
        return "dimensionless"
    return " * ".join("%s^%d" % (k, v) for k, v in sorted(d.items()))


def generate(seed, difficulty=0.5):
    rng = __import__("random").Random("unit-analysis|%d" % seed)
    n_terms = int_knob(rng, difficulty, 2, 4)
    names = sorted(TABLE)
    lhs = pick(rng, names)
    # build rhs as product/quotient of n_terms quantities
    rhs = []
    for i in range(n_terms):
        name = pick(rng, names)
        sign = 1 if i == 0 or rng.random() < 0.55 else -1
        powr = 1
        if difficulty > 0.55 and rng.random() < 0.3:
            powr = 2 if rng.random() < 0.7 else -2
        rhs.append((name, sign, powr))
    # force the expression's actual consistency to match the target flag
    def _rhs_dims(expr_terms):
        d = {}
        for nm, sg, pw in expr_terms:
            d = dims_mul(d, dims_pow(TABLE[nm], sg * pw))
        return d

    target = rng.random() > knob(rng, difficulty, 0.55, 0.25)
    consistent = dims_eq(_rhs_dims(rhs), TABLE[lhs]) == target
    if not consistent:
        idx = rng.randrange(n_terms)
        name, sign, powr = rhs[idx]
        for delta in (1, -1, 2, -2, 3, -3):
            trial = rhs[:idx] + [(name, sign, powr + delta)] + rhs[idx + 1:]
            if dims_eq(_rhs_dims(trial), TABLE[lhs]) == target:
                rhs = trial
                break
        else:
            # deterministic fallback: lhs alone is consistent; lhs*lhs never is
            rhs = [(lhs, 1, 1)] if target else [(lhs, 1, 1), (lhs, 1, 1)]
    consistent = target
    lhs_d = dict(TABLE[lhs])
    rhs_d = {}
    for nm, sg, pw in rhs:
        rhs_d = dims_mul(rhs_d, dims_pow(TABLE[nm], sg * pw))
    # build readable expression with powers and division
    parts = []
    for i, (nm, sg, pw) in enumerate(rhs):
        core = nm if pw == 1 else "%s^%d" % (nm, pw)
        if i == 0:
            parts.append(core)
        else:
            parts.append(("* " if sg > 0 else "/ ") + core)
    expr = "".join(parts)

    problem = {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": ("A student writes the equation: %s = %s. Using dimensional "
                   "analysis (base dimensions M, L, T, K, I), is this equation "
                   "dimensionally consistent? Give the dimension vector of each "
                   "side." % (lhs, expr)),
        "answer": {
            "consistent": bool(consistent),
            "lhs_dims": lhs_d,
            "rhs_dims": rhs_d,
        },
        "solution": ("LHS [%s] = %s. RHS = %s. Therefore the equation is %s."
                     % (lhs, dims_str(lhs_d), dims_str(rhs_d),
                        "consistent" if consistent else "NOT consistent")),
        "meta": {"lhs": lhs, "rhs": [[nm, sg, pw] for nm, sg, pw in rhs]},
    }
    return problem


def verify(problem):
    """Re-derive both sides from meta + TABLE; compare with the claimed answer."""
    try:
        lhs = problem["meta"]["lhs"]
        if lhs not in TABLE:
            return False
        lhs_d = dict(TABLE[lhs])
        rhs_d = {}
        for nm, sg, pw in problem["meta"]["rhs"]:
            if nm not in TABLE:
                return False
            rhs_d = dims_mul(rhs_d, dims_pow(TABLE[nm], int(sg) * int(pw)))
        consistent = dims_eq(lhs_d, rhs_d)
        a = problem["answer"]
        return (bool(a["consistent"]) == consistent
                and dims_eq(a["lhs_dims"], lhs_d)
                and dims_eq(a["rhs_dims"], rhs_d))
    except (KeyError, TypeError, ValueError):
        return False


def self_cases():
    import copy
    cases = []
    for sd in range(5):
        cases.append(("gen-deterministic-%d" % sd,
                      lambda sd=sd: generate(sd, 0.5) == generate(sd, 0.5)))
    for d in (0.0, 0.25, 0.5, 0.75, 1.0):
        cases.append(("verify-true-d%.2f" % d,
                      lambda d=d: verify(generate(123 + int(d * 100), d))))
    base = generate(7, 0.5)
    for field, corrupt in (("consistent", lambda a: a.update(consistent=not a["consistent"])),
                           ("lhs_dims", lambda a: a["lhs_dims"].update({"M": 9})),
                           ("rhs_dims", lambda a: a["rhs_dims"].update({"Z": 1}))):
        p = copy.deepcopy(base)
        corrupt(p["answer"])
        cases.append(("verify-false-corrupt-%s" % field,
                      lambda p=p: verify(p) is False))
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("purity", lambda: dims_eq(dims_mul({"M": 1}, {"T": -1}), {"M": 1, "T": -1})))
    cases.append(("pow-zero", lambda: dims_pow({"M": 2}, 0) == {}))
    cases.append(("neg-power", lambda: dims_eq(dims_pow({"L": 2}, -1), {"L": -2})))

    from .common import schema_ok  # noqa: F401  (re-exported for readability)
    return cases
