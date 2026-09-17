from dataclasses import dataclass


@dataclass(frozen=True)
class QualitySignals:
    complete: bool
    clear: bool
    traceable: bool
    estimable: bool
    dependencies_valid: bool
    unique: bool


WEIGHTS = {
    "complete": 25,
    "clear": 20,
    "traceable": 20,
    "estimable": 15,
    "dependencies_valid": 10,
    "unique": 10,
}


def score_quality(signals: QualitySignals) -> int:
    return sum(weight for name, weight in WEIGHTS.items() if getattr(signals, name))
