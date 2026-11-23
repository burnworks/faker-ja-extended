"""意地悪な姓のカタログを使ったテストの例。

自分のシステムの関数に置き換えて使う。ここでは例として、
「姓を正規化して保存し、検索する」簡単な顧客ストアをテストする。

    uv run pytest examples/test_nasty_surnames.py

カタログは同梱されているので、データのビルドは不要。
"""

from __future__ import annotations

import unicodedata

import pytest

from faker_ja_extended import NastyCase, surname_cases

# --- テスト対象の例（実際のシステムの関数に置き換える）---


def normalize_name(name: str) -> str:
    """保存・検索の前に名前を正規化する。"""
    return unicodedata.normalize("NFC", name).strip()


def visible_length(name: str) -> int:
    """見た目の文字数を数える（異体字セレクタは数えない）。

    len() はコードポイント数なので、異体字セレクタ付きの文字を 2 文字と数えてしまう。
    """
    return sum(1 for ch in name if not 0xE0100 <= ord(ch) <= 0xE01EF)


def to_cp932(name: str) -> bytes:
    """CP932 の連携先に渡すために変換する。変換できない文字があればエラーにする。"""
    try:
        return name.encode("cp932")
    except UnicodeEncodeError as e:
        raise ValueError(f"CP932 に変換できない文字があります: {name[e.start : e.end]!r}") from e


class CustomerStore:
    def __init__(self) -> None:
        self._customers: dict[int, str] = {}

    def register(self, last_name: str) -> int:
        customer_id = len(self._customers) + 1
        self._customers[customer_id] = normalize_name(last_name)
        return customer_id

    def find(self, last_name: str) -> list[int]:
        key = normalize_name(last_name)
        return [cid for cid, name in self._customers.items() if name == key]


def case_id(case: NastyCase) -> str:
    return case.id


# --- テスト ---


@pytest.mark.parametrize("case", surname_cases(), ids=case_id)
def test_register_and_find(case: NastyCase) -> None:
    """どの姓でも、登録した表記で検索できる。"""
    store = CustomerStore()
    customer_id = store.register(case.value)
    assert customer_id in store.find(case.value)


@pytest.mark.parametrize("case", surname_cases(include={"nfc_changes"}), ids=case_id)
def test_compat_ideograph_is_found_by_standard_form(case: NastyCase) -> None:
    """互換漢字で登録した姓も、正規化しているので標準の表記で検索できる。"""
    store = CustomerStore()
    customer_id = store.register(case.value)
    assert customer_id in store.find(case.base)


@pytest.mark.parametrize("case", surname_cases(include={"ivs", "surrogate_pair"}), ids=case_id)
def test_length_counts_what_users_see(case: NastyCase) -> None:
    """見た目の文字数は、標準の表記と同じになる（len() では一致しない）。"""
    assert visible_length(case.value) == len(case.base)


@pytest.mark.parametrize("case", surname_cases(include={"cp932_unmappable"}), ids=case_id)
def test_cp932_export_rejects_unmappable_names(case: NastyCase) -> None:
    """CP932 に変換できない姓は、黙って文字化けさせずにエラーにする。"""
    with pytest.raises(ValueError, match="CP932 に変換できない"):
        to_cp932(case.value)


@pytest.mark.parametrize("case", surname_cases(exclude={"cp932_unmappable"}), ids=case_id)
def test_cp932_export_roundtrips(case: NastyCase) -> None:
    """CP932 に変換できる姓は、元に戻しても同じ表記になる。"""
    assert to_cp932(case.value).decode("cp932") == case.value
