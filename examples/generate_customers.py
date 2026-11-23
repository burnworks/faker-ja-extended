"""顧客のテストデータを CSV に出力する例。

    uv run python examples/generate_customers.py --count 10000 --output customers.csv
    uv run python examples/generate_customers.py --count 100 --nasty-share 0.05 --seed 1

事前に `faker-ja-extended build --only surnames` で姓のデータをビルドしておく。
--extended-first-names を使う場合は、`--only surnames given_names` でビルドする。
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TextIO

from faker import Faker

from faker_ja_extended import AddressProvider, PersonProvider

FIELDS = [
    "customer_id",
    "last_name",
    "first_name",
    "last_name_kana",
    "first_name_kana",
    "last_name_romaji",
    "first_name_romaji",
    "email",
    "postcode",
    "prefecture",
    "city",
    "town",
]


def make_faker(seed: int, *, extended_first_names: bool, nasty_share: float) -> Faker:
    person = type(
        "CustomerPersonProvider",
        (PersonProvider,),
        {
            "extended_first_name_share": 0.5 if extended_first_names else 0.0,
            "nasty_share": nasty_share,
        },
    )
    fake = Faker("ja_JP")
    fake.add_provider(person)
    fake.add_provider(AddressProvider)
    fake.seed_instance(seed)
    return fake


def generate(fake: Faker, count: int) -> Iterator[dict[str, str]]:
    for i in range(1, count + 1):
        last_name, last_kana, last_romaji = fake.last_name_pair()
        first_name, first_kana, first_romaji = fake.first_name_pair()
        address = fake.address_record()
        yield {
            "customer_id": f"C{i:07d}",
            "last_name": last_name,
            "first_name": first_name,
            "last_name_kana": last_kana,
            "first_name_kana": first_kana,
            "last_name_romaji": last_romaji,
            "first_name_romaji": first_romaji,
            # 一意にするため連番から作る。example.com は例示用に予約されたドメインで、誰にも届かない
            "email": f"customer{i:07d}@example.com",
            "postcode": address.postcode_hyphenated,
            "prefecture": address.prefecture,
            "city": address.city,
            "town": address.town,
        }


def write_csv(out: TextIO, rows: Iterable[dict[str, str]]) -> None:
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="顧客のテストデータを CSV に出力する")
    parser.add_argument("--count", type=int, default=100, help="件数（既定: %(default)s）")
    parser.add_argument("--seed", type=int, default=0, help="シード（既定: %(default)s）")
    parser.add_argument("--output", type=Path, help="出力先（省略すると標準出力）")
    parser.add_argument(
        "--extended-first-names", action="store_true", help="名も JMnedict の名で拡張する"
    )
    parser.add_argument(
        "--nasty-share", type=float, default=0.0, help="意地悪な姓を混ぜる割合（既定: 0）"
    )
    parser.add_argument(
        "--excel", action="store_true", help="Excel で開けるよう BOM 付きの UTF-8 で出力する"
    )
    args = parser.parse_args()

    fake = make_faker(
        args.seed, extended_first_names=args.extended_first_names, nasty_share=args.nasty_share
    )
    rows = generate(fake, args.count)
    if args.output:
        encoding = "utf-8-sig" if args.excel else "utf-8"
        with open(args.output, "w", encoding=encoding, newline="") as f:
            write_csv(f, rows)
    else:
        write_csv(sys.stdout, rows)


if __name__ == "__main__":
    main()
