# faker-ja-extended

[Faker](https://github.com/joke2k/faker) の日本語ロケール（`ja_JP`）を拡張し、テストデータをより実際に近いものにする Provider 集です。

- **実在する住所と郵便番号**：日本郵便の郵便番号データをもとに、都道府県 / 市区町村 / 町域 / 郵便番号の対応が取れた住所を生成します。住所データはパッケージに同梱しているので、インストールしてすぐに使えます
- **約 14 万件の姓**：JMnedict（日本語固有名詞辞書）の姓を追加し、漢字 / カタカナ / ローマ字が対応した氏名を生成します
- **約 18 万件の名（任意）**：設定を変えると、名も JMnedict の名で拡張できます
- **意地悪なデータのカタログ**：異体字、サロゲートペア、異体字セレクタ付きの文字、表記の揺れなど、システムが壊れやすい姓を集めたカタログを使えます

```python
>>> fake.address_with_postcode()
'〒247-0062 神奈川県鎌倉市山ノ内'
>>> fake.name_pair()
('冨士尾 裕美子', 'フジオ ユミコ', 'Yumiko Fujio')
```

## なぜこれを作ったのか

Faker の `ja_JP` ロケールは手軽に使えますが、大量のテストデータを作ると次のような問題が出ます。

- 姓は 50 種類、名は 51 種類しかないため、例えば 100 万件のテストデータを生成すると同じ氏名が平均 400 回ほど重複します
- 住所は都道府県 / 市区町村 / 町名を別々に選ぶため、「京都府練馬区」のような実在しない組み合わせや、「39丁目」のようなありえない値が出ます
- 郵便番号も住所とは無関係に生成されます

faker-ja-extended は、Faker の使い方はそのままに、これらを公開データに基づく値で置き換えます。

## 生成例

同じシード（`seed_instance(3)`）で 5 件ずつ生成した、実際の出力です。

**Faker 標準（`ja_JP`）**

| `name()` | `kana_name()` | `postcode()` | `address()` |
|---|---|---|---|
| 林 京助 | フジイ ミキ | 640-9516 | 高知県我孫子市上野公園17丁目18番8号 |
| 中川 直樹 | カトウ クミコ | 237-2484 | 滋賀県神津島村東和町5丁目6番19号 パレス皇居外苑479 |
| 山下 舞 | イシカワ ユミコ | 455-2197 | 福島県君津市湯宮32丁目7番9号 戸塚町クレスト869 |
| 松本 舞 | アオキ ミノル | 937-0469 | 高知県あきる野市氏家新田21丁目18番19号 南郷屋アーバン411 |
| 石井 幹 | ナカムラ オサム | 420-2470 | 山梨県北区大京町8丁目2番20号 |

氏名と読みは別々に生成されるので、「林 京助」の読みが「フジイ ミキ」になります。住所も「高知県我孫子市」のように都道府県と市区町村が合わず、郵便番号とも対応しません。

**faker-ja-extended**（名の拡張を有効にした場合）

| 氏名 | フリガナ | ローマ字 | 郵便番号・住所 |
|---|---|---|---|
| 佐々木 伶衣 | ササキ レイ | Rei Sasaki | 〒515-3135 三重県津市白山町二俣 |
| 薮阪 亮介 | ヤブサカ リョウスケ | Ryosuke Yabusaka | 〒737-0808 広島県呉市上内神町 |
| 高橋 あすか | タカハシ アスカ | Asuka Takahashi | 〒959-4407 新潟県東蒲原郡阿賀町西 |
| 福田 佳須子 | フクダ カズコ | Kazuko Fukuda | 〒321-0933 栃木県宇都宮市簗瀬町 |
| 鹿嶋 洋介 | シカジマ ヨウスケ | Yosuke Shikajima | 〒959-3226 新潟県岩船郡関川村片貝 |

```python
class MyPersonProvider(PersonProvider):
    extended_first_name_share = 0.5

fake.add_provider(MyPersonProvider)
fake.add_provider(AddressProvider)
fake.seed_instance(3)

kanji, kana, romaji = fake.name_pair()
record = fake.address_record()
```

氏名 / フリガナ / ローマ字が対応し、郵便番号と住所は実在する組み合わせです。

**意地悪なデータを混ぜた場合**（`nasty_share = 0.3`、`seed_instance(8)`）

| 氏名 | フリガナ | カタログにあるパターン |
|---|---|---|
| 三ケ島 淳 | ミカジマ ジュン | 表記の揺れ（「三ヶ島」の「ヶ」を大きい「ケ」で書いた表記） |
| 齋藤 健一 | サイトウ ケンイチ | 異体字（「斎藤」の旧字体） |
| 林 翼 | ハヤシ ツバサ | 1 文字の姓 |
| 佐藤 あすか | サトウ アスカ | |
| 岡本 拓真 | オカモト タクマ | |

実際にデータを生成するスクリプトの例は [examples/](https://github.com/burnworks/faker-ja-extended/tree/main/examples) にあります。

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

このコマンドでビルドされるのは姓のデータだけです。名も拡張する場合は、`--only surnames given_names` のように名のデータ（`given_names`）も指定してビルドしてください（[名を拡張する](#名を拡張する)を参照）。

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
| 設定で候補が増える | `first_name()`、`first_name_female()`、`first_name_male()` など名を含むもの | 既定では Faker 標準のまま。設定すると約 18 万件に増えます（[名を拡張する](#名を拡張する)） |
| 追加 | `name_pair()` | 氏名の (漢字, カタカナ, ローマ字)。読みとローマ字が漢字と対応しています |

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

### 名を拡張する

名（ファーストネーム）は、既定では Faker 標準（女性 21 件、男性 30 件）のままです。`extended_first_name_share` を設定すると、JMnedict の名（約 18 万件）を追加できます。

```sh
faker-ja-extended build --only given_names
```

```python
class MyPersonProvider(PersonProvider):
    extended_first_name_share = 0.5  # 追加した名が選ばれる割合

fake.add_provider(MyPersonProvider)
fake.first_name_female()  # '安莉砂'
fake.name_pair()          # ('城台 真綾', 'ジョウダイ マアヤ', 'Maaya Jodai')
```

姓と名の両方を拡張すると、100 万件生成したときの氏名の種類は約 74 万種類になります（拡張しない場合は 2,550 種類）。

既定で無効にしているのは、次の注意点があるためです。

- **性別は目安です**：JMnedict の性別の分類は不完全なため、分類と語尾（～郎 / ～彦なら男性、～子 / ～美なら女性など）から振り分けています。Faker 標準の名で確かめると、女性名は 18 件すべて、男性名は 30 件中 24 件が正しく振り分けられ、6 件（晃、淳、翼、学、裕樹、零）は女性名に振り分けられました。`first_name_male()` で女性名が、`first_name_female()` で男性名が出ることがあります
- **頻度の情報がありません**：珍しい名や当て字の読みが、実際の分布より多く出ます。1 つの漢字表記に読みが多いもの（「愛」は数十通り）が偏らないよう、漢字表記ごとに同じくらいの確率になるよう調整しています

入力欄や検索のテストで、名の文字や読みのバリエーションを増やしたい場合に向いています。性別ごとの集計など、性別の正確さが必要なテストには向きません。

### 意地悪なデータを使う

文字コード、Unicode の正規化、文字数の数え方、表記の揺れなどで、システムが壊れやすい姓を集めたカタログを同梱しています（現在は姓の 37 件）。データのビルドは不要です。

使い方は 3 通りあります。

**1. 全件を試す（pytest のパラメータ化）**

登録や検索の処理がすべてのパターンで壊れないかを確かめるのに向いています。Faker は使いません。

```python
import pytest
from faker_ja_extended import surname_cases


@pytest.mark.parametrize("case", surname_cases(), ids=lambda c: c.id)
def test_register_customer(case):
    customer = register(last_name=case.value, last_name_kana=case.kana)
    assert find_customer(case.value) == customer
```

各件は `NastyCase` で、表記（`value`）、標準的な表記（`base`）、読み（`kana`）、ローマ字（`romaji`）、タグ（`tags`）、何が壊れやすいかの説明（`note`）を持っています。

**2. Faker から選ぶ**

```python
fake.nasty_last_name()                              # '𠮷田'
fake.nasty_last_name_pair()                         # ('𠮷田', 'ヨシダ', 'Yoshida')
fake.nasty_last_name(include={"cp932_unmappable"})  # CP932 に変換できないものだけ
fake.nasty_last_name_case()                         # 説明やタグを含む NastyCase
```

`PersonProvider` を追加すると使えます（姓のデータのビルドが必要です）。

**3. 通常の生成に一定の割合で混ぜる**

大量のテストデータの中に、本番データのように時々意地悪なデータが混ざっている状態を作れます。既定は 0（混ぜない）です。

```python
class MyPersonProvider(PersonProvider):
    nasty_share = 0.01                            # last_name() などの 1% をカタログの姓にする
    nasty_exclude = frozenset({"ivs"})            # 混ぜないもの（システムが扱わない仕様のもの）
```

`last_name()`、`name()`、`name_pair()` など、姓を含むメソッドすべてに混ざります。混ざった姓も、読みとローマ字は対応しています。

#### タグ

`include`（どれかを持つものだけ）と `exclude`（どれかを持つものを除く）で絞り込めます。

| タグ | 内容 | 例 |
|---|---|---|
| `kanji_variant` | 異体字（旧字体 / 俗字 / 互換漢字など） | 渡邊、齋藤、櫻井 |
| `spelling_variant` | 表記の揺れ | 三ケ島（三ヶ島）、一之瀬（一ノ瀬）、佐佐木（佐々木） |
| `cp932_only` | CP932 にはあるが JIS X 0208（Shift_JIS）にはない文字を含む | 髙橋、山﨑、德永 |
| `cp932_unmappable` | CP932 に変換できない文字を含む | 𠮷田、𡈽屋 |
| `nfc_changes` | Unicode の正規化（NFC）で文字列が変わる | 大塚（互換漢字の「塚」U+FA10） |
| `surrogate_pair` | UTF-16 でサロゲートペアになる文字を含む | 𠮷田、異体字セレクタ付きのもの |
| `ivs` | 異体字セレクタを含む（見た目は 1 文字でもコードポイントは 2 つ） | 葛󠄀城、辻󠄁 |
| `iteration_mark` | 繰り返し記号「々」を含む | 佐々木、野々村 |
| `contains_kana` | ひらがな / カタカナを含む | 一ノ瀬、三ヶ島 |
| `single_char` | 見た目が 1 文字 | 林、東 |
| `long` | 見た目が 4 文字以上 | 勅使河原、勘解由小路 |
| `unusual_reading` | 漢字から読みを推測しにくい | 小鳥遊、勘解由小路 |

カタログは手作業で作っているため、文字の性質から判定できるタグ（`cp932_only`、`nfc_changes`、`surrogate_pair` など）は、テストで文字の性質と一致しているかを自動で検証しています。

### 設定を変える

サブクラスを作って設定を変更します。

```python
from pathlib import Path
from faker_ja_extended import AddressProvider, PersonProvider


class MyPersonProvider(PersonProvider):
    extended_share = 0.3       # 追加した姓が選ばれる割合（既定 0.5）
    extended_first_name_share = 0.5  # 追加した名が選ばれる割合（既定 0 = 無効）
    nasty_share = 0.01               # 意地悪な姓を混ぜる割合（既定 0 = 無効）
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
| `faker-ja-extended build` | 元データを取得して、住所 / 姓 / 名のデータをビルドする |
| `faker-ja-extended build --only surnames` | 姓だけビルドする（`addresses` で住所、`given_names` で名。`--only surnames given_names` のように複数指定も可） |
| `faker-ja-extended build --ken-all ./utf_ken_all.zip` | 取得済みの郵便番号データを使う |
| `faker-ja-extended build --jmnedict ./JMnedict.xml.gz` | 取得済みの JMnedict を使う |
| `faker-ja-extended info` | ビルド済みデータと同梱データの件数・元データの日付と、どちらが使われるかを表示する |

`faker-ja-extended` の代わりに `python -m faker_ja_extended` でも実行できます。

### 更新

元データはどちらも定期的に更新されます（郵便番号データは毎月）。

- 住所：同梱データは、郵便番号データの更新を毎月確認し、変更があればパッチバージョン（例：0.2.0 → 0.2.1）として公開します。それより新しいデータが必要な場合は、`faker-ja-extended build --only addresses` を実行してください
- 姓・名：最新の状態を保つため、定期的に `faker-ja-extended build --only surnames given_names`（名を使わない場合は `surnames` だけ）を実行し直してください

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

### 姓・名とローマ字

JMnedict のうち、種別が「姓」「名」のエントリから、漢字表記と読みの組を取り出しています。1 つの漢字に複数の読みがある姓（「新谷」の「あらたに」「しんたに」「にいや」など）は、それぞれ別の姓として扱います。

ローマ字は、読みからヘボン式（パスポート式）で生成しています。

- 長音は表記しません（さとう → Sato、おおの → Ono）
- 「ん」は b / m / p の前で m にします（なんば → Namba）
- 促音「っ」は次の子音を重ねます（はっとり → Hattori）

## 制限事項

- 住所は町域までです。丁目以降（番地 / 号 / 建物名）は生成しません
- JMnedict には姓・名の頻度の情報がないため、追加した姓はすべて同じ確率で選ばれます。珍しい姓や名が実際の分布より多く出る点に注意してください
- 名を拡張した場合、性別は目安です（[名を拡張する](#名を拡張する)を参照）
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
2. 内容に変更があれば、パッチバージョンを上げてテストを実行し、プルリクエストを作る（変更がなければ何もしない）
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

ビルドした姓・名のデータ（`surnames.json.gz`、`given_names.json.gz`）は JMnedict の派生物なので、CC BY-SA 4.0 に従います。ビルドしたデータを配布する場合は、ビルド時にデータの保存先に出力される `JMNEDICT_ATTRIBUTION.txt` を添えてください。

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
