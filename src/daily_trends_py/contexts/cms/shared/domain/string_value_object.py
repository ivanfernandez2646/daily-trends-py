from dataclasses import dataclass


@dataclass(frozen=True)
class StringValueObject:
    value: str | None
