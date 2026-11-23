"""JMnedict 由来の姓で、ja_JP の姓のバリエーションを増やす Provider。

Faker 標準の上位 50 件は元の重み（おおよその人数）のまま残し、
JMnedict から追加した姓には一律の小さい重みを割り当てる。
JMnedict には頻度の情報がないため、追加分の重みは実態の分布を表すものではない。
"""

from __future__ import annotations

from bisect import bisect_right
from itertools import accumulate
from pathlib import Path
from typing import ClassVar

from faker.providers.person.ja_JP import Provider as JaPersonProvider

from faker_ja_extended._data import SURNAMES_FILE, default_data_dir, read_dataset

NamePair = tuple[str, str, str]


class Provider(JaPersonProvider):
    """ja_JP の姓を JMnedict の姓（約 14 万件）まで拡張する。"""

    data_dir: ClassVar[Path | None] = None
    """データの場所。None なら既定の場所（環境変数 FAKER_JA_EXTENDED_DATA_DIR など）を使う"""

    extended_share: ClassVar[float] = 0.5
    """JMnedict から追加した姓が選ばれる割合（0 以上 1 未満）。

    0.5 なら、半分は Faker 標準の上位 50 件から、半分は追加した姓から選ばれる。
    実態に基づく値ではないので、用途に合わせてサブクラスで変更する。
    """

    def __init__(self, generator) -> None:
        super().__init__(generator)
        if not 0 <= self.extended_share < 1:
            raise ValueError("extended_share は 0 以上 1 未満にしてください")
        path = (self.data_dir or default_data_dir()) / SURNAMES_FILE
        _, records = read_dataset(path)
        self._surnames, self._cum_weights = _build_population(records, self.extended_share)

    def last_name_pair(self) -> NamePair:
        """姓の (漢字, カタカナ, ローマ字) を返す。

        Faker 標準の random_element は呼び出しごとに重みを累積し直すため、
        14 万件規模では非常に遅い。累積重みを事前に計算して二分探索で選ぶ。

        :example: ('髙木', 'タカギ', 'Takagi')
        """
        r = self.generator.random.random() * self._cum_weights[-1]
        return self._surnames[bisect_right(self._cum_weights, r)]

    def name_pair(self) -> NamePair:
        """氏名の (漢字, カタカナ, ローマ字) を、読みが対応した状態で返す。

        Faker 標準の name() と kana_name() は別々に選ばれるため対応しないが、
        こちらは同じ姓・名から作る。

        :example: ('髙木 翼', 'タカギ ツバサ', 'Tsubasa Takagi')
        """
        last = self.last_name_pair()
        first = self.first_name_pair()
        return f"{last[0]} {first[0]}", f"{last[1]} {first[1]}", f"{first[2]} {last[2]}"


def _build_population(
    records: tuple[tuple[str, ...], ...], extended_share: float
) -> tuple[tuple[NamePair, ...], tuple[float, ...]]:
    base: dict[NamePair, float] = {
        tuple(pair): float(weight) for pair, weight in JaPersonProvider.last_name_pairs.items()
    }
    base_keys = {(kanji, kana) for kanji, kana, _ in base}
    extended = [
        (kanji, kana, romaji) for kanji, kana, romaji in records if (kanji, kana) not in base_keys
    ]

    population: list[NamePair] = list(base)
    weights: list[float] = list(base.values())
    if extended and extended_share > 0:
        base_total = sum(weights)
        extended_total = base_total * extended_share / (1 - extended_share)
        each = extended_total / len(extended)
        population.extend(extended)
        weights.extend([each] * len(extended))
    return tuple(population), tuple(accumulate(weights))
