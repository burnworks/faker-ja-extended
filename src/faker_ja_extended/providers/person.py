"""JMnedict 由来の姓と名で、ja_JP の氏名のバリエーションを増やす Provider。

姓：Faker 標準の上位 50 件は元の重み（おおよその人数）のまま残し、
JMnedict から追加した姓には一律の小さい重みを割り当てる。

名：既定では Faker 標準のまま。extended_first_name_share を 0 より大きくすると、
JMnedict の名を追加する。JMnedict の性別の分類は不完全なので、語尾と分類から
女性・男性に振り分けている（性別は目安）。1 つの漢字表記に読みが多いもの（「愛」は
数十通り）が偏って出ないよう、重みは「1 ÷ その漢字表記の読みの数」にしている。

JMnedict には頻度の情報がないため、追加分の重みは実態の分布を表すものではない。
"""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from collections.abc import Iterable
from itertools import accumulate
from pathlib import Path
from random import Random
from typing import ClassVar

from faker.providers.person.ja_JP import Provider as JaPersonProvider

from faker_ja_extended._data import (
    GIVEN_NAMES_FILE,
    SURNAMES_FILE,
    read_dataset,
    resolve_dataset_path,
)

NamePair = tuple[str, str, str]


class _WeightedPool:
    """重み付きの候補から、累積重みの二分探索で 1 件を選ぶ。

    Faker 標準の random_element は呼び出しごとに重みを累積し直すため、
    十数万件規模では非常に遅い。累積重みを事前に計算しておく。
    """

    __slots__ = ("_cum_weights", "_items")

    def __init__(self, items: list[NamePair], weights: list[float]) -> None:
        self._items = tuple(items)
        self._cum_weights = tuple(accumulate(weights))

    def __len__(self) -> int:
        return len(self._items)

    def pick(self, random: Random) -> NamePair:
        r = random.random() * self._cum_weights[-1]
        return self._items[bisect_right(self._cum_weights, r)]


def _build_pool(
    base: dict[NamePair, float], extended: Iterable[tuple[NamePair, float]], share: float
) -> _WeightedPool:
    """Faker 標準の候補に、追加分が全体の share の割合で選ばれるよう重みを付けて加える。"""
    base_keys = {(kanji, kana) for kanji, kana, _ in base}
    added = [(pair, w) for pair, w in extended if (pair[0], pair[1]) not in base_keys]
    items = list(base)
    weights = list(base.values())
    if added and share > 0:
        added_total = sum(weights) * share / (1 - share)
        weight_sum = sum(w for _, w in added)
        items.extend(pair for pair, _ in added)
        weights.extend(added_total * w / weight_sum for _, w in added)
    return _WeightedPool(items, weights)


def _check_share(name: str, value: float) -> None:
    if not 0 <= value < 1:
        raise ValueError(f"{name} は 0 以上 1 未満にしてください")


class Provider(JaPersonProvider):
    """ja_JP の姓を JMnedict の姓（約 14 万件）まで拡張する。名の拡張は任意。"""

    data_dir: ClassVar[Path | None] = None
    """データの場所。None なら既定の場所（環境変数 FAKER_JA_EXTENDED_DATA_DIR など）を使う"""

    extended_share: ClassVar[float] = 0.5
    """JMnedict から追加した姓が選ばれる割合（0 以上 1 未満）。

    0.5 なら、半分は Faker 標準の上位 50 件から、半分は追加した姓から選ばれる。
    実態に基づく値ではないので、用途に合わせてサブクラスで変更する。
    """

    extended_first_name_share: ClassVar[float] = 0.0
    """JMnedict から追加した名が選ばれる割合（0 以上 1 未満）。既定は 0（名は Faker 標準のまま）。

    0 より大きくすると、名のデータ（faker-ja-extended build --only given_names）が必要になる。
    性別は JMnedict の分類と語尾から振り分けた目安で、正確ではない。
    """

    def __init__(self, generator) -> None:
        super().__init__(generator)
        _check_share("extended_share", self.extended_share)
        _check_share("extended_first_name_share", self.extended_first_name_share)

        # 姓データ（JMnedict 由来、CC BY-SA 4.0）は同梱せず、利用者の環境でビルドする
        self.dataset_path = resolve_dataset_path(SURNAMES_FILE, self.data_dir, bundled=False)
        self.dataset_meta, surnames = read_dataset(self.dataset_path)
        self._surnames = _build_pool(
            {tuple(pair): float(w) for pair, w in JaPersonProvider.last_name_pairs.items()},
            (((kanji, kana, romaji), 1.0) for kanji, kana, romaji in surnames),
            self.extended_share,
        )

        self.given_names_dataset_path: Path | None = None
        self.given_names_dataset_meta: dict | None = None
        self._first_names: dict[str, _WeightedPool] | None = None
        if self.extended_first_name_share > 0:
            self._load_given_names()

    def _load_given_names(self) -> None:
        self.given_names_dataset_path = resolve_dataset_path(
            GIVEN_NAMES_FILE, self.data_dir, bundled=False
        )
        self.given_names_dataset_meta, records = read_dataset(self.given_names_dataset_path)
        readings = Counter(kanji for kanji, *_ in records)

        def extended(genders: set[str]) -> list[tuple[NamePair, float]]:
            return [
                ((kanji, kana, romaji), 1 / readings[kanji])
                for kanji, kana, romaji, gender in records
                if gender in genders
            ]

        share = self.extended_first_name_share
        female = dict.fromkeys(JaPersonProvider.first_name_female_pairs, 1.0)
        male = dict.fromkeys(JaPersonProvider.first_name_male_pairs, 1.0)
        self._first_names = {
            "female": _build_pool(female, extended({"female", "both"}), share),
            "male": _build_pool(male, extended({"male", "both"}), share),
            "any": _build_pool(female | male, extended({"female", "male", "both"}), share),
        }

    def last_name_pair(self) -> NamePair:
        """姓の (漢字, カタカナ, ローマ字) を返す。

        :example: ('髙木', 'タカギ', 'Takagi')
        """
        return self._surnames.pick(self.generator.random)

    def first_name_pair(self) -> NamePair:
        """名の (漢字, カタカナ, ローマ字) を返す。

        :example: ('明美', 'アケミ', 'Akemi')
        """
        if self._first_names is None:
            return super().first_name_pair()
        return self._first_names["any"].pick(self.generator.random)

    def first_name_female_pair(self) -> NamePair:
        """女性の名の (漢字, カタカナ, ローマ字) を返す。

        :example: ('明美', 'アケミ', 'Akemi')
        """
        if self._first_names is None:
            return super().first_name_female_pair()
        return self._first_names["female"].pick(self.generator.random)

    def first_name_male_pair(self) -> NamePair:
        """男性の名の (漢字, カタカナ, ローマ字) を返す。

        :example: ('晃', 'アキラ', 'Akira')
        """
        if self._first_names is None:
            return super().first_name_male_pair()
        return self._first_names["male"].pick(self.generator.random)

    def name_pair(self) -> NamePair:
        """氏名の (漢字, カタカナ, ローマ字) を、読みが対応した状態で返す。

        Faker 標準の name() と kana_name() は別々に選ばれるため対応しないが、
        こちらは同じ姓・名から作る。

        :example: ('髙木 翼', 'タカギ ツバサ', 'Tsubasa Takagi')
        """
        last = self.last_name_pair()
        first = self.first_name_pair()
        return f"{last[0]} {first[0]}", f"{last[1]} {first[1]}", f"{first[2]} {last[2]}"
