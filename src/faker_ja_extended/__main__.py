"""``python -m faker_ja_extended`` でデータビルド用のコマンドを実行する。

Windows のスマートアプリコントロールが有効な環境では、uv が作る
``faker-ja-extended.exe`` などのラッパーがブロックされることがあるため、こちらを使う。
"""

from faker_ja_extended.build.cli import main

main()
