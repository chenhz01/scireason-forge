# -*- coding: utf-8 -*-
"""forge.experimental-design — experimental-design flaw-spotting generator.

Problem: a short study description (research question + treatment/control
setup) contains exactly one planted methodological flaw (by construction).
The solver picks which of four options correctly names the flaw.

Verification re-derives the correct option letter from meta["defect_type"]
and the option texts (keyword structural check); it never trusts
answer["correct_option"] alone.
"""
from .common import make_id, pick, int_knob, knob, schema_ok
import random

TYPE = "experimental-design"

# Defect catalogue: each flaw has a public name, a description, and cue
# keywords that MUST appear in the option text that describes it.  Cue sets
# are pairwise disjoint so a keyword scan identifies exactly one defect.
DEFECTS = {
    "no-control": {
        "name": "No control group",
        "description": ("Every subject receives the treatment and the outcome "
                        "is reported as improved, with no untreated baseline "
                        "to compare against."),
        "cues": ("control group",),
    },
    "confounder": {
        "name": "Confounding variable",
        "description": ("A second variable differs systematically between the "
                        "treated and untreated subjects, so the effect cannot "
                        "be attributed to the treatment alone."),
        "cues": ("confounding", "confounder"),
    },
    "small-sample": {
        "name": "Sample size too small",
        "description": ("Very few subjects per group, so random noise can "
                        "easily explain the observed difference."),
        "cues": ("sample size",),
    },
    "no-blinding": {
        "name": "No blinding",
        "description": ("The people measuring the outcome know which group "
                        "each subject belongs to, so their judgements can be "
                        "biased."),
        "cues": ("blinded", "blind"),
    },
}

# At least six scenario templates; variable names are combined randomly.
SCENARIOS = [
    {"topic": "plant growth",
     "question": "Does a new growth supplement make plants grow taller?",
     "subject": "bean plants",
     "treatment": "the growth supplement",
     "outcome": "plant height after 30 days",
     "confound": "the treated plants were placed on the sunny windowsill while the untreated ones stayed in a shaded corner",
     "blind_note": "the research assistant measuring plant height could see which tray came from the treated bench"},
    {"topic": "drug trial",
     "question": "Does the new compound reduce headache frequency?",
     "subject": "volunteers with chronic headaches",
     "treatment": "the new compound",
     "outcome": "number of headache days per month",
     "confound": "volunteers receiving the compound were also told to drink more water, while the others were not",
     "blind_note": "the neurologist counting headache days knew which volunteers took the compound"},
    {"topic": "website A/B test",
     "question": "Does the new checkout page increase purchases?",
     "subject": "site visitors",
     "treatment": "the redesigned checkout page",
     "outcome": "purchase conversion rate",
     "confound": "the new page was shown only during the evening peak-traffic hours while the old page ran the rest of the day",
     "blind_note": "the analyst labelling sessions as successful knew which variant produced them"},
    {"topic": "battery life",
     "question": "Does a new electrolyte formula extend battery life?",
     "subject": "lithium-ion cells",
     "treatment": "the new electrolyte formula",
     "outcome": "hours of discharge until 80% capacity",
     "confound": "cells with the new formula were tested in a 20 C chamber while the standard cells were tested at 35 C",
     "blind_note": "the technician timing each discharge knew which batch used the new formula"},
    {"topic": "fertilizer effect",
     "question": "Does the organic fertilizer raise crop yield?",
     "subject": "wheat plots",
     "treatment": "the organic fertilizer",
     "outcome": "kilograms of grain per plot",
     "confound": "fertilized plots sat in the low-lying field with richer soil while control plots were on the sandy slope",
     "blind_note": "the student weighing the harvest knew which plots had been fertilized"},
    {"topic": "sleep and memory",
     "question": "Does an afternoon nap improve word recall?",
     "subject": "undergraduate participants",
     "treatment": "a 90-minute nap before the test",
     "outcome": "number of words recalled from a study list",
     "confound": "the nap group practised the word list once more before sleeping than the awake group did",
     "blind_note": "the experimenter scoring recall sheets knew which participants had napped"},
    {"topic": "typing speed",
     "question": "Does the new keyboard layout make people type faster?",
     "subject": "office workers",
     "treatment": "the ergonomic keyboard layout",
     "outcome": "words typed per minute",
     "confound": "workers given the new layout were all experienced typists while the others were beginners",
     "blind_note": "the evaluator timing each session knew which layout the worker was using"},
]


def _option_text(rng, defect_type, sc, defect_desc=None):
    """Render an option sentence for a defect in the context of scenario sc.

    The text embeds the defect's cue keyword(s) exactly once so the keyword
    scan in verify() can identify it structurally.
    """
    treat = sc["treatment"]
    outcome = sc["outcome"]
    subject = sc["subject"]
    n_small = int_knob(random.Random("n|%d" % rng.randrange(10**6)),
                       1.0, 4, 11)
    if defect_type == "no-control":
        return ("All %s receive %s and %s improves, but the study never "
                "includes a control group to compare against."
                % (subject, treat, outcome))
    if defect_type == "confounder":
        return ("A confounding variable is present: %s."
                % (sc["confound"],))
    if defect_type == "small-sample":
        return ("The sample size is too small: only about %d %s per group, "
                "so the difference in %s may be random noise."
                % (n_small, subject, outcome))
    if defect_type == "no-blinding":
        return ("The study is not blinded: %s, so measurements of %s may be "
                "biased." % (sc["blind_note"], outcome))
    raise ValueError(defect_type)


def _matches(option_text, defect_type):
    """Structural check: does the option text carry this defect's cues?"""
    low = option_text.lower()
    return any(cue in low for cue in DEFECTS[defect_type]["cues"])


def _derive_correct(options, defect_type):
    """Re-derive the correct option letter from option texts + defect type."""
    hits = [letter for letter, text in sorted(options.items())
            if _matches(text, defect_type)]
    if len(hits) != 1:
        return None
    return hits[0]


def generate(seed, difficulty=0.5):
    rng = random.Random("experimental-design|%d" % seed)
    if difficulty < 0.34:
        defect_type = "no-control"
    elif difficulty < 0.67:
        defect_type = "confounder"
    else:
        defect_type = "small-sample" if rng.random() < knob(
            rng, difficulty, 0.35, 0.65) else "no-blinding"
    sc = pick(rng, SCENARIOS)

    # exactly one planted defect: pick correct letter, build distractors from
    # the three remaining defect types
    letters = ["A", "B", "C", "D"]
    rng.shuffle(letters)
    correct_letter = letters[0]
    others = [d for d in DEFECTS if d != defect_type]
    rng.shuffle(others)
    options = {correct_letter: _option_text(rng, defect_type, sc)}
    for letter, d in zip(letters[1:], others):
        options[letter] = _option_text(rng, d, sc)

    prompt = ("%s To test this, a study is set up as follows. %s "
              "Which methodological flaw best describes the main defect in "
              "this study?\n"
              "A. %s\nB. %s\nC. %s\nD. %s\n"
              "Answer with a single letter."
              % (sc["question"], _design_text(rng, sc, defect_type),
                 options["A"], options["B"], options["C"], options["D"]))
    solution = ("The study plants exactly one defect: %s (%s). Option %s "
                "matches this defect; the other options describe different "
                "flaws absent from the design."
                % (DEFECTS[defect_type]["name"], defect_type,
                   correct_letter))
    problem = {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"correct_option": correct_letter,
                   "defect_type": defect_type},
        "solution": solution,
        "meta": {"defect_type": defect_type,
                 "correct_option": correct_letter,
                 "scenario": sc["topic"],
                 "options": options},
    }
    return problem


def _design_text(rng, sc, defect_type):
    """One-paragraph description of the study setup (groups, sizes, blinding)."""
    subject = sc["subject"]
    treat = sc["treatment"]
    outcome = sc["outcome"]
    n_a = int_knob(rng, rng.random(), 6, 40)
    n_b = int_knob(rng, rng.random(), 6, 40)
    if defect_type == "no-control":
        return ("All %d %s are given %s, and afterwards %s is recorded for "
                "every one of them." % (n_a, subject, treat, outcome))
    if defect_type == "small-sample":
        return ("A group of %d %s receives %s and another group of %d "
                "receives nothing; %s is then compared between the two "
                "groups." % (n_a, subject, treat, n_b, outcome))
    return ("One group of %d %s receives %s while a matched control group of "
            "%d receives nothing; %s is then compared between the two groups."
            % (n_a, subject, treat, n_b, outcome))


def verify(problem):
    """Re-derive the correct letter from meta + option texts; compare."""
    try:
        defect_type = problem["meta"]["defect_type"]
        options = problem["meta"]["options"]
        if defect_type not in DEFECTS:
            return False
        if sorted(options) != ["A", "B", "C", "D"]:
            return False
        derived = _derive_correct(options, defect_type)
        if derived is None:
            return False
        a = problem["answer"]
        # the correct option text must really match the defect's cue keywords
        if not _matches(options[derived], defect_type):
            return False
        # every other option must NOT match the planted defect's cues
        for letter, text in options.items():
            if letter != derived and _matches(text, defect_type):
                return False
        return (a["correct_option"] == derived
                and a["defect_type"] == defect_type
                and problem["meta"]["correct_option"] == derived)
    except (KeyError, TypeError, ValueError):
        return False


def self_cases():
    import copy
    cases = []
    for sd in range(5):
        cases.append(("gen-deterministic-%d" % sd,
                      lambda sd=sd: generate(sd, 0.5) == generate(sd, 0.5)))
    for i, d in enumerate((0.0, 0.2, 0.5, 0.8, 1.0)):
        cases.append(("verify-true-d%.2f" % d,
                      lambda d=d: verify(generate(321 + i, d))))
    base = generate(9, 0.5)
    for name, corrupt in (
            ("swap-letter", lambda a: a.update(correct_option="A"
                                               if a["correct_option"] != "A"
                                               else "B")),
            ("bad-defect-type", lambda a: a.update(defect_type="no-control")),
            ("wrong-letter", lambda a: a.update(
                correct_option=next(l for l in "ABCD"
                                    if l != a["correct_option"])))):
        p = copy.deepcopy(base)
        corrupt(p["answer"])
        cases.append(("verify-false-%s" % name,
                      lambda p=p: verify(p) is False))
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))

    def _exactly_one_correct():
        for s in (1, 5, 77, 900):
            p = generate(s, 0.5)
            dt = p["meta"]["defect_type"]
            opts = p["meta"]["options"]
            hits = [l for l, t in sorted(opts.items()) if _matches(t, dt)]
            if len(hits) != 1 or hits[0] != p["answer"]["correct_option"]:
                return False
            if sorted(opts) != ["A", "B", "C", "D"]:
                return False
        return True
    cases.append(("exactly-one-correct-option", _exactly_one_correct))
    return cases
