"""日本郵便の郵便番号データ（1レコード1行、UTF-8形式）から住所データをビルドする。

元データ: https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html
郵便番号データについて、日本郵便株式会社は著作権を主張していない。

町域名の列には住所ではない説明文や注記が含まれるため、次のように掃除する。

- 「以下に掲載がない場合」は町域を特定しないので除外する
- 「○○町一円」「○○町の次に番地がくる場合」「○○村の次に６６４番地以降がくる場合」は
  町域なし（市区町村まで）として残す
- 括弧書きの注記（「（１～１９丁目）」「（次のビルを除く）」など）は取り除く
- 高層ビルの階ごとの郵便番号（「（１階）」「（地階・階層不明）」）は除外する
- 読点で並べた複数の町域（「甲、乙」「樺沢１６地割、樺沢１７地割」）は 1 件ずつに分ける
- 地割の範囲（「種市第８地割〜第１４地割」）は個別の地割に展開する
- 掃除前の町域名は ``town_raw`` に残す（入力や正規化のテスト用）
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

SOURCE_URL = "https://www.post.japanpost.jp/service/search/zipcode/download/utf/zip/utf_ken_all.zip"
SOURCE_PAGE = "https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html"

# CSV の列（0 始まり）
COL_LG_CODE = 0
COL_POSTCODE = 2
COL_PREF_KANA = 3
COL_CITY_KANA = 4
COL_TOWN_KANA = 5
COL_PREF = 6
COL_CITY = 7
COL_TOWN = 8
COL_UPDATE = 13
UPDATE_ABOLISHED = "2"

NOT_LISTED = "以下に掲載がない場合"
ICHIEN = "一円"

_PAREN = re.compile(r"[（(].*?[）)]")
_FLOOR = re.compile(r"[（(](?:[０-９0-9]+階|地階・階層不明)[）)]")
# 「の次に番地がくる場合」「の次に１〜６６３番地がくる場合」「の次に６６４番地以降がくる場合」
_NEXT_IS_BANCHI = re.compile(r"の次に.*番地.*がくる場合")
# 「種市第８地割〜第１４地割」「左草１地割〜左草６地割」。カナ側の範囲記号は U+2212（−）
_CHIWARI_RANGE = re.compile(
    r"^(?P<pre>.*?)(?P<dai>第?)(?P<start>[０-９]+)地割[〜～−－](?:(?P=pre))?第?(?P<end>[０-９]+)地割$"
)
_CHIWARI_RANGE_KANA = re.compile(
    r"^(?P<pre>.*?)(?P<dai>(?:ダイ)?)(?P<start>[０-９]+)チワリ[−－〜～](?:(?P=pre))?(?:ダイ)?"
    r"(?P<end>[０-９]+)チワリ$"
)
_MAX_RANGE = 200
_TO_FULLWIDTH = str.maketrans("0123456789", "０１２３４５６７８９")

# レコードの列順。Provider 側の AddressRecord と揃える。
FIELDS = (
    "postcode",
    "lg_code",
    "prefecture",
    "prefecture_kana",
    "city",
    "city_kana",
    "town",
    "town_kana",
    "town_raw",
)


def iter_rows(zip_path: Path) -> Iterator[list[str]]:
    """zip に含まれる CSV の行を順に返す。"""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"zip に CSV がちょうど 1 つ含まれている必要があります: {names}")
        with zf.open(names[0]) as raw:
            yield from csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))


def clean_town(town: str, town_kana: str, city: str) -> list[tuple[str, str]]:
    """町域名（漢字・カナ）を住所として使える形にする。

    1 行が複数の町域を表す場合は複数の組を返す。除外する行は空のリストを返す。
    """
    if town == NOT_LISTED:
        return []
    if _FLOOR.search(town):
        return []
    if _NEXT_IS_BANCHI.search(town):
        return [("", "")]
    # 「軽井沢町一円」のように市区町村名＋一円の場合だけ町域なしとみなす。
    # 町域名がそのまま「一円」の地名（滋賀県犬上郡多賀町一円など）は実在するので残す。
    if town.endswith(ICHIEN):
        head = town.removesuffix(ICHIEN)
        if head and city.endswith(head):
            return [("", "")]
    cleaned = _PAREN.sub("", town).strip()
    cleaned_kana = _PAREN.sub("", town_kana).strip()

    results: list[tuple[str, str]] = []
    for part, part_kana in _split_list(cleaned, cleaned_kana):
        results.extend(_expand_chiwari_range(part, part_kana))
    return results


def _split_list(town: str, town_kana: str) -> list[tuple[str, str]]:
    """読点で並べた町域を分ける。漢字とカナで数が合わない場合は分けない。"""
    parts = town.split("、")
    kana_parts = town_kana.split("、")
    if len(parts) == 1 or len(parts) != len(kana_parts):
        return [(town, town_kana)]
    return list(zip(parts, kana_parts, strict=True))


def _expand_chiwari_range(town: str, town_kana: str) -> list[tuple[str, str]]:
    """地割の範囲を個別の地割に展開する。範囲でない、または漢字とカナが合わない場合はそのまま。"""
    m = _CHIWARI_RANGE.match(town)
    mk = _CHIWARI_RANGE_KANA.match(town_kana)
    if not m or not mk:
        return [(town, town_kana)]
    start, end = int(m["start"]), int(m["end"])  # int() は全角数字も解釈できる
    if (start, end) != (int(mk["start"]), int(mk["end"])) or not 0 <= end - start <= _MAX_RANGE:
        return [(town, town_kana)]
    results = []
    for n in range(start, end + 1):
        num = str(n).translate(_TO_FULLWIDTH)
        results.append((f"{m['pre']}{m['dai']}{num}地割", f"{mk['pre']}{mk['dai']}{num}チワリ"))
    return results


def build_records(rows: Iterable[list[str]]) -> list[list[str]]:
    """CSV の行から住所レコードを作る。重複は除き、郵便番号順に並べる。"""
    seen: set[tuple[str, ...]] = set()
    records: list[list[str]] = []
    for row in rows:
        if len(row) < 15:
            raise ValueError(f"列数が想定と異なります（15 列を想定）: {row}")
        if row[COL_UPDATE] == UPDATE_ABOLISHED:
            continue
        for town, town_kana in clean_town(row[COL_TOWN], row[COL_TOWN_KANA], row[COL_CITY]):
            record = [
                row[COL_POSTCODE],
                row[COL_LG_CODE],
                row[COL_PREF],
                row[COL_PREF_KANA],
                row[COL_CITY],
                row[COL_CITY_KANA],
                town,
                town_kana,
                row[COL_TOWN],
            ]
            key = (record[0], record[2], record[4], record[6])
            if key in seen:
                continue
            seen.add(key)
            records.append(record)
    records.sort(key=lambda r: (r[0], r[1], r[7], r[6]))
    return records
