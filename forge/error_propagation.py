# -*- coding: utf-8 -*-
"""forge.error-propagation — measurement uncertainty propagation generator.

Problem: a result is computed from measured quantities,
    z = x + y, z = x - y, z = x * y, z = x / y,  or  z = a * x^n,
with known measurement uncertainties. Compute the propagated absolute
uncertainty sigma_z and the relative uncertainty sigma_z / |z|.

Standard physics conventions:
    z = x +- y :           sigma_z = sqrt(sigma_x^2 + sigma_y^2)
    z = x * y, x / y :     (sigma_z/|z|)^2 = (sigma_x/x)^2 + (sigma_y/y)^2
    z = a * x^n :          sigma_z/|z| = |n| * sigma_x/|x|

Verification re-derives sigma_z from the expression structure stored in
problem["meta"] (never trusts answer["sigma_z"]).
"""
import math
import random

from .common import make_id, pick, knob, int_knob, schema_ok

TYPE = "error-propagation"

TOL = 1e-9


def _close(a, b):
    """Relative tolerance comparison: |a - b| <= 1e-9 * max(1, |b|)."""
    return abs(a - b) <= TOL * max(1.0, abs(b))


def derive(meta):
    """Re-derive (z, sigma_z, relative_sigma, formula) from meta.

    Raises KeyError/TypeError/ValueError/ZeroDivisionError on bad input.
    """
    op = meta["op"]
    x = float(meta["x"])
    sx = float(meta["sigma_x"])
    if op in ("add", "sub"):
        y = float(meta["y"])
        sy = float(meta["sigma_y"])
        z = x + y if op == "add" else x - y
        sz = math.sqrt(sx * sx + sy * sy)
        formula = "sum-diff"
    elif op in ("mul", "div"):
        y = float(meta["y"])
        sy = float(meta["sigma_y"])
        if x == 0 or y == 0:
            raise ZeroDivisionError("relative uncertainty undefined at zero")
        z = x * y if op == "mul" else x / y
        rel = math.sqrt((sx / x) ** 2 + (sy / y) ** 2)
        sz = abs(z) * rel
        formula = "product-quotient"
    elif op == "power":
        a = float(meta["a"])
        n = float(meta["n"])
        if x == 0:
            raise ZeroDivisionError("relative uncertainty undefined at zero")
        z = a * x ** n
        sz = abs(z) * abs(n) * sx / abs(x)
        formula = "power"
    else:
        raise ValueError("unknown op: %r" % (op,))
    if z == 0 or sz < 0:
        raise ValueError("degenerate result")
    return z, sz, sz / abs(z), formula


def _measured(rng, difficulty):
    """A measured value with a small relative uncertainty."""
    x = round(rng.uniform(1.0, 50.0), 2)
    rel = rng.uniform(knob(rng, difficulty, 0.01, 0.02),
                      knob(rng, difficulty, 0.04, 0.06))
    return x, round(x * rel, 3)


def _op_for(rng, difficulty):
    if difficulty < 1.0 / 3.0:
        return pick(rng, ("add", "sub"))          # low: sums and differences
    if difficulty < 2.0 / 3.0:
        return pick(rng, ("mul", "div"))          # mid: products and quotients
    return pick(rng, ("power", "power", "mul", "div"))  # high: powers / mixed


def generate(seed, difficulty=0.5):
    rng = random.Random("error-propagation|%d" % seed)
    difficulty = min(max(float(difficulty), 0.0), 1.0)
    op = _op_for(rng, difficulty)
    meta = {"op": op}

    if op in ("add", "sub", "mul", "div"):
        x, sx = _measured(rng, difficulty)
        y, sy = _measured(rng, difficulty)
        if op == "sub":
            while abs(x - y) < 0.5:               # keep |z| safely away from 0
                x, sx = _measured(rng, difficulty)
                y, sy = _measured(rng, difficulty)
        meta.update(x=x, sigma_x=sx, y=y, sigma_y=sy)
        if op in ("add", "sub"):
            z = x + y if op == "add" else x - y
            expr = "z = x %s y" % ("+" if op == "add" else "-")
        else:
            z = x * y if op == "mul" else x / y
            expr = "z = x %s y" % ("*" if op == "mul" else "/")
        meas = ("x = %.2f +- %.3f and y = %.2f +- %.3f (independent, same units)"
                % (x, sx, y, sy))
    else:  # power
        x, sx = _measured(rng, difficulty)
        a = round(rng.uniform(0.5, 5.0), 2)
        n = int_knob(rng, difficulty, 2, 4)
        if difficulty > 0.85 and rng.random() < 0.3:
            n = -n
        meta.update(x=x, sigma_x=sx, a=a, n=n)
        z = a * x ** n
        expr = "z = %.2f * x^%d" % (a, n)
        meas = "x = %.2f +- %.3f" % (x, sx)

    z, sz, rel, formula = derive(meta)
    problem = {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": difficulty,
        "seed": int(seed),
        "prompt": ("A measurement gives %s. The result is computed as %s. "
                   "Using standard uncertainty propagation, find the absolute "
                   "uncertainty sigma_z and the relative uncertainty "
                   "sigma_z / |z| of the result z = %.6g."
                   % (meas, expr, z)),
        "answer": {
            "sigma_z": sz,
            "relative_sigma": rel,
            "formula": formula,
        },
        "solution": ("Rule (%s): %s. With %s this gives sigma_z = %.6g and "
                     "relative uncertainty = %.6g."
                     % (formula, _RULE_TEXT[formula], meas, sz, rel)),
        "meta": meta,
    }
    return problem


_RULE_TEXT = {
    "sum-diff": "sigma_z = sqrt(sigma_x^2 + sigma_y^2)",
    "product-quotient": "sigma_z/|z| = sqrt((sigma_x/x)^2 + (sigma_y/y)^2)",
    "power": "sigma_z/|z| = |n| * sigma_x/|x|",
}


def verify(problem):
    """Re-derive sigma_z from meta and compare against the claimed answer."""
    try:
        z, sz, rel, formula = derive(problem["meta"])
        a = problem["answer"]
        return (_close(float(a["sigma_z"]), sz)
                and _close(float(a["relative_sigma"]), rel)
                and a["formula"] == formula)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False


def self_cases():
    import copy
    cases = []
    # 1-5: deterministic generation across the difficulty range
    for d in (0.0, 0.25, 0.5, 0.75, 1.0):
        cases.append(("gen-deterministic-d%.2f" % d,
                      lambda d=d: generate(11, d) == generate(11, d)))
    # 6-10: verify accepts freshly generated problems
    for i, (sd, d) in enumerate(((1, 0.0), (2, 0.3), (3, 0.5), (4, 0.7), (5, 1.0))):
        cases.append(("verify-true-%d" % i,
                      lambda sd=sd, d=d: verify(generate(sd, d)) is True))
    # 11-13: corrupting any answer field must fail verification
    base = generate(7, 0.5)
    for field, corrupt in (
            ("sigma_z", lambda a: a.update(sigma_z=a["sigma_z"] * 1.01)),
            ("relative_sigma", lambda a: a.update(relative_sigma=0.0)),
            ("formula", lambda a: a.update(formula="bogus-rule"))):
        p = copy.deepcopy(base)
        corrupt(p["answer"])
        cases.append(("verify-false-corrupt-%s" % field,
                      lambda p=p: verify(p) is False))
    # 14: structural schema conformance
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    # helper boundary cases
    cases.append(("close-within-tol", lambda: _close(1.0, 1.0 + 5e-10) is True))
    cases.append(("close-outside-tol", lambda: _close(1.0, 1.0 + 1e-6) is False))
    cases.append(("zero-div-y-rejected",
                  lambda: verify({"meta": {"op": "div", "x": 2.0, "sigma_x": 0.1,
                                           "y": 0.0, "sigma_y": 0.1},
                                  "answer": {"sigma_z": 1.0,
                                             "relative_sigma": 1.0,
                                             "formula": "product-quotient"}}) is False))
    cases.append(("power-negative-n",
                  lambda: _close(derive({"op": "power", "x": 2.0, "sigma_x": 0.1,
                                         "a": 1.0, "n": -2})[2], 0.1) is True))
    cases.append(("missing-answer-rejected", lambda: verify({"meta": {}}) is False))
    return cases
