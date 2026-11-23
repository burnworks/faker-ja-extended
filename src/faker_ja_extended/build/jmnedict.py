"""JMnedict（EDRDG の日本語固有名詞辞書）から姓と名のデータをビルドする。

元データ: https://www.edrdg.org/enamdict/enamdict_doc.html
ライセンス: CC BY-SA 4.0（https://www.edrdg.org/edrdg/license.html）
ビルドしたデータは JMnedict の派生物になるため、同じライセンスに従う。

name_type が姓・名のエントリについて、漢字表記と読みの組を取り出す。
読みに re_restr（その読みが対応する漢字表記の限定）がある場合はそれに従う。
"""

from __future__ import annotations

import gzip
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from contextlib import ExitStack
from pathlib import Path

from faker_ja_extended.kana import hira_to_kata, is_hiragana, kata_to_hira, to_hepburn

SOURCE_URL = "http://ftp.edrdg.org/pub/Nihongo/JMnedict.xml.gz"
SOURCE_PAGE = "https://www.edrdg.org/enamdict/enamdict_doc.html"
LICENSE_URL = "https://www.edrdg.org/edrdg/license.html"
ATTRIBUTION = (
    "This data is derived from the JMnedict dictionary file, which is the property of "
    "the Electronic Dictionary Research and Development Group (EDRDG), and is used in "
    "conformance with the Group's licence (CC BY-SA 4.0). "
    f"{LICENSE_URL}"
)

SURNAME_TYPE = "family or surname"
FEMALE_TYPE = "female given name or forename"
MALE_TYPE = "male given name or forename"
GIVEN_TYPE = "given name or forename, gender not specified"
GIVEN_NAME_TYPES = frozenset({FEMALE_TYPE, MALE_TYPE, GIVEN_TYPE})

# 名前の表記として受け入れる文字: 漢字（拡張領域・互換漢字を含む）、々、ヶ、ノ、ひらがな、カタカナ
_NAME_CHARS = re.compile(
    r"^[々ヶノぁ-ゖァ-ヺー"
    r"㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]+$"
)

# 性別の振り分けに使う名の語尾（漢字表記の最後の 1 文字）。
# JMnedict の性別の分類は不完全なので、語尾がはっきりしているものはこちらを優先する。
MALE_SUFFIXES = frozenset("郎朗夫雄彦助介輔蔵造衛男之也哉吉")
FEMALE_SUFFIXES = frozenset("子美香恵江代奈菜絵枝乃花")

FEMALE = "female"
MALE = "male"
BOTH = "both"


def iter_name_entries(path: Path) -> Iterator[tuple[frozenset[str], str, str]]:
    """JMnedict の XML（.gz も可）から (name_type の集合, 漢字表記, 読み) を順に返す。

    JMnedict は信頼できる配布元のデータで、エンティティは DTD の内部サブセットで定義されている。
    巨大なファイルなので、iterparse で 1 エントリずつ処理してメモリを解放する。
    漢字表記のないエントリ（かなだけの名前）は対象外。
    """
    with ExitStack() as stack:
        if path.suffix == ".gz":
            f = stack.enter_context(gzip.open(path, "rb"))
        else:
            f = stack.enter_context(open(path, "rb"))
        context = ET.iterparse(f, events=("start", "end"))
        _, root = next(context)
        for event, elem in context:
            if event != "end" or elem.tag != "entry":
                continue
            types = frozenset(t.text for t in elem.iter("name_type") if t.text)
            if SURNAME_TYPE in types or types & GIVEN_NAME_TYPES:
                kebs = [k.text for k in elem.iter("keb") if k.text]
                for r_ele in elem.findall("r_ele"):
                    reb = r_ele.findtext("reb")
                    if not reb:
                        continue
                    restr = {x.text for x in r_ele.findall("re_restr")}
                    for keb in kebs:
                        if not restr or keb in restr:
                            yield types, keb, reb
            root.clear()


def iter_surname_entries(path: Path) -> Iterator[tuple[str, str]]:
    """姓のエントリの (漢字表記, 読み) を順に返す。"""
    for types, kanji, reading in iter_name_entries(path):
        if SURNAME_TYPE in types:
            yield kanji, reading


def iter_given_name_entries(path: Path) -> Iterator[tuple[str, str, frozenset[str]]]:
    """名のエントリの (漢字表記, 読み, 名の name_type の集合) を順に返す。"""
    for types, kanji, reading in iter_name_entries(path):
        given = types & GIVEN_NAME_TYPES
        if given:
            yield kanji, reading, given


def classify_gender(kanji: str, types: Iterable[str]) -> str:
    """名を女性（female）・男性（male）・両方（both）に振り分ける。

    1. 語尾がはっきりしている場合は語尾で決める（〜郎・〜彦なら男性、〜子・〜美なら女性）
    2. JMnedict で女性と男性の両方に分類されていれば両方
    3. 女性に分類されていれば女性
    4. それ以外（男性、または性別の指定なし）は男性。
       JMnedict で性別の指定がない名は、実データを見るとほとんどが男性名のため
    """
    types = set(types)
    last = kanji[-1]
    if last in MALE_SUFFIXES:
        return MALE
    if last in FEMALE_SUFFIXES:
        return FEMALE
    if FEMALE_TYPE in types and MALE_TYPE in types:
        return BOTH
    if FEMALE_TYPE in types:
        return FEMALE
    return MALE


def _normalize(kanji: str, reading: str, skipped: dict[str, int]) -> tuple[str, str, str] | None:
    """表記と読みを検証し、(漢字, ひらがな, ローマ字) を返す。使えないものは None。"""
    if not _NAME_CHARS.match(kanji):
        skipped["invalid_chars"] += 1
        return None
    hira = kata_to_hira(reading)
    if not is_hiragana(hira):
        skipped["invalid_reading"] += 1
        return None
    try:
        romaji = to_hepburn(hira)
    except ValueError:
        skipped["invalid_reading"] += 1
        return None
    return kanji, hira, romaji


def build_records(
    entries: Iterable[tuple[str, str]],
) -> tuple[list[list[str]], dict[str, int]]:
    """姓の (漢字表記, 読み) から (漢字, カタカナ, ローマ字) のレコードを作る。

    戻り値は (レコード, 除外した件数の内訳)。
    """
    seen: set[tuple[str, str]] = set()
    records: list[list[str]] = []
    skipped = {"invalid_chars": 0, "invalid_reading": 0, "duplicate": 0}
    for kanji, reading in entries:
        normalized = _normalize(kanji, reading, skipped)
        if normalized is None:
            continue
        kanji, hira, romaji = normalized
        if (kanji, hira) in seen:
            skipped["duplicate"] += 1
            continue
        seen.add((kanji, hira))
        records.append([kanji, hira_to_kata(hira), romaji])
    records.sort()
    return records, skipped


def build_given_name_records(
    entries: Iterable[tuple[str, str, frozenset[str]]],
) -> tuple[list[list[str]], dict[str, int]]:
    """名の (漢字表記, 読み, name_type) から (漢字, カタカナ, ローマ字, 性別) のレコードを作る。

    同じ表記と読みが複数のエントリにある場合は、name_type を合わせてから性別を決める。
    戻り値は (レコード, 除外した件数の内訳)。
    """
    skipped = {"invalid_chars": 0, "invalid_reading": 0, "duplicate": 0}
    merged: dict[tuple[str, str], tuple[str, set[str]]] = {}
    for kanji, reading, types in entries:
        normalized = _normalize(kanji, reading, skipped)
        if normalized is None:
            continue
        kanji, hira, romaji = normalized
        if (kanji, hira) in merged:
            skipped["duplicate"] += 1
            merged[(kanji, hira)][1].update(types)
        else:
            merged[(kanji, hira)] = (romaji, set(types))
    records = [
        [kanji, hira_to_kata(hira), romaji, classify_gender(kanji, types)]
        for (kanji, hira), (romaji, types) in merged.items()
    ]
    records.sort()
    return records, skipped
