from __future__ import annotations

from dataclasses import dataclass
import re

from .type_a.kostka_tableau import conjugate_partition, iter_partitions

SuccessiveRankPartitionWord = str
_ENCODING = re.compile(r"([ST]);([1-9][0-9]*);([1-9][0-9]*);([1-9][0-9]*(?:,[1-9][0-9]*)*)")


def successive_ranks(parts: tuple[int, ...]) -> tuple[int, ...]:
    conjugate = conjugate_partition(parts)
    return tuple(
        parts[index] - conjugate[index]
        for index in range(len(parts))
        if parts[index] > index
    )


def canonical_successive_rank_partition(
    side: str,
    modulus: int,
    residue: int,
    parts: tuple[int, ...],
) -> SuccessiveRankPartitionWord:
    parts = tuple(parts)
    if (
        side not in {"S", "T"}
        or type(modulus) is not int
        or type(residue) is not int
        or not _valid_parameters(modulus, residue)
        or not parts
        or any(type(part) is not int or part < 1 for part in parts)
        or any(left < right for left, right in zip(parts, parts[1:]))
        or not _belongs(side, modulus, residue, parts)
    ):
        raise ValueError("invalid successive-rank partition")
    return f"{side};{modulus};{residue};{','.join(map(str, parts))}"


def _valid_parameters(modulus: int, residue: int) -> bool:
    return modulus >= 3 and 0 < 2 * residue < modulus


def _belongs(side: str, modulus: int, residue: int, parts: tuple[int, ...]) -> bool:
    if side == "S":
        lower, upper = 2 - residue, modulus - residue - 2
        return all(lower <= rank <= upper for rank in successive_ranks(parts))
    forbidden = {0, residue, (-residue) % modulus}
    return all(part % modulus not in forbidden for part in parts)


def is_successive_rank_partition_encoding(value: object) -> bool:
    if not isinstance(value, str):
        return False
    match = _ENCODING.fullmatch(value)
    if match is None:
        return False
    side, modulus_text, residue_text, parts_text = match.groups()
    modulus, residue = int(modulus_text), int(residue_text)
    parts = tuple(int(piece) for piece in parts_text.split(","))
    if (
        not _valid_parameters(modulus, residue)
        or any(left < right for left, right in zip(parts, parts[1:]))
        or not _belongs(side, modulus, residue, parts)
    ):
        return False
    return value == canonical_successive_rank_partition(side, modulus, residue, parts)


@dataclass(frozen=True, init=False)
class SuccessiveRankPartition:
    """A partition in one side of the Andrews--Bressoud identity."""

    encoding: SuccessiveRankPartitionWord
    side: str
    modulus: int
    residue: int
    parts: tuple[int, ...]

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_successive_rank_partition_encoding(encoding):
            raise ValueError("invalid canonical successive-rank partition encoding")
        match = _ENCODING.fullmatch(encoding)
        if match is None:
            raise ValueError("invalid successive-rank partition encoding")
        side, modulus_text, residue_text, parts_text = match.groups()
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "side", "source" if side == "S" else "target")
        object.__setattr__(self, "modulus", int(modulus_text))
        object.__setattr__(self, "residue", int(residue_text))
        object.__setattr__(self, "parts", tuple(int(piece) for piece in parts_text.split(",")))

    @property
    def weight(self) -> int:
        return sum(self.parts)

    @property
    def size(self) -> int:
        return self.weight

    @property
    def ranks(self) -> tuple[int, ...]:
        return successive_ranks(self.parts)

    def feature_dict(self) -> dict[str, object]:
        return {
            "side": self.side,
            "modulus": self.modulus,
            "residue": self.residue,
            "parts": list(self.parts),
            "successive_ranks": list(self.ranks),
            "weight": self.weight,
        }


def iter_successive_rank_partitions(
    side: str,
    modulus: int,
    residue: int,
    weight: int,
) -> tuple[SuccessiveRankPartition, ...]:
    if side not in {"source", "target"} or not _valid_parameters(modulus, residue):
        raise ValueError("invalid side or Andrews--Bressoud parameters")
    marker = "S" if side == "source" else "T"
    return tuple(
        SuccessiveRankPartition(
            canonical_successive_rank_partition(marker, modulus, residue, parts),
            validate=False,
        )
        for parts in iter_partitions(weight)
        if _belongs(marker, modulus, residue, parts)
    )


def successive_rank_partition_size(value) -> int:
    if isinstance(value, SuccessiveRankPartition):
        return value.weight
    return SuccessiveRankPartition(value).weight
