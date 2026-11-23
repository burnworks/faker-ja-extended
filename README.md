# faker-ja-extended

[Faker](https://github.com/joke2k/faker) の日本語ロケール（`ja_JP`）を拡張し、テストデータをより実際に近いものにする Provider 集です。

- **実在する住所と郵便番号**：日本郵便の郵便番号データをもとに、都道府県 / 市区町村 / 町域 / 郵便番号の対応が取れた住所を生成します。住所データはパッケージに同梱しているので、インストールしてすぐに使えます
- **約 14 万件の姓**：JMnedict（日本語固有名詞辞書）の姓を追加し、漢字 / カタカナ / ローマ字が対応した氏名を生成します

```python
>>> fake.address_with_postcode()
'〒247-0062 神奈川県鎌倉市山ノ内'
>>> fake.name_pair()
('冨士尾 裕美子', 'フジオ ユミコ', 'Yumiko Fujio')
```

## なぜ必要か

Faker の `ja_JP` ロケールは手軽に使えますが、大量のテストデータを作ると次のような問題が出ます。

- 姓は 50 種類、名は 51 種類しかないため、100 万件生成すると同じ氏名が平均 400 回ほど重複します
- 住所は都道府県 / 市区町村 / 町名を別々に選ぶため、「京都府練馬区」のような実在しない組み合わせや、「39丁目」のようなありえない値が出ます
- 郵便番号も住所とは無関係に生成されます

faker-ja-extended は、Faker の使い方はそのままに、これらを公開データに基づく値で置き換えます。

## クイックスタート

### 1. インストール

```sh
# uv
uv add faker-ja-extended

# pip（仮想環境を有効にした状態で）
pip install faker-ja-extended
```

### 2. 姓のデータをビルドする（姓を使う場合、最初に一度だけ）

住所データはパッケージに同梱しているので、住所だけを使う場合はこの手順は不要です。

姓のデータはライセンスの都合で同梱していないため、EDRDG から元データを取得してビルドします。インターネット接続が必要です。

```sh
# uv
uv run faker-ja-extended build --only surnames

# pip
faker-ja-extended build --only surnames
```

### 3. Provider を追加する

```python
from faker import Faker
from faker_ja_extended import AddressProvider, PersonProvider

fake = Faker("ja_JP")
fake.add_provider(PersonProvider)
fake.add_provider(AddressProvider)

fake.address_with_postcode()  # '〒150-0022 東京都渋谷区恵比寿南'
fake.name_pair()              # ('幸脇 英樹', 'サイノワキ ヒデキ', 'Hideki Sainowaki')
```

姓のデータをビルドする前に `PersonProvider` を追加すると、`DataNotBuiltError` が発生します。

## Provider を追加すると何が変わるか

### AddressProvider（住所）

Faker 標準の `ja_JP` の住所 Provider を継承しています。

| | メソッド | 内容 |
|---|---|---|
| 置き換わる | `address()` | 都道府県から町域まで（例：`'東京都渋谷区恵比寿南'`）。**Faker 標準と違い、番地 / 号 / 建物名は付きません** |
| 置き換わる | `postcode()` / `zipcode()` | 実在する郵便番号（例：`'150-0022'`） |
| 追加 | `address_with_postcode()` | 郵便番号付きの住所。郵便番号と住所が対応しています |
| 追加 | `address_record()` | 郵便番号 / 住所 / カナ / 地方公共団体コードなどをまとめた `AddressRecord` |

`prefecture()`、`city()`、`town()`、`chome()`、`ban()`、`gou()`、`building_name()` など、上の表にないメソッドは Faker 標準のままです。

`address()` と `postcode()` は、呼び出すたびに別々のレコードから選ばれます。住所と郵便番号を対応させたい場合は、`address_with_postcode()` か `address_record()` を使ってください。

```python
record = fake.address_record()
record.postcode               # '1500022'（ハイフンなし）
record.postcode_hyphenated    # '150-0022'
record.prefecture             # '東京都'
record.city                   # '渋谷区'
record.town                   # '恵比寿南'
record.address                # '東京都渋谷区恵比寿南'
record.address_kana           # 'トウキョウトシブヤクエビスミナミ'
record.lg_code                # '13113'（全国地方公共団体コード）
record.town_raw               # 加工前の町域名（後述）
```

### PersonProvider（氏名）

Faker 標準の `ja_JP` の氏名 Provider を継承しています。

| | メソッド | 内容 |
|---|---|---|
| 候補が増える | `last_name()`、`last_kana_name()`、`last_romanized_name()`、`last_name_pair()` | 姓の候補が、Faker 標準の 50 件から約 14 万件に増えます |
| 候補が増える | `name()`、`kana_name()`、`romanized_name()` など姓を含むもの | 同上 |
| 追加 | `name_pair()` | 氏名の (漢字, カタカナ, ローマ字)。読みとローマ字が漢字と対応しています |

名（ファーストネーム）は Faker 標準のままです。

Faker 標準の `name()` と `kana_name()` は、それぞれ別の氏名から生成されます。漢字と読みを対応させたい場合は、`name_pair()` を使ってください。

```python
fake.last_name_pair()  # ('幸脇', 'サイノワキ', 'Sainowaki')
fake.name_pair()       # ('幸脇 英樹', 'サイノワキ ヒデキ', 'Hideki Sainowaki')
```

## さまざまな使い方

### 住所だけ、または姓だけ使う

2 つの Provider は独立しているので、片方だけ追加できます。住所だけを使う場合は、データのビルドは不要です。

```python
fake = Faker("ja_JP")
fake.add_provider(AddressProvider)  # 住所だけ実在のものにする
```

### pytest で使う

Faker の pytest プラグイン（Faker と一緒にインストールされます）の `faker` フィクスチャに Provider を追加するには、`conftest.py` に次のように書きます。

```python
# conftest.py
import pytest
from faker_ja_extended import AddressProvider, PersonProvider


@pytest.fixture(scope="session")
def faker_session_locale():
    return ["ja_JP"]


@pytest.fixture
def faker(faker):
    faker.add_provider(PersonProvider)
    faker.add_provider(AddressProvider)
    return faker
```

```python
# test_customer.py
def test_register_customer(faker):
    name, kana, _ = faker.name_pair()
    record = faker.address_record()
    ...
```

Faker の pytest プラグインは、テストごとにシードを `0` に戻すので、毎回同じデータが生成されます。

### factory_boy で使う

```python
import factory
from faker_ja_extended import AddressProvider, PersonProvider

factory.Faker.add_provider(PersonProvider, locale="ja_JP")
factory.Faker.add_provider(AddressProvider, locale="ja_JP")


class CustomerFactory(factory.Factory):
    class Meta:
        model = dict

    name = factory.Faker("name", locale="ja_JP")
    address = factory.Faker("address_with_postcode", locale="ja_JP")
```

### 同じデータを再現する

Faker 標準と同じく、シードを固定すると毎回同じデータが生成されます。同梱の住所データはパッケージのバージョンごとに固定されているので、同じバージョンと同じシードなら、どの環境でも同じ住所が生成されます。

ただし、`faker-ja-extended build` でデータをビルドし直した場合は、元データの更新によって、同じシードでも結果が変わることがあります。

```python
fake.seed_instance(42)
```

### 設定を変える

サブクラスを作って設定を変更します。

```python
from pathlib import Path
from faker_ja_extended import AddressProvider, PersonProvider


class MyPersonProvider(PersonProvider):
    extended_share = 0.3       # 追加した姓が選ばれる割合（既定 0.5）
    data_dir = Path("./data")  # データの保存先


class MyAddressProvider(AddressProvider):
    data_dir = Path("./data")


fake.add_provider(MyPersonProvider)
fake.add_provider(MyAddressProvider)
```

`extended_share` は、JMnedict から追加した姓が選ばれる割合です。`0.5` なら、半分は Faker 標準の頻出姓（佐藤、鈴木、高橋など 50 件）から、残り半分は追加した約 14 万件から選ばれます。`0` にすると Faker 標準の姓だけになります。

## データの管理

### 使われるデータ

Provider は、次の順でデータを探して使います。

1. Provider の `data_dir` が設定されていれば、その場所のデータ（見つからなければエラー）
2. 保存先（下記）に `faker-ja-extended build` でビルドしたデータがあれば、そのデータ
3. 住所は、パッケージに同梱しているデータ

同梱の住所データは、リリースした時点の郵便番号データから作っています。より新しい郵便番号データを使いたい場合は、`faker-ja-extended build --only addresses` でビルドすると、そちらが優先されます。どちらが使われるかは `faker-ja-extended info` で確認できます。

### 保存先

ビルドしたデータと取得した元データは、次の場所に保存されます。

- Linux / macOS：`~/.local/share/faker-ja-extended`（環境変数 `XDG_DATA_HOME` が設定されていればその下）
- Windows：`%LOCALAPPDATA%\faker-ja-extended`

保存先は、環境変数 `FAKER_JA_EXTENDED_DATA_DIR` か、`--data-dir` オプションで変更できます。CI などで姓のデータをプロジェクト内に置きたい場合に使ってください。

```sh
FAKER_JA_EXTENDED_DATA_DIR=./data faker-ja-extended build --only surnames
```

### コマンド

| コマンド | 内容 |
|---|---|
| `faker-ja-extended build` | 元データを取得して、住所と姓の両方のデータをビルドする |
| `faker-ja-extended build --only surnames` | 姓だけビルドする（`addresses` で住所だけ） |
| `faker-ja-extended build --ken-all ./utf_ken_all.zip` | 取得済みの郵便番号データを使う |
| `faker-ja-extended build --jmnedict ./JMnedict.xml.gz` | 取得済みの JMnedict を使う |
| `faker-ja-extended info` | ビルド済みデータと同梱データの件数・元データの日付と、どちらが使われるかを表示する |

`faker-ja-extended` の代わりに `python -m faker_ja_extended` でも実行できます。

### 更新

元データはどちらも定期的に更新されます（郵便番号データは毎月）。

- 住所：同梱データは、郵便番号データの更新を毎月確認し、変更があればパッチバージョン（例：0.2.0 → 0.2.1）として公開します。それより新しいデータが必要な場合は、`faker-ja-extended build --only addresses` を実行してください
- 姓：最新の状態を保つため、定期的に `faker-ja-extended build --only surnames` を実行し直してください

## データの加工内容

### 住所

郵便番号データの町域名には、住所ではない説明文や注記が含まれているため、次のように加工しています。

| 元データの町域名 | 扱い |
|---|---|
| 「以下に掲載がない場合」 | 町域を特定しないので除外 |
| 「軽井沢町一円」のような市区町村名＋「一円」 | 町域なし（市区町村まで）として残す |
| 町域名がそのまま「一円」の地名（滋賀県犬上郡多賀町一円） | 実在する地名なので残す |
| 「○○の次に番地がくる場合」「○○村の次に６６４番地以降がくる場合」など | 町域なしとして残す |
| 括弧書きの注記（「大通西（１～１９丁目）」など） | 注記を取り除く（「大通西」） |
| 高層ビルの階ごとの郵便番号（「（１階）」「（地階・階層不明）」） | 除外 |
| 読点で並べた複数の町域（「甲、乙」「樺沢１６地割、樺沢１７地割」） | 1 件ずつに分ける |
| 地割の範囲（「種市第８地割〜第１４地割」） | 個別の地割に展開する |
| 廃止のレコード | 除外 |

町域名に含まれる丁目・番町・地割（「象潟町５丁目塩越」「すずらん台東１番町」など）は、郵便番号データ上の町域名そのものなので残しています。

加工前の町域名は `AddressRecord.town_raw` で取得できます。表記の揺れや注記を含むデータとして、住所の入力欄や正規化処理のテストに使えます。

### 姓とローマ字

JMnedict のうち、種別が「姓」のエントリから、漢字表記と読みの組を取り出しています。1 つの漢字に複数の読みがある姓（「新谷」の「あらたに」「しんたに」「にいや」など）は、それぞれ別の姓として扱います。

ローマ字は、読みからヘボン式（パスポート式）で生成しています。

- 長音は表記しません（さとう → Sato、おおの → Ono）
- 「ん」は b / m / p の前で m にします（なんば → Namba）
- 促音「っ」は次の子音を重ねます（はっとり → Hattori）

## 制限事項

- 住所は町域までです。丁目以降（番地 / 号 / 建物名）は生成しません
- JMnedict には姓の頻度の情報がないため、追加した姓はすべて同じ確率で選ばれます。珍しい姓が実際の分布より多く出る点に注意してください
- ローマ字の長音の判定は、読みだけから行う近似です。語の切れ目によっては、パスポートの表記と一致しない場合があります（「うえ」の「う」は縮めない例外を設けています。例：いのうえ → Inoue）
- 住所は実在する地域、氏名は実在する姓と名の組み合わせです。実在の個人を表すものではありませんが、生成したデータを宛先にして郵便物を送るなどの使い方はしないでください

## 動作環境

- Python 3.11 以上
- Faker 40 以上
- Linux / macOS / Windows（Windows の注意点は[付録](https://github.com/burnworks/faker-ja-extended#付録windows-環境をご利用の場合)を参照）

## 開発

```sh
git clone https://github.com/burnworks/faker-ja-extended
cd faker-ja-extended
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

テストは小さなフィクスチャデータと同梱の住所データで行い、ネットワークには接続しません。

### 同梱データの更新とリリース（メンテナー向け）

同梱の住所データは、GitHub Actions のワークフロー（`.github/workflows/update-addresses.yml`）で毎月確認しています。

1. 毎月 3 日に日本郵便から郵便番号データを取得し、同梱データを作り直す
2. 変更があれば、パッチバージョンを上げてテストを実行し、プルリクエストを作る（同じ元データからは常に同じファイルができるので、変更がなければ何もしない）
3. プルリクエストをマージし、新しいバージョンと同じ名前のタグ（例：`v0.2.1`）で GitHub のリリースを作ると、`.github/workflows/publish.yml` が PyPI に公開する

手元で同梱データを更新する場合は、次のスクリプトを実行します。

```sh
uv run python scripts/update_bundled_addresses.py
```

### バージョンの付け方

- パッチ（0.2.0 → 0.2.1）：同梱の住所データの更新、またはバグ修正
- マイナー（0.2.x → 0.3.0）：機能の追加や、データの加工方法の変更

同梱データが更新されると、同じシードでも生成される住所が変わります。生成結果を固定したい場合は、パッケージのバージョンを固定してください。

## ライセンス

このリポジトリのコードは [MIT License](https://github.com/burnworks/faker-ja-extended/blob/main/LICENSE) で公開しています。

同梱データ、元データ、ビルドしたデータには、それぞれ次の出典とライセンスが適用されます。

### データの出典

- **郵便番号データ**：[日本郵便株式会社](https://www.post.japanpost.jp/service/search/zipcode/download/utf-zip.html)。郵便番号データについて、日本郵便株式会社は著作権を主張していません。パッケージに同梱している住所データ（`src/faker_ja_extended/data/addresses.json.gz`）は、このデータを加工したものです
- **JMnedict**：This package uses the [JMnedict](https://www.edrdg.org/enamdict/enamdict_doc.html) dictionary file. This file is the property of the [Electronic Dictionary Research and Development Group](https://www.edrdg.org/), and is used in conformance with the Group's [licence](https://www.edrdg.org/edrdg/license.html) (CC BY-SA 4.0).

ビルドした姓データ（`surnames.json.gz`）は JMnedict の派生物なので、CC BY-SA 4.0 に従います。ビルドしたデータを配布する場合は、ビルド時にデータの保存先に出力される `SURNAMES_ATTRIBUTION.txt` を添えてください。

## 付録：Windows 環境をご利用の場合

基本的な使い方は Linux / macOS と同じです。ただし、Windows 11 のスマートアプリコントロールが有効な環境では、次の点に注意が必要です。

### スマートアプリコントロールによるブロック

スマートアプリコントロールは、デジタル署名のない実行ファイルをブロックします。次のものは署名がないため、実行時に次のエラーで失敗することがあります。

```
アプリケーション制御ポリシーによってこのファイルがブロックされました。 (os error 4551)
```

- uv が自動でダウンロードする Python
- uv や pip が作るコマンド用のラッパー（`faker-ja-extended.exe`、`pytest.exe` など）

スマートアプリコントロールの状態は、「Windows セキュリティ」→「アプリとブラウザー コントロール」→「スマート アプリ コントロールの設定」で確認できます。Microsoft Defender のウイルス対策の除外設定では解決しません。

### 対処方法

python.org で配布されている Python（署名あり）を使い、コマンドは `python -m` の形式で実行してください。

```powershell
# python.org 版の Python をインストールする
winget install --id Python.Python.3.13 -e

# uv がダウンロードした Python ではなく、インストール済みの Python を使う
uv sync --python-preference only-system

# コマンドは python -m の形式で実行する
uv run python -m faker_ja_extended build --only surnames
uv run python -m faker_ja_extended info
uv run python -m pytest
```

毎回 `--python-preference only-system` を指定する代わりに、uv の設定ファイル（`%APPDATA%\uv\uv.toml`）に次の 1 行を書いておくこともできます。

```toml
python-preference = "only-system"
```

### その他の方法

- **WSL を使う**：WSL（Windows Subsystem for Linux）の中で動かす場合は、スマートアプリコントロールの影響を受けません。Linux と同じ手順で使えます
- **スマートアプリコントロールをオフにする**：「Windows セキュリティ」から変更できます。ただし、オフにした後でオンに戻せるかどうかは Windows のバージョンや設定によって異なるため、慎重に判断してください
