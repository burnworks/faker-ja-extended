from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest
from faker import Faker
from faker.providers.person.ja_JP import Provider as JaPersonProvider

from faker_ja_extended import AddressProvider, AddressRecord, PersonProvider
from faker_ja_extended._data import (
    ADDRESSES_FILE,
    BUNDLED_DATA_DIR,
    ENV_DATA_DIR,
    GIVEN_NAMES_FILE,
    SURNAMES_FILE,
    DataNotBuiltError,
    read_dataset,
)
from faker_ja_extended.build.cli import main as cli_main


def make_faker(data_dir: Path, share: float = 0.5, seed: int = 42) -> Faker:
    person = type("P", (PersonProvider,), {"data_dir": data_dir, "extended_share": share})
    address = type("A", (AddressProvider,), {"data_dir": data_dir})
    fake = Faker("ja_JP")
    fake.add_provider(person)
    fake.add_provider(address)
    fake.seed_instance(seed)
    return fake


def test_address_record_is_consistent(data_dir: Path) -> None:
    fake = make_faker(data_dir)
    for _ in range(100):
        record = fake.address_record()
        assert isinstance(record, AddressRecord)
        assert re.fullmatch(r"\d{7}", record.postcode)
        assert record.address == f"{record.prefecture}{record.city}{record.town}"
        assert "（" not in record.address  # 注記は取り除かれている
        assert "丁目" not in record.address


def test_address_formats(data_dir: Path) -> None:
    fake = make_faker(data_dir)
    assert re.fullmatch(r"\d{3}-\d{4}", fake.postcode())
    assert re.fullmatch(r"〒\d{3}-\d{4} \S+", fake.address_with_postcode())
    assert fake.zipcode().count("-") == 1


def test_seed_reproducibility(data_dir: Path) -> None:
    def sample(seed: int) -> list:
        fake = make_faker(data_dir, seed=seed)
        return [(fake.address(), fake.name_pair()) for _ in range(50)]

    assert sample(1) == sample(1)
    assert sample(1) != sample(2)


def test_name_pair_is_consistent(data_dir: Path) -> None:
    fake = make_faker(data_dir)
    _, built = read_dataset(data_dir / SURNAMES_FILE)
    last_pairs = set(JaPersonProvider.last_name_pairs) | set(built)
    first_pairs = set(JaPersonProvider.first_name_pairs)
    for _ in range(500):
        kanji, kana, romaji = fake.name_pair()
        last_k, first_k = kanji.split(" ")
        last_r, first_r = kana.split(" ")
        first_rom, last_rom = romaji.split(" ")
        assert (last_k, last_r, last_rom) in last_pairs
        assert (first_k, first_r, first_rom) in first_pairs


def test_extended_surnames_appear_with_expected_share(data_dir: Path) -> None:
    fake = make_faker(data_dir, share=0.5)
    base = {pair[0] for pair in JaPersonProvider.last_name_pairs}
    counts = Counter(fake.last_name() in base for _ in range(20_000))
    assert 0.45 < counts[False] / 20_000 < 0.55


def test_extended_share_zero_keeps_faker_default(data_dir: Path) -> None:
    fake = make_faker(data_dir, share=0.0)
    base = {pair[0] for pair in JaPersonProvider.last_name_pairs}
    assert all(fake.last_name() in base for _ in range(2_000))


def test_invalid_share(data_dir: Path) -> None:
    with pytest.raises(ValueError):
        make_faker(data_dir, share=1.0)


def test_missing_data_raises_helpful_error(tmp_path: Path) -> None:
    with pytest.raises(DataNotBuiltError, match="faker-ja-extended build"):
        make_faker(tmp_path)


def test_info_command(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cli_main(["--data-dir", str(data_dir), "info"])
    out = capsys.readouterr().out
    assert "ビルド済み: 11 件" in out
    assert "同梱データ:" in out
    assert "→ ビルド済みのデータを使います" in out
    assert "名（given_names.json.gz）" in out


# --- データの読み込み先の優先順位 ---


def test_address_falls_back_to_bundled_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))  # ビルド済みのデータがない状態
    provider = AddressProvider(Faker("ja_JP"))
    assert provider.dataset_path == BUNDLED_DATA_DIR / ADDRESSES_FILE
    assert provider.dataset_meta["count"] > 100_000


def test_local_build_is_preferred_over_bundled(monkeypatch, data_dir: Path) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(data_dir))
    provider = AddressProvider(Faker("ja_JP"))
    assert provider.dataset_path == data_dir / ADDRESSES_FILE
    assert provider.dataset_meta["count"] == 11


def test_explicit_data_dir_does_not_fall_back(tmp_path: Path) -> None:
    provider = type("A", (AddressProvider,), {"data_dir": tmp_path})
    with pytest.raises(DataNotBuiltError):
        provider(Faker("ja_JP"))


def test_surnames_are_not_bundled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_DATA_DIR, str(tmp_path))
    assert not (BUNDLED_DATA_DIR / SURNAMES_FILE).exists()
    with pytest.raises(DataNotBuiltError):
        PersonProvider(Faker("ja_JP"))


def test_bundled_address_data_is_clean() -> None:
    meta, records = read_dataset(BUNDLED_DATA_DIR / ADDRESSES_FILE)
    assert meta["count"] == len(records) > 100_000
    assert "built_at" not in meta  # 同じ元データから同じファイルができるよう、日時を含めない
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["source_date"])
    for postcode, lg_code, _, _, _, _, town, town_kana, _ in records:
        assert re.fullmatch(r"\d{7}", postcode)
        assert re.fullmatch(r"\d{5}", lg_code)
        assert not re.search(r"[（）()、]|以下に掲載がない場合|がくる場合", town), town
        assert not re.search(r"[（）()、]", town_kana), town_kana


# --- 名の拡張 ---


def make_faker_with_first_names(data_dir: Path, share: float, seed: int = 7) -> Faker:
    person = type(
        "P",
        (PersonProvider,),
        {"data_dir": data_dir, "extended_first_name_share": share},
    )
    fake = Faker("ja_JP")
    fake.add_provider(person)
    fake.seed_instance(seed)
    return fake


FAKER_FEMALE = {p[0] for p in JaPersonProvider.first_name_female_pairs}
FAKER_MALE = {p[0] for p in JaPersonProvider.first_name_male_pairs}


def test_first_names_are_unchanged_by_default(data_dir: Path) -> None:
    fake = make_faker(data_dir)
    assert all(fake.first_name_female() in FAKER_FEMALE for _ in range(500))
    assert all(fake.first_name_male() in FAKER_MALE for _ in range(500))


def test_given_names_data_is_not_required_by_default(monkeypatch, tmp_path: Path, data_dir) -> None:
    # 姓のデータだけがある状態（名のデータなし）でも、既定の設定なら使える
    (tmp_path / SURNAMES_FILE).write_bytes((data_dir / SURNAMES_FILE).read_bytes())
    fake = make_faker_with_first_names(tmp_path, share=0.0)
    assert fake.first_name()
    with pytest.raises(DataNotBuiltError):
        make_faker_with_first_names(tmp_path, share=0.5)


def test_extended_first_names_respect_gender(data_dir: Path) -> None:
    fake = make_faker_with_first_names(data_dir, share=0.5)
    female = {fake.first_name_female() for _ in range(3_000)}
    male = {fake.first_name_male() for _ in range(3_000)}
    assert {"美咲", "愛", "薫"} <= female
    assert {"大輔", "盛貞", "翼", "薫"} <= male
    assert not {"大輔", "盛貞"} & female  # 男性に振り分けた名は女性として出ない
    assert not {"美咲", "愛"} & male


def test_extended_first_name_share(data_dir: Path) -> None:
    fake = make_faker_with_first_names(data_dir, share=0.3)
    n = 20_000
    added = sum(fake.first_name_female() not in FAKER_FEMALE for _ in range(n))
    assert 0.27 < added / n < 0.33


def test_kanji_with_many_readings_is_not_overrepresented(data_dir: Path) -> None:
    # 「愛」は 3 通りの読みがあるが、漢字表記としては「美咲」と同じくらいの頻度で出る
    fake = make_faker_with_first_names(data_dir, share=0.5)
    counts = Counter(fake.first_name_female() for _ in range(30_000))
    assert 0.7 < counts["愛"] / counts["美咲"] < 1.3


def test_name_pair_with_extended_first_names_is_consistent(data_dir: Path) -> None:
    fake = make_faker_with_first_names(data_dir, share=0.5)
    _, built = read_dataset(data_dir / GIVEN_NAMES_FILE)
    first_pairs = set(JaPersonProvider.first_name_pairs) | {tuple(r[:3]) for r in built}
    for _ in range(500):
        kanji, kana, romaji = fake.name_pair()
        first = (kanji.split(" ")[1], kana.split(" ")[1], romaji.split(" ")[0])
        assert first in first_pairs


def test_invalid_first_name_share(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="extended_first_name_share"):
        make_faker_with_first_names(data_dir, share=1.0)


def test_build_only_given_names(tmp_path: Path, jmnedict_gz: Path) -> None:
    cli_main(
        [
            "--data-dir",
            str(tmp_path),
            "build",
            "--only",
            "given_names",
            "--jmnedict",
            str(jmnedict_gz),
        ]
    )
    assert (tmp_path / GIVEN_NAMES_FILE).exists()
    assert not (tmp_path / SURNAMES_FILE).exists()
    assert (tmp_path / "JMNEDICT_ATTRIBUTION.txt").exists()
    meta, records = read_dataset(tmp_path / GIVEN_NAMES_FILE)
    assert meta["count"] == len(records)
    assert sum(meta["genders"].values()) == len(records)
