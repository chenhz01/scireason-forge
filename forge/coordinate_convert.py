# -*- coding: utf-8 -*-
"""forge.coordinate-convert — unit conversion & coordinate transform generator.

Three sub-kinds, selected by a difficulty-weighted RNG draw:
    si     -- SI-prefix conversion (k/M/G/m/u/n), factor 10^n
    temp   -- temperature conversion (degC <-> K <-> degF)
    polar  -- polar (r, theta) -> Cartesian (x, y) on special angles

Verification re-derives the answer from problem["meta"] (kind, input values,
conversion factors / formulas) and never trusts problem["answer"].  Both the
generated answer and the re-derived expectation are rounded to 4 significant
digits with the same helper so the comparison is deterministic.
"""
import math
import random

from .common import make_id, pick, schema_ok

TYPE = "coordinate-convert"

# SI prefixes: internal symbol -> power of ten ("u" is rendered as micro sign)
PREFIX_EXP = {"k": 3, "M": 6, "G": 9, "m": -3, "u": -6, "n": -9}
PREFIX_ORDER = ("k", "M", "G", "m", "u", "n")
_DISPLAY = {"u": "µ"}
_BASE_UNITS = ("m", "g", "s")
_SPECIAL_DEG = (0, 30, 45, 60, 90, 120, 135, 150, 180)

_TEMP_NAME = {"C": "°C", "K": "K", "F": "°F"}
_TEMP_FORMULA = {
    ("C", "K"): "T_K = T_C + 273.15",
    ("K", "C"): "T_C = T_K - 273.15",
    ("C", "F"): "T_F = T_C * 9/5 + 32",
    ("F", "C"): "T_C = (T_F - 32) * 5/9",
    ("K", "F"): "T_F = (T_K - 273.15) * 9/5 + 32",
    ("F", "K"): "T_K = (T_F - 32) * 5/9 + 273.15",
}


def sym(prefix):
    """Display symbol for an internal prefix key."""
    return _DISPLAY.get(prefix, prefix)


def sig4(x):
    """Round to 4 significant digits (applied identically on both sides)."""
    x = float(x)
    if x == 0.0 or math.isnan(x) or math.isinf(x):
        return x
    exp = math.floor(math.log10(abs(x)))
    return round(x, 3 - int(exp))


def fmt(x):
    return "%g" % float(x)


def si_convert(value, src_exp, dst_exp):
    """Scale value from a 10^src_exp prefix to a 10^dst_exp prefix."""
    return value * (10.0 ** (int(dst_exp) - int(src_exp)))


def temp_convert(value, src, dst):
    """Convert temperature via Celsius as the pivot scale."""
    if src == "C":
        c = value
    elif src == "K":
        c = value - 273.15
    elif src == "F":
        c = (value - 32.0) * 5.0 / 9.0
    else:
        raise ValueError("unknown temperature unit: %r" % (src,))
    if dst == "C":
        return c
    if dst == "K":
        return c + 273.15
    if dst == "F":
        return c * 9.0 / 5.0 + 32.0
    raise ValueError("unknown temperature unit: %r" % (dst,))


def polar_xy(r, deg):
    """Polar (r, deg) -> Cartesian (x, y)."""
    t = math.radians(deg)
    return r * math.cos(t), r * math.sin(t)


def _close(a, b):
    return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))


def _gen_si(rng, seed, difficulty):
    base = pick(rng, _BASE_UNITS)
    src = pick(rng, PREFIX_ORDER)
    dst = pick(rng, PREFIX_ORDER)
    if difficulty >= 0.5:
        # hard mode: force a multi-step prefix chain (large exponent gap)
        for _ in range(16):
            if abs(PREFIX_EXP[dst] - PREFIX_EXP[src]) >= 6:
                break
            dst = pick(rng, PREFIX_ORDER)
    if difficulty < 0.5:
        value = float(rng.randint(1, 99))
    else:
        value = round(rng.uniform(0.1, 999.9), 2)
    src_u, dst_u = sym(src) + base, sym(dst) + base
    e_src, e_dst = PREFIX_EXP[src], PREFIX_EXP[dst]
    raw = si_convert(value, e_src, e_dst)
    prompt = ("Convert %s %s to %s. (Conversion factors: 1 %s = 10^%d %s, "
              "1 %s = 10^%d %s.)"
              % (fmt(value), src_u, dst_u, src_u, e_src, base, dst_u, e_dst, base))
    solution = ("%s %s = %s %s, since 1 %s = 10^(%d - (%d)) %s = 10^%d %s. "
                "Stepping through the base unit: %s -> %s (x10^%d), then "
                "%s -> %s (x10^%d)."
                % (fmt(value), src_u, fmt(sig4(raw)), dst_u, dst_u,
                   e_dst, e_src, base, e_dst - e_src, base,
                   src_u, base, -e_src, base, dst_u, e_dst))
    problem = {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"kind": "si", "value": sig4(raw)},
        "solution": solution,
        "meta": {"kind": "si", "value": value, "src": src, "dst": dst,
                 "src_exp": e_src, "dst_exp": e_dst, "base": base},
    }
    return problem


def _gen_temp(rng, seed, difficulty):
    units = ("C", "K", "F")
    src = pick(rng, units)
    dst = pick(rng, units)
    while dst == src:
        dst = pick(rng, units)
    if difficulty < 0.5:
        value = float(rng.randint(-40, 120))
    else:
        value = round(rng.uniform(-40.0, 120.0), 1)
    raw = temp_convert(value, src, dst)
    formula = _TEMP_FORMULA[(src, dst)]
    prompt = ("Convert %s %s to %s. (Formula: %s.)"
              % (fmt(value), _TEMP_NAME[src], _TEMP_NAME[dst], formula))
    solution = ("Applying %s: %s %s = %s %s."
                % (formula, fmt(value), _TEMP_NAME[src],
                   fmt(sig4(raw)), _TEMP_NAME[dst]))
    problem = {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"kind": "temp", "value": sig4(raw)},
        "solution": solution,
        "meta": {"kind": "temp", "value": value, "src": src, "dst": dst},
    }
    return problem


def _gen_polar(rng, seed, difficulty):
    deg = pick(rng, _SPECIAL_DEG)
    if difficulty < 0.5:
        r = float(rng.randint(1, 20))
    else:
        r = round(rng.uniform(0.5, 20.0), 2)
    x, y = polar_xy(r, deg)
    prompt = ("A point has polar coordinates (r, theta) = (%s, %d deg). "
              "Compute its Cartesian coordinates (x, y), where x = r*cos(theta) "
              "and y = r*sin(theta)." % (fmt(r), deg))
    solution = ("x = %s*cos(%d deg) = %s and y = %s*sin(%d deg) = %s."
                % (fmt(r), deg, fmt(sig4(x)), fmt(r), deg, fmt(sig4(y))))
    problem = {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"kind": "polar", "x": sig4(x), "y": sig4(y)},
        "solution": solution,
        "meta": {"kind": "polar", "r": r, "deg": deg},
    }
    return problem


def generate(seed, difficulty=0.5):
    rng = random.Random("coordinate-convert|%d" % seed)
    difficulty = min(max(float(difficulty), 0.0), 1.0)
    # difficulty-weighted sub-kind selection (deterministic draw)
    weights = (("si", 1.0),
               ("temp", 0.8 + 0.6 * difficulty),
               ("polar", 1.2 - 0.4 * difficulty))
    r = rng.random() * sum(w for _, w in weights)
    acc = 0.0
    kind = weights[-1][0]
    for k, w in weights:
        acc += w
        if r < acc:
            kind = k
            break
    if kind == "si":
        return _gen_si(rng, seed, difficulty)
    if kind == "temp":
        return _gen_temp(rng, seed, difficulty)
    return _gen_polar(rng, seed, difficulty)


def verify(problem):
    """Re-derive the answer from meta (factors/formulas); ignore answer values."""
    try:
        meta = problem["meta"]
        ans = problem["answer"]
        kind = meta["kind"]
        if kind == "si":
            raw = si_convert(float(meta["value"]),
                             int(meta["src_exp"]), int(meta["dst_exp"]))
            return (ans.get("kind") == "si"
                    and _close(ans["value"], sig4(raw)))
        if kind == "temp":
            raw = temp_convert(float(meta["value"]), meta["src"], meta["dst"])
            return (ans.get("kind") == "temp"
                    and _close(ans["value"], sig4(raw)))
        if kind == "polar":
            x, y = polar_xy(float(meta["r"]), float(meta["deg"]))
            return (ans.get("kind") == "polar"
                    and _close(ans["x"], sig4(x))
                    and _close(ans["y"], sig4(y)))
        return False
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False


def self_cases():
    import copy
    cases = []
    for sd in range(5):
        cases.append(("gen-deterministic-%d" % sd,
                      lambda sd=sd: generate(sd, 0.5) == generate(sd, 0.5)))
    for d in (0.0, 0.25, 0.5, 0.75, 1.0):
        cases.append(("verify-true-d%.2f" % d,
                      lambda d=d: verify(generate(123 + int(d * 100), d)) is True))

    def _find_seed(kind):
        for s in range(60):
            if generate(s, 0.8)["answer"]["kind"] == kind:
                return s
        return 0

    for kind, field in (("si", "value"), ("temp", "value"), ("polar", "x")):
        p = copy.deepcopy(generate(_find_seed(kind), 0.8))
        p["answer"][field] = p["answer"][field] + 1.0
        cases.append(("verify-false-corrupt-%s" % kind,
                      lambda p=p: verify(p) is False))
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("prefix-table-exponents",
                  lambda: PREFIX_EXP == {"k": 3, "M": 6, "G": 9,
                                         "m": -3, "u": -6, "n": -9}))
    cases.append(("sig4-zero", lambda: sig4(0.0) == 0.0))
    cases.append(("sig4-significant-digits",
                  lambda: abs(sig4(123456.7) - 123500.0) < 1e-6
                  and abs(sig4(0.000123456) - 0.0001235) < 1e-9))
    cases.append(("all-kinds-covered",
                  lambda: {generate(s, (s % 21) / 20.0)["answer"]["kind"]
                           for s in range(40)} == {"si", "temp", "polar"}))
    return cases
