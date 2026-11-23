import pytest

from faker_ja_extended.kana import hira_to_kata, is_hiragana, kata_to_hira, to_hepburn


@pytest.mark.parametrize(
    ("hira", "expected"),
    [
        ("さとう", "Sato"),
        ("たかはし", "Takahashi"),
        ("おおの", "Ono"),
        ("おおうち", "Ouchi"),
        ("ゆうき", "Yuki"),
        ("いのうえ", "Inoue"),
        ("はっとり", "Hattori"),
        ("いっちょう", "Itcho"),
        ("なんば", "Namba"),
        ("ほんま", "Homma"),
        ("かんの", "Kanno"),
        ("しんや", "Shinya"),
        ("ちゅうじょう", "Chujo"),
        ("きょうごく", "Kyogoku"),
        ("ふじい", "Fujii"),
        ("いいだ", "Iida"),
        ("つづき", "Tsuzuki"),
    ],
)
def test_to_hepburn(hira: str, expected: str) -> None:
    assert to_hepburn(hira) == expected


def test_to_hepburn_rejects_unknown_chars() -> None:
    with pytest.raises(ValueError):
        to_hepburn("さとう1")


def test_kana_roundtrip() -> None:
    assert hira_to_kata("ゔぁいおりん") == "ヴァイオリン"
    assert kata_to_hira("ヴァイオリン") == "ゔぁいおりん"


def test_is_hiragana() -> None:
    assert is_hiragana("さとう")
    assert is_hiragana("えーびーしー")
    assert not is_hiragana("サトウ")
    assert not is_hiragana("")
