from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest
from faker import Faker
from faker.providers.person.ja_JP import Provider as JaPersonProvider

from faker_ja_extended import AddressProvider, AddressRecord, PersonProvider
from faker_ja_extended._data import SURNAMES_FILE, DataNotBuiltError, read_dataset
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
    assert "addresses.json.gz: 11 件" in out
    assert "surnames.json.gz:" in out
