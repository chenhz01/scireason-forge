# -*- coding: utf-8 -*-
"""forge.citation-chain — citation-chain (DAG reachability) task generator.

Problem: a directed acyclic citation graph over papers P1..PN, where an edge
A -> B means "paper A cites paper B" (edges only go from a higher number to
a lower number, which guarantees acyclicity). When a paper is retracted,
every paper that cites it directly or indirectly has its conclusions
invalidated.

Verification re-derives the affected set from meta["edges"] and
meta["retracted"] (reverse reachability), and re-checks acyclicity.
It never trusts answer["affected"].
"""
import copy
import random

from .common import make_id, pick, int_knob, knob, schema_ok

TYPE = "citation-chain"


def _num(pid):
    """'P7' -> 7"""
    return int(pid[1:])


def _is_acyclic(edges):
    """True iff every edge goes from a higher paper number to a lower one."""
    for a, b in edges:
        if _num(a) <= _num(b):
            return False
    return True


def _affected_set(edges, retracted):
    """All papers with a directed path -> retracted (excluding itself)."""
    preds = {}
    for a, b in edges:
        preds.setdefault(b, []).append(a)
    seen = set()
    stack = [retracted]
    while stack:
        cur = stack.pop()
        for p in preds.get(cur, ()):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return sorted(seen)


def generate(seed, difficulty=0.5):
    rng = random.Random("citation-chain|%d" % seed)
    n = int_knob(rng, difficulty, 4, 8)
    density = knob(rng, difficulty, 0.4, 0.9)
    retract_prob = knob(rng, difficulty, 0.0, 0.6)
    papers = ["P%d" % i for i in range(1, n + 1)]
    edges = []
    for i in range(2, n + 1):
        # every paper cites at least one earlier paper (keeps the chain connected)
        base = pick(rng, papers[: i - 1])
        edges.append(["P%d" % i, base])
        for j in range(1, i - 1):
            if rng.random() < density:
                edges.append(["P%d" % i, papers[j - 1]])
    retracted = None
    if rng.random() < retract_prob:
        cited = sorted({b for _, b in edges})
        retracted = pick(rng, cited) if cited else papers[0]
    affected = _affected_set(edges, retracted) if retracted else []
    if retracted:
        prompt = ("In a citation network of %d papers (P1..P%d), an edge "
                  "\"A cites B\" means A's conclusions depend on B's results. "
                  "Paper %s has been RETRACTED. Which papers' conclusions "
                  "become invalid, directly or indirectly (i.e. all papers "
                  "with a citation path leading to %s)? Give the sorted list."
                  % (n, n, retracted, retracted))
        solution = ("Retracted: %s. A paper is affected iff some citation "
                    "path leads to %s. Reverse-reachable closure from %s "
                    "gives: %s (%d paper(s) affected, excluding %s itself)."
                    % (retracted, retracted, retracted,
                       ", ".join(affected) if affected else "none",
                       len(affected), retracted))
    else:
        prompt = ("In a citation network of %d papers (P1..P%d), an edge "
                  "\"A cites B\" means A's conclusions depend on B's results. "
                  "No paper has been retracted. Which papers' conclusions are "
                  "invalidated by a retraction? Give the sorted list."
                  % (n, n))
        solution = ("No paper is retracted, so no conclusions are invalidated: "
                    "the affected list is empty and the count is 0.")
    problem = {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"retracted": retracted,
                   "affected": affected,
                   "count": len(affected)},
        "solution": solution,
        "meta": {"edges": edges, "retracted": retracted},
    }
    return problem


def verify(problem):
    """Re-derive the affected set from meta; compare with the claimed answer."""
    try:
        edges = [[str(a), str(b)] for a, b in problem["meta"]["edges"]]
        retracted = problem["meta"]["retracted"]
        if retracted is not None:
            retracted = str(retracted)
        # acyclicity: every citation must point to an earlier paper
        if not _is_acyclic(edges):
            return False
        ids = {p for e in edges for p in e}
        for pid in ids | ({retracted} if retracted else set()):
            if pid[:1] != "P" or not pid[1:].isdigit():
                return False
        if retracted and retracted not in ids:
            return False
        if retracted:
            affected = _affected_set(edges, retracted)
        else:
            affected = []
        a = problem["answer"]
        if a["retracted"] != retracted:
            return False
        claimed = list(a["affected"])
        if claimed != sorted(claimed):
            return False
        if claimed != affected or int(a["count"]) != len(affected):
            return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def self_cases():
    cases = []
    for sd in range(5):
        cases.append(("gen-deterministic-%d" % sd,
                      lambda sd=sd: generate(sd, 0.5) == generate(sd, 0.5)))
    for d in (0.0, 0.25, 0.5, 0.75, 1.0):
        cases.append(("verify-true-d%.2f" % d,
                      lambda d=d: verify(generate(123 + int(d * 100), d))))
    # find a seed whose retraction actually invalidates someone
    base = None
    for sd in range(1, 60):
        p = generate(sd, 1.0)
        if p["answer"]["count"] >= 2:
            base = p
            break
    assert base is not None
    p = copy.deepcopy(base)
    p["answer"]["affected"] = p["answer"]["affected"][1:]
    cases.append(("verify-false-corrupt-affected-drop",
                  lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"]["count"] = p["answer"]["count"] + 1
    cases.append(("verify-false-corrupt-count",
                  lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"]["retracted"] = "P999"
    cases.append(("verify-false-corrupt-retracted",
                  lambda p=p: verify(p) is False))
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    # acyclicity guard: high->low ok, low->high rejected
    cases.append(("acyclic-ok", lambda: _is_acyclic([["P3", "P1"], ["P2", "P1"]])))
    cases.append(("cyclic-rejected", lambda: not _is_acyclic([["P1", "P3"]])))
    return cases
