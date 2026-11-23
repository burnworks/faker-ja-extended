"""パッケージに同梱する住所データを更新する（メンテナー向け）。

    uv run python scripts/update_bundled_addresses.py                 # 日本郵便から取得して更新
    uv run python scripts/update_bundled_addresses.py ./utf_ken_all.zip  # 取得済みのファイルを使う

同梱データには、同じ元データから同じ内容ができるよう、ビルド日時を含めない。
内容が変わっていなければファイルを書き換えないので、差分の有無で更新の要否を判断できる。
（gzip の圧縮結果は環境によって変わることがあるため、展開した内容で比較している）
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from faker_ja_extended._data import ADDRESSES_FILE, BUNDLED_DATA_DIR, write_dataset_if_changed
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
    summary = f"{len(records):,} 件（元データ {meta['source_date']} 版）"
    if write_dataset_if_changed(dest, meta, records):
        print(f"同梱データを更新しました: {summary}")
        print(f"  → {dest}")
    else:
        print(f"同梱データは最新です。変更はありません: {summary}")


if __name__ == "__main__":
    main()
