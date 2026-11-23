"""データをビルドするコマンドラインツール。

faker-ja-extended build            # 元データを取得してすべてビルドする
faker-ja-extended build --only addresses --ken-all ./utf_ken_all.zip
faker-ja-extended info             # ビルド済みデータの情報を表示する
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from faker_ja_extended._data import (
    ADDRESSES_FILE,
    BUNDLED_DATA_DIR,
    SURNAMES_FILE,
    DataNotBuiltError,
    default_data_dir,
    read_dataset,
    write_dataset,
)
from faker_ja_extended.build import jmnedict, ken_all

USER_AGENT = "faker-ja-extended (test data builder)"
TARGETS = ("addresses", "surnames")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"取得中: {url}", file=sys.stderr)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(request, timeout=120) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out)
    tmp.replace(dest)
    return dest


def _source(local: Path | None, url: str, sources_dir: Path, filename: str) -> tuple[Path, str]:
    """ローカルのファイルが指定されていればそれを、なければダウンロードしたものを返す。"""
    if local is not None:
        if not local.exists():
            raise SystemExit(f"ファイルが見つかりません: {local}")
        return local, str(local.resolve())
    return download(url, sources_dir / filename), url


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def address_dataset(
    zip_path: Path, origin: str, *, built_at: str | None
) -> tuple[dict, list[list[str]]]:
    """郵便番号データの zip から、住所データセットのメタデータとレコードを作る。"""
    records = ken_all.build_records(ken_all.iter_rows(zip_path))
    meta = {
        "dataset": "addresses",
        "fields": list(ken_all.FIELDS),
        "source": origin,
        "source_page": ken_all.SOURCE_PAGE,
        "source_date": ken_all.source_date(zip_path),
        "source_sha256": _sha256(zip_path),
        "count": len(records),
        "notice": "郵便番号データについて、日本郵便株式会社は著作権を主張していません。",
    }
    if built_at is not None:
        meta["built_at"] = built_at
    return meta, records


def build_addresses(data_dir: Path, local: Path | None) -> None:
    path, origin = _source(local, ken_all.SOURCE_URL, data_dir / "sources", "utf_ken_all.zip")
    meta, records = address_dataset(path, origin, built_at=_now())
    write_dataset(data_dir / ADDRESSES_FILE, meta, records)
    print(f"住所: {len(records):,} 件 → {data_dir / ADDRESSES_FILE}", file=sys.stderr)


def build_surnames(data_dir: Path, local: Path | None) -> None:
    path, origin = _source(local, jmnedict.SOURCE_URL, data_dir / "sources", "JMnedict.xml.gz")
    records, skipped = jmnedict.build_records(jmnedict.iter_surname_entries(path))
    meta = {
        "dataset": "surnames",
        "fields": ["kanji", "kana", "romaji"],
        "source": origin,
        "source_page": jmnedict.SOURCE_PAGE,
        "source_sha256": _sha256(path),
        "built_at": _now(),
        "count": len(records),
        "skipped": skipped,
        "license": "CC BY-SA 4.0",
        "license_url": jmnedict.LICENSE_URL,
        "attribution": jmnedict.ATTRIBUTION,
    }
    write_dataset(data_dir / SURNAMES_FILE, meta, records)
    (data_dir / "SURNAMES_ATTRIBUTION.txt").write_text(
        jmnedict.ATTRIBUTION + "\n", encoding="utf-8"
    )
    print(f"姓: {len(records):,} 件 → {data_dir / SURNAMES_FILE}", file=sys.stderr)


def cmd_build(args: argparse.Namespace) -> None:
    data_dir: Path = args.data_dir
    targets = [args.only] if args.only else list(TARGETS)
    if "addresses" in targets:
        build_addresses(data_dir, args.ken_all)
    if "surnames" in targets:
        build_surnames(data_dir, args.jmnedict)


def _describe(meta: dict) -> str:
    parts = [f"{meta['count']:,} 件"]
    if "source_date" in meta:
        parts.append(f"元データ {meta['source_date']} 版")
    if "built_at" in meta:
        parts.append(f"ビルド {meta['built_at']}")
    return "、".join(parts)


def cmd_info(args: argparse.Namespace) -> None:
    print(f"保存先: {args.data_dir}")
    for name, label in ((ADDRESSES_FILE, "住所"), (SURNAMES_FILE, "姓")):
        try:
            meta, _ = read_dataset(args.data_dir / name)
            local = _describe(meta)
        except DataNotBuiltError:
            local = None
        bundled_path = BUNDLED_DATA_DIR / name
        bundled = _describe(read_dataset(bundled_path)[0]) if bundled_path.exists() else None

        print(f"{label}（{name}）")
        print(f"  ビルド済み: {local or '未ビルド'}")
        if bundled is not None:
            print(f"  同梱データ: {bundled}")
        if local:
            print("  → ビルド済みのデータを使います")
        elif bundled:
            print("  → 同梱データを使います")
        else:
            print("  → 使用できません（faker-ja-extended build を実行してください）")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="faker-ja-extended")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="データの保存先（既定: %(default)s。環境変数 FAKER_JA_EXTENDED_DATA_DIR でも指定可）",
    )
    sub = parser.add_subparsers(required=True)

    build = sub.add_parser("build", help="元データを取得してデータをビルドする")
    build.add_argument("--only", choices=TARGETS, help="指定したデータだけビルドする")
    build.add_argument(
        "--ken-all", type=Path, help="取得済みの utf_ken_all.zip を使う（指定しなければ取得する）"
    )
    build.add_argument(
        "--jmnedict", type=Path, help="取得済みの JMnedict.xml.gz を使う（指定しなければ取得する）"
    )
    build.set_defaults(func=cmd_build)

    info = sub.add_parser("info", help="ビルド済みデータと同梱データの情報を表示する")
    info.set_defaults(func=cmd_info)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
