"""パッケージに同梱する住所データを更新する（メンテナー向け）。

    uv run python scripts/update_bundled_addresses.py                 # 日本郵便から取得して更新
    uv run python scripts/update_bundled_addresses.py ./utf_ken_all.zip  # 取得済みのファイルを使う

同梱データには、同じ元データから常に同じバイト列ができるよう、ビルド日時を含めない。
元データが変わっていなければファイルは変わらないので、差分の有無で更新の要否を判断できる。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from faker_ja_extended._data import ADDRESSES_FILE, BUNDLED_DATA_DIR, write_dataset
from faker_ja_extended.build import ken_all
from faker_ja_extended.build.cli import address_dataset, download


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        if len(sys.argv) > 1:
            zip_path = Path(sys.argv[1])
        else:
            zip_path = download(ken_all.SOURCE_URL, Path(tmp) / "utf_ken_all.zip")
        meta, records = address_dataset(zip_path, ken_all.SOURCE_URL, built_at=None)
    dest = BUNDLED_DATA_DIR / ADDRESSES_FILE
    write_dataset(dest, meta, records)
    print(f"同梱データを更新しました: {len(records):,} 件（元データ {meta['source_date']} 版）")
    print(f"  → {dest}")


if __name__ == "__main__":
    main()
