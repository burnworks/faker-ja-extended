"""Faker の ja_JP ロケールを拡張する Provider 集。

使い方::

    from faker import Faker
    from faker_ja_extended import AddressProvider, PersonProvider

    fake = Faker("ja_JP")
    fake.add_provider(PersonProvider)
    fake.add_provider(AddressProvider)

事前に ``faker-ja-extended build`` でデータをビルドしておく必要がある。
"""

from faker_ja_extended.providers.address import AddressRecord
from faker_ja_extended.providers.address import Provider as AddressProvider
from faker_ja_extended.providers.person import Provider as PersonProvider

__all__ = ["AddressProvider", "AddressRecord", "PersonProvider"]
