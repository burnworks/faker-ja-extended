"""意地悪なデータのカタログ。

文字コード、正規化、文字数の数え方、表記の揺れなど、システムが壊れやすいパターンを集めたもの。
Faker を使わずに、pytest のパラメータ化などで全件を試すのに使える::

    from faker_ja_extended.nasty import surname_cases

    @pytest.mark.parametrize("case", surname_cases(exclude={"ivs"}), ids=lambda c: c.id)
    def test_register(case):
        ...

Faker からは PersonProvider の nasty_last_name() などで使う。
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from importlib.resources import files

TAGS: dict[str, str] = {
    "kanji_variant": "異体字（旧字体・俗字・互換漢字など）。base が標準的な表記",
    "spelling_variant": "表記の揺れ（ヶ／ケ、ノ／之／の、々の有無など）。base が標準的な表記",
    "cp932_only": "CP932（Windows-31J）では表せるが、JIS X 0208（Shift_JIS）にはない文字を含む",
    "cp932_unmappable": "CP932 に変換できない文字を含む",
    "nfc_changes": "Unicode の正規化（NFC）で文字列が変わる",
    "surrogate_pair": "U+10000 以降の文字（UTF-16 でサロゲートペアになる文字）を含む",
    "ivs": "異体字セレクタ（IVS、U+E0100〜U+E01EF）を含む。セレクタ自体もサロゲートペアになる",
    "iteration_mark": "繰り返し記号「々」を含む",
    "contains_kana": "ひらがな・カタカナを含む",
    "single_char": "見た目が 1 文字（異体字セレクタは数えない）",
    "long": "見た目が 4 文字以上（異体字セレクタは数えない）",
    "unusual_reading": "漢字から読みを推測しにくい",
}


@dataclass(frozen=True, slots=True)
class NastyCase:
    """カタログの 1 件。"""

    id: str
    category: str
    value: str
    base: str
    kana: str
    romaji: str
    tags: frozenset[str]
    note: str

    @property
    def pair(self) -> tuple[str, str, str]:
        """(表記, カタカナ, ローマ字)。Faker の last_name_pair() と同じ形。"""
        return self.value, self.kana, self.romaji

    def __str__(self) -> str:
        return self.value


@cache
def _load(category: str) -> tuple[NastyCase, ...]:
    text = files("faker_ja_extended").joinpath("catalog", f"{category}s.toml").read_text("utf-8")
    entries = tomllib.loads(text)[category]
    cases = tuple(
        NastyCase(
            id=e["id"],
            category=category,
            value=e["value"],
            base=e["base"],
            kana=e["kana"],
            romaji=e["romaji"],
            tags=frozenset(e["tags"]),
            note=e["note"],
        )
        for e in entries
    )
    unknown = {tag for case in cases for tag in case.tags} - TAGS.keys()
    if unknown:
        raise ValueError(f"カタログに未定義のタグがあります: {sorted(unknown)}")
    return cases


def _check_tags(tags: Iterable[str] | None, argument: str) -> frozenset[str]:
    tags = frozenset(tags or ())
    unknown = tags - TAGS.keys()
    if unknown:
        raise ValueError(
            f"{argument} に未定義のタグがあります: {sorted(unknown)}（使えるタグ: {sorted(TAGS)}）"
        )
    return tags


def filter_cases(
    cases: Iterable[NastyCase],
    include: Iterable[str] | None = None,
    exclude: Iterable[str] | None = None,
) -> list[NastyCase]:
    """タグで絞り込む。

    include を指定すると、そのタグのどれかを持つものだけを残す。
    exclude を指定すると、そのタグのどれかを持つものを除く。
    """
    include_tags = _check_tags(include, "include")
    exclude_tags = _check_tags(exclude, "exclude")
    return [
        case
        for case in cases
        if (not include_tags or case.tags & include_tags) and not case.tags & exclude_tags
    ]


def surname_cases(
    include: Iterable[str] | None = None, exclude: Iterable[str] | None = None
) -> list[NastyCase]:
    """意地悪な姓のカタログを返す。タグで絞り込める（filter_cases を参照）。"""
    return filter_cases(_load("surname"), include, exclude)
