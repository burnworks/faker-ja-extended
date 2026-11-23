"""JMnedict（EDRDG の日本語固有名詞辞書）から姓データをビルドする。

元データ: https://www.edrdg.org/enamdict/enamdict_doc.html
ライセンス: CC BY-SA 4.0（https://www.edrdg.org/edrdg/license.html）
ビルドしたデータは JMnedict の派生物になるため、同じライセンスに従う。

name_type が「family or surname」のエントリについて、漢字表記と読みの組を取り出す。
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

# 姓の表記として受け入れる文字: 漢字（拡張領域・互換漢字を含む）、々、ヶ、ノ、ひらがな、カタカナ
_SURNAME_CHARS = re.compile(
    r"^[々ヶノぁ-ゖァ-ヺー"
    r"㐀-䶿一-鿿豈-﫿\U00020000-\U0003134f]+$"
)


def iter_surname_entries(path: Path) -> Iterator[tuple[str, str]]:
    """JMnedict の XML（.gz も可）から (漢字表記, 読み) を順に返す。

    JMnedict は信頼できる配布元のデータで、エンティティは DTD の内部サブセットで定義されている。
    巨大なファイルなので、iterparse で 1 エントリずつ処理してメモリを解放する。
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
            types = {t.text for t in elem.iter("name_type")}
            if SURNAME_TYPE in types:
                kebs = [k.text for k in elem.iter("keb") if k.text]
                for r_ele in elem.findall("r_ele"):
                    reb = r_ele.findtext("reb")
                    if not reb:
                        continue
                    restr = {x.text for x in r_ele.findall("re_restr")}
                    for keb in kebs:
                        if not restr or keb in restr:
                            yield keb, reb
            root.clear()


def build_records(
    entries: Iterable[tuple[str, str]],
) -> tuple[list[list[str]], dict[str, int]]:
    """(漢字表記, 読み) から (漢字, カタカナ, ローマ字) のレコードを作る。

    戻り値は (レコード, 除外した件数の内訳)。
    """
    seen: set[tuple[str, str]] = set()
    records: list[list[str]] = []
    skipped = {"invalid_chars": 0, "invalid_reading": 0, "duplicate": 0}
    for kanji, reading in entries:
        if not _SURNAME_CHARS.match(kanji):
            skipped["invalid_chars"] += 1
            continue
        hira = kata_to_hira(reading)
        if not is_hiragana(hira):
            skipped["invalid_reading"] += 1
            continue
        try:
            romaji = to_hepburn(hira)
        except ValueError:
            skipped["invalid_reading"] += 1
            continue
        key = (kanji, hira)
        if key in seen:
            skipped["duplicate"] += 1
            continue
        seen.add(key)
        records.append([kanji, hira_to_kata(hira), romaji])
    records.sort()
    return records, skipped
