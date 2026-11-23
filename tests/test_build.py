from pathlib import Path

import pytest

from faker_ja_extended.build import jmnedict, ken_all


@pytest.mark.parametrize(
    ("town", "kana", "city", "expected"),
    [
        ("恵比寿南", "エビスミナミ", "渋谷区", [("恵比寿南", "エビスミナミ")]),
        ("以下に掲載がない場合", "イカニケイサイガナイバアイ", "渋谷区", []),
        ("大通西（１～１９丁目）", "オオドオリニシ（１－１９チョウメ）", "札幌市中央区",
         [("大通西", "オオドオリニシ")]),
        ("西新宿新宿アイランドタワー（１階）", "", "新宿区", []),
        ("西新宿新宿アイランドタワー（地階・階層不明）", "", "新宿区", []),
        ("軽井沢町一円", "カルイザワマチイチエン", "北佐久郡軽井沢町", [("", "")]),
        ("一円", "イチエン", "犬上郡多賀町", [("一円", "イチエン")]),
        ("三宅島三宅村の次に番地がくる場合", "", "三宅島三宅村", [("", "")]),
        # 番地の範囲が入る書き方
        ("小菅村の次に６６４番地以降がくる場合", "", "北都留郡小菅村", [("", "")]),
        ("琴平町の次に１〜４２６番地がくる場合（川東）", "", "仲多度郡琴平町", [("", "")]),
        # 実在の町域名に含まれる丁目・番町・地割はそのまま
        ("象潟町５丁目塩越", "キサカタマチ５チョウメシオコシ", "にかほ市",
         [("象潟町５丁目塩越", "キサカタマチ５チョウメシオコシ")]),
        ("杉名畑４４地割（湯田ダム管理事務所、後口山、当楽）", "スギナハタ４４チワリ（ユダダムカンリジムショ、ウシログチヤマ、トウラク）",
         "和賀郡西和賀町", [("杉名畑４４地割", "スギナハタ４４チワリ")]),
        # 読点で並べた町域は分ける
        ("甲、乙（港新町）", "コウ、オツ（ミナトシンマチ）", "小豆郡土庄町", [("甲", "コウ"), ("乙", "オツ")]),
        ("樺沢１６地割、樺沢１７地割", "カバサワ１６チワリ、カバサワ１７チワリ", "和賀郡西和賀町",
         [("樺沢１６地割", "カバサワ１６チワリ"), ("樺沢１７地割", "カバサワ１７チワリ")]),
        # 漢字とカナで数が合わなければ分けない
        ("甲、乙", "コウオツ", "小豆郡土庄町", [("甲、乙", "コウオツ")]),
        # 地割の範囲は展開する（カナ側の範囲記号は U+2212）
        ("種市第８地割〜第１０地割（玉川、戸類家）", "タネイチダイ８チワリ−ダイ１０チワリ（タマガワ、トルイケ）",
         "九戸郡洋野町",
         [("種市第８地割", "タネイチダイ８チワリ"), ("種市第９地割", "タネイチダイ９チワリ"),
          ("種市第１０地割", "タネイチダイ１０チワリ")]),
        ("左草１地割〜左草３地割", "サソウ１チワリ−サソウ３チワリ", "和賀郡西和賀町",
         [("左草１地割", "サソウ１チワリ"), ("左草２地割", "サソウ２チワリ"), ("左草３地割", "サソウ３チワリ")]),
        # 漢字とカナで範囲が食い違えば展開しない
        ("左草１地割〜左草３地割", "サソウ１チワリ−サソウ４チワリ", "和賀郡西和賀町",
         [("左草１地割〜左草３地割", "サソウ１チワリ−サソウ４チワリ")]),
    ],
)  # fmt: skip
def test_clean_town(town: str, kana: str, city: str, expected) -> None:
    assert ken_all.clean_town(town, kana, city) == expected


def test_build_address_records(ken_all_zip: Path) -> None:
    records = ken_all.build_records(ken_all.iter_rows(ken_all_zip))
    by_postcode = {r[0]: r for r in records}

    # 除外: 以下に掲載がない場合、ビルの階 2 件、廃止。重複 1 件はまとめる
    # 追加: 地割の範囲（３件に展開）、読点の並び（２件に分割）
    assert len(records) == 11
    assert [r[6] for r in records if r[0] == "0287901"] == [
        "種市第１２地割",
        "種市第１３地割",
        "種市第１４地割",
    ]
    assert sorted(r[6] for r in records if r[0] == "7614102") == ["乙", "甲"]
    assert "1500000" not in by_postcode
    assert "1509999" not in by_postcode
    assert by_postcode["0600042"][6] == "大通西"
    assert by_postcode["0600042"][8] == "大通西（１～１９丁目）"  # 元の町域名は残す
    assert by_postcode["0285102"][6:8] == ["葛巻", "クズマキ"]
    assert by_postcode["3890199"][6] == ""
    assert by_postcode["5220341"][6] == "一円"
    assert [r[0] for r in records] == sorted(r[0] for r in records)


def test_build_address_records_rejects_unexpected_columns() -> None:
    with pytest.raises(ValueError):
        ken_all.build_records([["13113", "1500022"]])


def test_iter_surname_entries(jmnedict_gz: Path) -> None:
    entries = list(jmnedict.iter_surname_entries(jmnedict_gz))
    assert ("髙橋", "たかはし") in entries
    assert {r for k, r in entries if k == "新谷"} == {"あらたに", "しんたに", "にいや"}
    # re_restr: 「こや」は「小埜」だけ
    assert ("小埜", "こや") in entries
    assert ("小野", "こや") not in entries
    # 地名だけ・名前だけのエントリは含まない
    assert all(k not in ("渋谷", "翼") for k, _ in entries)


def test_build_surname_records(jmnedict_gz: Path) -> None:
    records, skipped = jmnedict.build_records(jmnedict.iter_surname_entries(jmnedict_gz))
    assert ["髙橋", "タカハシ", "Takahashi"] in records
    assert ["服部", "ハットリ", "Hattori"] in records
    assert ["𠮷田", "ヨシダ", "Yoshida"] in records
    assert all(r[0] != "ＡＢＣ" for r in records)
    assert skipped["invalid_chars"] == 1


def test_write_dataset_if_changed_compares_content(tmp_path: Path) -> None:
    import gzip

    from faker_ja_extended._data import write_dataset, write_dataset_if_changed

    path = tmp_path / "data.json.gz"
    meta, records = {"count": 1}, [["a", "b"]]
    write_dataset(path, meta, records)

    # 圧縮レベルを変えて書き直し、内容は同じでバイト列だけが違う状態を再現する
    original = gzip.decompress(path.read_bytes())
    path.write_bytes(gzip.compress(original, compresslevel=1, mtime=0))
    recompressed = path.read_bytes()

    assert write_dataset_if_changed(path, meta, records) is False
    assert path.read_bytes() == recompressed  # 内容が同じならファイルに触れない

    assert write_dataset_if_changed(path, meta, [["a", "c"]]) is True
    assert gzip.decompress(path.read_bytes()) != original


@pytest.mark.parametrize(
    ("kanji", "types", "expected"),
    [
        # 語尾がはっきりしていれば、JMnedict の分類より語尾を優先する
        ("大輔", {jmnedict.FEMALE_TYPE}, jmnedict.MALE),
        ("一郎", {jmnedict.GIVEN_TYPE}, jmnedict.MALE),
        ("花子", {jmnedict.MALE_TYPE}, jmnedict.FEMALE),
        # 語尾で決まらなければ分類に従う
        ("薫", {jmnedict.FEMALE_TYPE, jmnedict.MALE_TYPE}, jmnedict.BOTH),
        ("美咲", {jmnedict.FEMALE_TYPE}, jmnedict.FEMALE),
        ("翼", {jmnedict.MALE_TYPE}, jmnedict.MALE),
        # 性別の指定がなければ男性（実データでは大半が男性名のため）
        ("盛貞", {jmnedict.GIVEN_TYPE}, jmnedict.MALE),
    ],
)
def test_classify_gender(kanji: str, types: set[str], expected: str) -> None:
    assert jmnedict.classify_gender(kanji, types) == expected


def test_build_given_name_records(jmnedict_gz: Path) -> None:
    records, skipped = jmnedict.build_given_name_records(
        jmnedict.iter_given_name_entries(jmnedict_gz)
    )
    by_key = {(r[0], r[1]): r for r in records}
    assert by_key[("大輔", "ダイスケ")] == ["大輔", "ダイスケ", "Daisuke", "male"]
    assert by_key[("美咲", "ミサキ")][3] == "female"
    assert by_key[("薫", "カオル")][3] == "both"
    assert by_key[("盛貞", "モリサダ")][3] == "male"
    assert {r[1] for r in records if r[0] == "愛"} == {"アイ", "マナ", "メグミ"}
    # 姓だけのエントリは含まない
    assert ("髙橋", "タカハシ") not in by_key
    assert skipped["invalid_chars"] == 1  # Ｍａｒｙ
