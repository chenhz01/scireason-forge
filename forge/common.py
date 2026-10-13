# -*- coding: utf-8 -*-
"""forge.common — shared schema and helpers for SciReason-Forge task generators.

Every task module exposes:
    TYPE: str                       -- unique task-type id (kebab-case)
    generate(seed, difficulty=0.5)  -- deterministic problem dict
    verify(problem) -> bool         -- re-derives the answer from the problem
                                       statement (never trusts problem["answer"])
    self_cases() -> list[(name, fn)]-- module-level sanity cases (fn -> bool)

Problem schema (all types):
    id          unique string
    type        task-type id
    difficulty  float 0.0-1.0
    seed        int used by the generator
    prompt      human-readable question (English, public-facing)
    answer      dict of machine-checkable ground-truth fields
    solution    step-by-step derivation trace
    meta        type-specific extras (e.g. distractors, topic tags)

Pure standard library only. Deterministic: same (seed, difficulty) -> same problem.
"""
import random
import hashlib

TYPES = ("unit-analysis", "error-propagation", "experimental-design",
         "coordinate-convert", "citation-chain")

_SCHEMA_KEYS = ("id", "type", "difficulty", "seed", "prompt", "answer",
                "solution", "meta")


def make_id(task_type, seed):
    """Stable unique id from type + seed."""
    h = hashlib.sha1(("%s|%d" % (task_type, seed)).encode("utf-8")).hexdigest()[:10]
    return "%s-%s" % (task_type, h)


def schema_ok(problem):
    """Structural conformance to the problem schema."""
    if not isinstance(problem, dict):
        return False
    for k in _SCHEMA_KEYS:
        if k not in problem:
            return False
    if problem["type"] not in TYPES:
        return False
    if not (0.0 <= float(problem["difficulty"]) <= 1.0):
        return False
    for k in ("prompt", "solution"):
        if not isinstance(problem[k], str) or len(problem[k]) < 10:
            return False
    if not isinstance(problem["answer"], dict) or not problem["answer"]:
        return False
    if not isinstance(problem["meta"], dict):
        return False
    return True


def knob(rng, difficulty, lo, hi):
    """Map global difficulty [0,1] onto a module-local parameter range."""
    difficulty = min(max(difficulty, 0.0), 1.0)
    return lo + (hi - lo) * difficulty


def int_knob(rng, difficulty, lo, hi):
    return int(round(knob(rng, difficulty, lo, hi)))


def pick(rng, seq):
    return seq[rng.randrange(len(seq))]


def rrng(*parts):
    """Deterministic RNG from arbitrary hashable parts (for verify-side replay)."""
    return random.Random(hash(("forge",) + tuple(parts)))
