"""意地悪なデータのカタログのテスト。

カタログは手で書くので、タグの付け間違いを防ぐことが一番大事。
文字の性質から判定できるタグは、「タグがあるのに性質がない」「性質があるのにタグがない」の
両方を検出する。
"""

from __future__ import annotations

import random
import unicodedata
from pathlib import Path

import pytest
from faker import Faker

from faker_ja_extended import NastyCase, PersonProvider, surname_cases
from faker_ja_extended.kana import kata_to_hira, to_hepburn
from faker_ja_extended.nasty import TAGS, filter_cases

CASES = surname_cases()


def _encodable(text: str, encoding: str) -> bool:
    try:
        text.encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


def _is_ivs(ch: str) -> bool:
    return 0xE0100 <= ord(ch) <= 0xE01EF


def _visible_length(text: str) -> int:
    return sum(1 for ch in text if not _is_ivs(ch))


# 文字の性質から判定できるタグ
AUTO_TAGS = {
    "surrogate_pair": lambda v: any(ord(ch) > 0xFFFF for ch in v),
    "ivs": lambda v: any(_is_ivs(ch) for ch in v),
    "nfc_changes": lambda v: unicodedata.normalize("NFC", v) != v,
    "cp932_only": lambda v: _encodable(v, "cp932") and not _encodable(v, "shift_jis"),
    "cp932_unmappable": lambda v: not _encodable(v, "cp932"),
    "iteration_mark": lambda v: "々" in v,
    "contains_kana": lambda v: any(
        0x3041 <= ord(ch) <= 0x3096 or 0x30A1 <= ord(ch) <= 0x30FA for ch in v
    ),
    "single_char": lambda v: _visible_length(v) == 1,
    "long": lambda v: _visible_length(v) >= 4,
}


def test_catalog_is_loaded() -> None:
    assert len(CASES) >= 30
    assert all(isinstance(case, NastyCase) for case in CASES)
    ids = [case.id for case in CASES]
    assert len(ids) == len(set(ids)), "ID が重複しています"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
@pytest.mark.parametrize("tag", sorted(AUTO_TAGS))
def test_auto_tags_match_properties(case: NastyCase, tag: str) -> None:
    has_property = AUTO_TAGS[tag](case.value)
    assert (tag in case.tags) == has_property, (
        f"{case.id}: タグ {tag} は {'必要' if has_property else '不要'}です（value={case.value!r}）"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_variant_tags_match_base(case: NastyCase) -> None:
    is_variant = bool(case.tags & {"kanji_variant", "spelling_variant"})
    assert is_variant == (case.value != case.base), (
        f"{case.id}: base と value が異なるものには kanji_variant か spelling_variant が必要です"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_reading_and_romaji_are_consistent(case: NastyCase) -> None:
    hira = kata_to_hira(case.kana)
    assert all(0x3041 <= ord(ch) <= 0x3096 or ch == "ー" for ch in hira), case.kana
    assert to_hepburn(hira) == case.romaji


def test_variants_share_reading_with_base() -> None:
    by_value = {case.value: case for case in CASES}
    for case in CASES:
        if case.base in by_value:
            assert case.kana == by_value[case.base].kana, case.id


def test_all_tags_are_documented_and_used() -> None:
    used = {tag for case in CASES for tag in case.tags}
    assert used == set(TAGS)
    assert set(AUTO_TAGS) <= set(TAGS)


def test_nfc_case_normalizes_to_base() -> None:
    case = next(c for c in CASES if c.id == "nfc-otsuka")
    assert unicodedata.normalize("NFC", case.value) == case.base


# --- 絞り込み ---


def test_filter_include_and_exclude() -> None:
    surrogate = surname_cases(include={"surrogate_pair"})
    assert surrogate and all("surrogate_pair" in c.tags for c in surrogate)

    either = surname_cases(include={"ivs", "surrogate_pair"})
    assert {c.id for c in either} == {c.id for c in CASES if c.tags & {"ivs", "surrogate_pair"}}

    without = surname_cases(exclude={"ivs", "surrogate_pair"})
    assert not any(c.tags & {"ivs", "surrogate_pair"} for c in without)
    assert len(without) + len(either) == len(CASES)


def test_filter_rejects_unknown_tags() -> None:
    with pytest.raises(ValueError, match="未定義のタグ"):
        surname_cases(include={"surrogate"})
    with pytest.raises(ValueError, match="exclude"):
        filter_cases(CASES, exclude={"nfc"})


# --- Faker から使う ---


def make_faker(data_dir: Path, seed: int = 1, **settings) -> Faker:
    provider = type("P", (PersonProvider,), {"data_dir": data_dir, **settings})
    fake = Faker("ja_JP")
    fake.add_provider(provider)
    fake.seed_instance(seed)
    return fake


def test_nasty_last_name_methods(data_dir: Path) -> None:
    fake = make_faker(data_dir)
    values = {case.value for case in CASES}
    assert fake.nasty_last_name() in values
    assert fake.nasty_last_name_pair() in {case.pair for case in CASES}
    case = fake.nasty_last_name_case(include={"cp932_unmappable"})
    assert "cp932_unmappable" in case.tags and case.note

    picked = {fake.nasty_last_name(exclude={"ivs"}) for _ in range(500)}
    assert not any(c.value in picked for c in CASES if "ivs" in c.tags)

    with pytest.raises(ValueError, match="条件に合う姓"):
        fake.nasty_last_name(include={"ivs"}, exclude={"kanji_variant"})


def test_nasty_last_name_is_reproducible(data_dir: Path) -> None:
    def sample(seed: int) -> list[str]:
        fake = make_faker(data_dir, seed=seed)
        return [fake.nasty_last_name() for _ in range(20)]

    assert sample(3) == sample(3)


def _person_provider(fake: Faker) -> PersonProvider:
    return next(p for p in fake.get_providers() if isinstance(p, PersonProvider))


def test_nasty_share_zero_keeps_previous_results(data_dir: Path) -> None:
    # nasty_share が 0 のときは乱数を余分に使わず、姓の候補だけから選ぶ（0.3.0 と同じ結果）
    fake = make_faker(data_dir, seed=42)
    rng = random.Random(42)
    expected = [_person_provider(fake)._surnames.pick(rng)[0] for _ in range(200)]
    assert [fake.last_name() for _ in range(200)] == expected


def test_nasty_share_mixes_catalog_surnames(data_dir: Path) -> None:
    share = 0.2
    fake = make_faker(data_dir, nasty_share=share, nasty_exclude=frozenset({"ivs"}))
    # 「佐々木」「林」などは通常の姓の候補にも含まれるので、カタログにしかない姓だけを数える
    regular = {pair[0] for pair in _person_provider(fake)._surnames._items}
    mix = surname_cases(exclude={"ivs"})
    exclusive = {c.value for c in mix} - regular
    expected = share * sum(c.value in exclusive for c in mix) / len(mix)

    n = 20_000
    names = [fake.last_name() for _ in range(n)]
    observed = sum(name in exclusive for name in names) / n
    assert abs(observed - expected) < 0.02
    assert not {c.value for c in CASES if "ivs" in c.tags} & set(names)


def test_nasty_share_applies_to_name_pair(data_dir: Path) -> None:
    fake = make_faker(data_dir, nasty_share=0.5)
    pairs = {case.pair for case in CASES}
    regular = {pair for pair in _person_provider(fake)._surnames._items}
    for _ in range(500):
        kanji, kana, romaji = fake.name_pair()
        last = (kanji.split(" ")[0], kana.split(" ")[0], romaji.split(" ")[1])
        assert last in pairs or last in regular  # 混ざった姓も読みとローマ字が対応している


def test_nasty_exclude_that_removes_everything_is_rejected(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="混ぜる姓がなくなりました"):
        make_faker(data_dir, nasty_share=0.1, nasty_exclude=frozenset(TAGS))


def test_invalid_nasty_share(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="nasty_share"):
        make_faker(data_dir, nasty_share=1.0)
