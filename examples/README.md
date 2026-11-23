# examples

faker-ja-extended の使い方の例です。リポジトリをクローンしたうえで、`uv sync` してから実行してください。

| ファイル | 内容 | 必要なデータ |
|---|---|---|
| [generate_customers.py](generate_customers.py) | 顧客のテストデータ（氏名・フリガナ・ローマ字・メールアドレス・郵便番号・住所）を CSV に出力する | 姓（`faker-ja-extended build --only surnames`） |
| [test_nasty_surnames.py](test_nasty_surnames.py) | 意地悪な姓のカタログを pytest のパラメータ化で全件試す | 不要 |

## generate_customers.py

```sh
uv run faker-ja-extended build --only surnames
uv run python examples/generate_customers.py --count 10000 --output customers.csv
```

| オプション | 内容 |
|---|---|
| `--count` | 件数（既定: 100） |
| `--seed` | シード（既定: 0）。同じシードなら同じデータになる |
| `--output` | 出力先（省略すると標準出力） |
| `--extended-first-names` | 名も JMnedict の名で拡張する（`--only given_names` のビルドも必要） |
| `--nasty-share` | 意地悪な姓を混ぜる割合（例: `0.05`） |
| `--excel` | Excel で開けるよう BOM 付きの UTF-8 で出力する |

メールアドレスは、一意になるよう連番から作っています。ドメインは例示用に予約された `example.com` なので、誤って送信しても誰にも届きません。

## test_nasty_surnames.py

```sh
uv run pytest examples/test_nasty_surnames.py
```

「姓を正規化して保存し、検索する」簡単な顧客ストアを例に、次のようなテストを書いています。テスト対象の関数を、自分のシステムのものに置き換えて使ってください。

- どの姓でも、登録した表記で検索できるか
- 互換漢字（「塚」U+FA10 など）で登録した姓を、標準の表記で検索できるか
- 異体字セレクタやサロゲートペアを含む姓の文字数を、見た目どおりに数えられるか
- CP932 の連携先に渡すとき、変換できない姓をエラーにできるか
