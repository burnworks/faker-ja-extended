"""ビルド済みデータの保存場所と、読み書きの共通処理。"""

from __future__ import annotations

import gzip
import json
import os
from functools import cache
from pathlib import Path
from typing import Any

ENV_DATA_DIR = "FAKER_JA_EXTENDED_DATA_DIR"

ADDRESSES_FILE = "addresses.json.gz"
SURNAMES_FILE = "surnames.json.gz"

# パッケージに同梱しているデータの場所（住所データのみ同梱）
BUNDLED_DATA_DIR = Path(__file__).parent / "data"

FORMAT_VERSION = 1


class DataNotBuiltError(FileNotFoundError):
    """ビルド済みデータが見つからないときに送出する。"""


def default_data_dir() -> Path:
    """データの保存先を返す。

    環境変数 ``FAKER_JA_EXTENDED_DATA_DIR`` があればそれを使い、
    なければ OS ごとのユーザーデータ用ディレクトリを使う。
    """
    if value := os.environ.get(ENV_DATA_DIR):
        return Path(value)
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "faker-ja-extended"


def resolve_dataset_path(filename: str, explicit_dir: Path | None, *, bundled: bool) -> Path:
    """Provider が読むデータファイルの場所を決める。

    1. Provider に data_dir が明示されていれば、その場所だけを見る（なければエラー）
    2. 既定の保存先（環境変数 FAKER_JA_EXTENDED_DATA_DIR など）にビルド済みのデータがあれば、
       それを使う
    3. 同梱データがあるもの（住所）は、同梱データを使う
    """
    if explicit_dir is not None:
        return explicit_dir / filename
    local = default_data_dir() / filename
    if local.exists() or not bundled:
        return local
    return BUNDLED_DATA_DIR / filename


def write_dataset(path: Path, meta: dict[str, Any], records: list[list[str]]) -> None:
    """メタデータとレコードを gzip 圧縮した JSON として書き出す。

    同じ入力からは同じバイト列になるよう、gzip のタイムスタンプは 0 に固定する。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"format_version": FORMAT_VERSION, "meta": meta, "records": records}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        gz.write(body)
    tmp.replace(path)


@cache
def read_dataset(path: Path) -> tuple[dict[str, Any], tuple[tuple[str, ...], ...]]:
    """データセットを読み込む。同じパスはプロセス内でキャッシュする。"""
    if not path.exists():
        raise DataNotBuiltError(
            f"データが見つかりません: {path}\n"
            "先に `faker-ja-extended build` を実行してデータをビルドしてください。"
        )
    with gzip.open(path, "rt", encoding="utf-8") as f:
        payload = json.load(f)
    if payload.get("format_version") != FORMAT_VERSION:
        raise DataNotBuiltError(
            f"データの形式が古いか未対応です: {path}\n"
            "`faker-ja-extended build` を再実行してください。"
        )
    records = tuple(tuple(r) for r in payload["records"])
    return payload["meta"], records
