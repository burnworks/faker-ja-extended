"""郵便番号データ（KEN_ALL）由来の実在住所を返す Provider。

都道府県・市区町村・町域・郵便番号は、すべて同じ 1 件のレコードから取るので整合が取れている。
丁目以降（番地・号・建物名）は付けない。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from faker.providers.address.ja_JP import Provider as JaAddressProvider

from faker_ja_extended._data import ADDRESSES_FILE, default_data_dir, read_dataset


@dataclass(frozen=True, slots=True)
class AddressRecord:
    postcode: str
    """郵便番号（7 桁、ハイフンなし）"""
    lg_code: str
    """全国地方公共団体コード（5 桁）"""
    prefecture: str
    prefecture_kana: str
    city: str
    city_kana: str
    town: str
    """町域名。市区町村全域が 1 つの郵便番号の場合などは空文字"""
    town_kana: str
    town_raw: str
    """掃除する前の元データの町域名（「（１～１９丁目）」などの注記を含む）"""

    @property
    def postcode_hyphenated(self) -> str:
        return f"{self.postcode[:3]}-{self.postcode[3:]}"

    @property
    def address(self) -> str:
        return f"{self.prefecture}{self.city}{self.town}"

    @property
    def address_kana(self) -> str:
        return f"{self.prefecture_kana}{self.city_kana}{self.town_kana}"


class Provider(JaAddressProvider):
    """ja_JP の住所 Provider を、実在の郵便番号・住所で置き換える。"""

    data_dir: ClassVar[Path | None] = None
    """データの場所。None なら既定の場所（環境変数 FAKER_JA_EXTENDED_DATA_DIR など）を使う"""

    def __init__(self, generator) -> None:
        super().__init__(generator)
        path = (self.data_dir or default_data_dir()) / ADDRESSES_FILE
        _, self._records = read_dataset(path)

    def address_record(self) -> AddressRecord:
        """実在する郵便番号と住所の組を 1 件返す。

        :example: AddressRecord(postcode='1500022', prefecture='東京都', city='渋谷区',
            town='恵比寿南', ...)
        """
        # random_element は大きな配列で遅くなるので、Faker の乱数で添字を直接選ぶ
        # （self.generator.random を使うことで seed_instance による再現性が保たれる）
        index = self.generator.random.randrange(len(self._records))
        return AddressRecord(*self._records[index])

    def address(self) -> str:
        """都道府県から町域までの住所を返す（丁目以降は付けない）。

        :example: '東京都渋谷区恵比寿南'
        """
        return self.address_record().address

    def postcode(self) -> str:
        """実在する郵便番号を返す（Faker の ja_JP と同じハイフン付きの形式）。

        単独で呼ぶと address() とは別のレコードから選ばれる。
        住所と対応させたい場合は address_record() を使う。

        :example: '150-0022'
        """
        return self.address_record().postcode_hyphenated

    def zipcode(self) -> str:
        return self.postcode()

    def address_with_postcode(self) -> str:
        """郵便番号付きの住所を返す。

        :example: '〒150-0022 東京都渋谷区恵比寿南'
        """
        record = self.address_record()
        return f"〒{record.postcode_hyphenated} {record.address}"
