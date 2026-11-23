from __future__ import annotations

import csv
import gzip
import io
import zipfile
from pathlib import Path

import pytest

from faker_ja_extended.build.cli import main as cli_main

# 実データの癖を再現したテスト用の行（郵便番号・コードの一部は架空）
KEN_ALL_ROWS = [
    # 通常の町域
    ["13113", "150  ", "1500022", "トウキョウト", "シブヤク", "エビスミナミ",
     "東京都", "渋谷区", "恵比寿南", "0", "0", "1", "0", "0", "0"],
    # 「以下に掲載がない場合」→ 除外
    ["13113", "150  ", "1500000", "トウキョウト", "シブヤク", "イカニケイサイガナイバアイ",
     "東京都", "渋谷区", "以下に掲載がない場合", "0", "0", "0", "0", "0", "0"],
    # 括弧書きの注記 → 取り除く
    ["01101", "060  ", "0600042", "ホッカイドウ", "サッポロシチュウオウク", "オオドオリニシ（１－１９チョウメ）",
     "北海道", "札幌市中央区", "大通西（１～１９丁目）", "1", "0", "1", "0", "0", "0"],
    # 地割の注記（括弧の中に「」を含む）
    ["03302", "028  ", "0285102", "イワテケン", "イワテグンクズマキマチ",
     "クズマキ（ダイ４０チワリ「５７バンチ１２５、１７６ヲノゾク」－ダイ４５チワリ）",
     "岩手県", "岩手郡葛巻町", "葛巻（第４０地割「５７番地１２５、１７６を除く」～第４５地割）",
     "0", "1", "0", "0", "0", "0"],
    # 高層ビルの階ごとの郵便番号 → 除外
    ["13104", "160  ", "1636090", "トウキョウト", "シンジュクク", "ニシシンジュクシンジュクアイランドタワー（チカイ・カイソウフメイ）",
     "東京都", "新宿区", "西新宿新宿アイランドタワー（地階・階層不明）", "0", "0", "0", "0", "0", "0"],
    ["13104", "160  ", "1636001", "トウキョウト", "シンジュクク", "ニシシンジュクシンジュクアイランドタワー（１カイ）",
     "東京都", "新宿区", "西新宿新宿アイランドタワー（１階）", "0", "0", "0", "0", "0", "0"],
    # 「○○町一円」→ 町域なし
    ["20321", "389  ", "3890199", "ナガノケン", "キタサクグンカルイザワマチ", "カルイザワマチイチエン",
     "長野県", "北佐久郡軽井沢町", "軽井沢町一円", "0", "0", "0", "0", "0", "0"],
    # 町域名がそのまま「一円」の実在地名 → 残す
    ["25443", "522  ", "5220341", "シガケン", "イヌカミグンタガチョウ", "イチエン",
     "滋賀県", "犬上郡多賀町", "一円", "0", "0", "0", "0", "0", "0"],
    # 「○○の次に番地がくる場合」→ 町域なし
    ["13364", "100  ", "1001299", "トウキョウト", "ミヤケムラ", "ミヤケムラノツギニバンチガクルバアイ",
     "東京都", "三宅島三宅村", "三宅島三宅村の次に番地がくる場合", "0", "0", "0", "0", "0", "0"],
    # 廃止 → 除外
    ["13113", "150  ", "1509999", "トウキョウト", "シブヤク", "ハイシチョウ",
     "東京都", "渋谷区", "廃止町", "0", "0", "0", "0", "2", "6"],
    # 地割の範囲 → 展開する（カナ側の範囲記号は U+2212）
    ["03507", "02879", "0287901", "イワテケン", "クノヘグンヒロノチョウ", "タネイチダイ１２チワリ−ダイ１４チワリ（タマガワ、トルイケ）",
     "岩手県", "九戸郡洋野町", "種市第１２地割〜第１４地割（玉川、戸類家）", "0", "1", "0", "0", "0", "0"],
    # 読点で並べた町域 → 分ける
    ["37322", "761  ", "7614102", "カガワケン", "ショウズグントノショウチョウ", "コウ、オツ（ミナトシンマチ）",
     "香川県", "小豆郡土庄町", "甲、乙（港新町）", "1", "0", "0", "1", "0", "0"],
    # 掃除すると重複する行 → 1 件にまとめる
    ["01101", "060  ", "0600042", "ホッカイドウ", "サッポロシチュウオウク", "オオドオリニシ（ソノタ）",
     "北海道", "札幌市中央区", "大通西（その他）", "1", "0", "1", "0", "0", "0"],
]  # fmt: skip

JMNEDICT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE JMnedict [
<!ELEMENT JMnedict (entry*)>
<!ENTITY surname "family or surname">
<!ENTITY given "given name or forename, gender not specified">
<!ENTITY place "place name">
]>
<JMnedict>
<entry><ent_seq>1</ent_seq>
<k_ele><keb>髙橋</keb></k_ele>
<r_ele><reb>たかはし</reb></r_ele>
<trans><name_type>&surname;</name_type><trans_det>Takahashi</trans_det></trans></entry>
<entry><ent_seq>2</ent_seq>
<k_ele><keb>新谷</keb></k_ele>
<r_ele><reb>あらたに</reb></r_ele><r_ele><reb>しんたに</reb></r_ele><r_ele><reb>にいや</reb></r_ele>
<trans><name_type>&surname;</name_type><name_type>&place;</name_type></trans></entry>
<entry><ent_seq>3</ent_seq>
<k_ele><keb>小野</keb></k_ele><k_ele><keb>小埜</keb></k_ele>
<r_ele><reb>おの</reb></r_ele>
<r_ele><reb>こや</reb><re_restr>小埜</re_restr></r_ele>
<trans><name_type>&surname;</name_type></trans></entry>
<entry><ent_seq>4</ent_seq>
<k_ele><keb>渋谷</keb></k_ele>
<r_ele><reb>しぶや</reb></r_ele>
<trans><name_type>&place;</name_type></trans></entry>
<entry><ent_seq>5</ent_seq>
<k_ele><keb>ＡＢＣ</keb></k_ele>
<r_ele><reb>えーびーしー</reb></r_ele>
<trans><name_type>&surname;</name_type></trans></entry>
<entry><ent_seq>6</ent_seq>
<k_ele><keb>佐藤</keb></k_ele>
<r_ele><reb>さとう</reb></r_ele>
<trans><name_type>&surname;</name_type></trans></entry>
<entry><ent_seq>7</ent_seq>
<k_ele><keb>服部</keb></k_ele>
<r_ele><reb>はっとり</reb></r_ele>
<trans><name_type>&surname;</name_type></trans></entry>
<entry><ent_seq>8</ent_seq>
<k_ele><keb>𠮷田</keb></k_ele>
<r_ele><reb>よしだ</reb></r_ele>
<trans><name_type>&surname;</name_type></trans></entry>
<entry><ent_seq>9</ent_seq>
<k_ele><keb>翼</keb></k_ele>
<r_ele><reb>つばさ</reb></r_ele>
<trans><name_type>&given;</name_type></trans></entry>
</JMnedict>
"""


@pytest.fixture(scope="session")
def ken_all_zip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    buf = io.StringIO(newline="")
    csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\r\n").writerows(KEN_ALL_ROWS)
    path = tmp_path_factory.mktemp("src") / "utf_ken_all.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("utf_ken_all.csv", buf.getvalue().encode("utf-8"))
    return path


@pytest.fixture(scope="session")
def jmnedict_gz(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("src") / "JMnedict.xml.gz"
    with gzip.open(path, "wb") as f:
        f.write(JMNEDICT_XML.encode("utf-8"))
    return path


@pytest.fixture(scope="session")
def data_dir(
    tmp_path_factory: pytest.TempPathFactory, ken_all_zip: Path, jmnedict_gz: Path
) -> Path:
    """フィクスチャの元データから、CLI でデータをビルドしたディレクトリ。"""
    out = tmp_path_factory.mktemp("data")
    cli_main(
        ["--data-dir", str(out), "build", "--ken-all", str(ken_all_zip),
         "--jmnedict", str(jmnedict_gz)]
    )  # fmt: skip
    return out
