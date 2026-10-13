# -*- coding: utf-8 -*-
"""SciReason-Forge: verifiable scientific-reasoning task generators.

Three-piece suite: forge (generators) / verify (solver grading) / bench
(independent eval, ships later). Pure standard library.
"""
MODULES = {}
for _name in ("unit_analysis", "error_propagation", "experimental_design",
              "coordinate_convert", "citation_chain"):
    try:
        _m = __import__("forge." + _name, fromlist=["x"])
        MODULES[_m.TYPE] = _m
    except ImportError:
        pass
