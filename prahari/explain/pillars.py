"""Aggregate declared drivers without dropping unmapped contributions."""

from collections.abc import Mapping


def pillar_contributions(contributions: Mapping[str, float], settings: dict) -> dict[str, float]:
    result = dict.fromkeys(settings["labels"], 0.0)
    for name, value in contributions.items():
        canonical = name.removesuffix("__missing")
        if canonical not in settings["features"]:
            raise ValueError("Unmapped attribution: " + name)
        result[settings["features"][canonical]] += value
    return result
