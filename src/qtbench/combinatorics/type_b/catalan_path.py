from __future__ import annotations

from dataclasses import dataclass
from functools import cache, cached_property
from math import comb


def type_b_catalan_number(n: int) -> int:
    """The type B Catalan number, `binomial(2n, n)`."""
    if n < 0:
        raise ValueError("n must be nonnegative")
    return comb(2 * n, n)


def is_type_b_catalan_path(steps: str) -> bool:
    """A `2n`-step N/E word starting at `(0,0)` that stays weakly above `y=x`."""
    if not isinstance(steps, str) or len(steps) % 2 != 0:
        return False
    x = y = 0
    for step in steps:
        if step == "N":
            y += 1
        elif step == "E":
            x += 1
        else:
            return False
        if x > y:
            return False
    return True


@dataclass(frozen=True, init=False)
class TypeBCatalanPath:
    """Stump's type B Catalan path.

    A word of `2n` north (`N`) and east (`E`) steps from `(0,0)` that stays
    weakly above the diagonal `y = x`; the endpoint lies on the anti-diagonal
    `x + y = 2n`. These paths are counted by the type B Catalan number
    `binomial(2n, n)`. The public first statistic is `area`.
    """

    steps: str
    n: int

    def __init__(self, steps: str, *, validate: bool = True) -> None:
        if validate and not is_type_b_catalan_path(steps):
            raise ValueError(f"not a type B Catalan path: {steps!r}")
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "n", len(steps) // 2)

    def __len__(self) -> int:
        return len(self.steps)

    @cached_property
    def area_word(self) -> tuple[int, ...]:
        """Per-north-step area contributions over the type B (diamond) region."""
        n = self.n
        x = y = 0
        values: list[int] = []
        for step in self.steps:
            if step == "N":
                row_capacity = y if y < n else 2 * n - y
                values.append(row_capacity - x)
                y += 1
            else:
                x += 1
        return tuple(values)

    def area(self) -> int:
        """Type B area: the number of boxes under the path in the diamond region."""
        return sum(self.area_word)

    def to_jsonable(self) -> str:
        return self.steps


@cache
def _type_b_catalan_path_steps(n: int) -> tuple[str, ...]:
    if n < 0:
        raise ValueError("n must be nonnegative")
    total = 2 * n
    paths: list[str] = []

    def build(x: int, y: int, prefix: str) -> None:
        if len(prefix) == total:
            paths.append(prefix)
            return
        build(x, y + 1, prefix + "N")
        if x < y:
            build(x + 1, y, prefix + "E")

    build(0, 0, "")
    return tuple(paths)


@cache
def enumerate_type_b_catalan_paths(n: int) -> tuple[TypeBCatalanPath, ...]:
    return tuple(TypeBCatalanPath(steps, validate=False) for steps in _type_b_catalan_path_steps(n))
