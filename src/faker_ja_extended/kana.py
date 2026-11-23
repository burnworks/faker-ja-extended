"""かなの変換（ひらがな・カタカナの相互変換、ヘボン式ローマ字）。"""

from __future__ import annotations

_HIRA_START, _HIRA_END = 0x3041, 0x3096  # ぁ〜ゖ
_KATA_OFFSET = 0x60

_TO_KATA = {c: c + _KATA_OFFSET for c in range(_HIRA_START, _HIRA_END + 1)}
_TO_HIRA = {v: k for k, v in _TO_KATA.items()}


def hira_to_kata(text: str) -> str:
    return text.translate(_TO_KATA)


def kata_to_hira(text: str) -> str:
    return text.translate(_TO_HIRA)


def is_hiragana(text: str) -> bool:
    """ひらがなと長音記号だけで構成されているか。"""
    return bool(text) and all(_HIRA_START <= ord(c) <= _HIRA_END or c == "ー" for c in text)


_BASE: dict[str, str] = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "i", "ゑ": "e", "を": "o",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ゔ": "vu",
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o",
    "ゃ": "ya", "ゅ": "yu", "ょ": "yo", "ゎ": "wa",
}  # fmt: skip

_YOUON_HEAD: dict[str, str] = {
    "き": "ky", "ぎ": "gy", "し": "sh", "じ": "j", "ち": "ch", "ぢ": "j",
    "に": "ny", "ひ": "hy", "び": "by", "ぴ": "py", "み": "my", "り": "ry",
}  # fmt: skip
_YOUON_TAIL = {"ゃ": "a", "ゅ": "u", "ょ": "o"}

_SOKUON = "っ"
_HATSUON = "ん"
_CHOON = "ー"


def _tokenize(hira: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(hira):
        ch = hira[i]
        nxt = hira[i + 1] if i + 1 < len(hira) else ""
        if ch in _YOUON_HEAD and nxt in _YOUON_TAIL:
            tokens.append(_YOUON_HEAD[ch] + _YOUON_TAIL[nxt])
            i += 2
            continue
        if ch in (_SOKUON, _HATSUON, _CHOON):
            tokens.append(ch)
        elif ch in _BASE:
            tokens.append(_BASE[ch])
        else:
            raise ValueError(f"ローマ字に変換できない文字があります: {ch!r} in {hira!r}")
        i += 1
    return tokens


def to_hepburn(hira: str) -> str:
    """ひらがなをヘボン式ローマ字（パスポート式）に変換する。

    - 長音は表記しない（さとう → Sato、おおの → Ono、ゆうき → Yuki）
    - 撥音「ん」は b・m・p の前で m（なんば → Namba）
    - 促音「っ」は次の子音を重ね、ch の前は t（はっとり → Hattori、いっちょう → Itcho）

    読みだけでは語の切れ目が分からないため、長音の判定は近似になる。
    「うえ」の「う」だけは縮めない例外を設けている（いのうえ → Inoue）。
    """
    tokens = _tokenize(hira)
    out: list[str] = []
    prev_absorbed = False  # 直前で長音を吸収したか（「おおう」を 1 回だけ縮めるため）
    for idx, tok in enumerate(tokens):
        nxt = tokens[idx + 1] if idx + 1 < len(tokens) else ""
        if tok == _CHOON:
            continue
        if tok == _SOKUON:
            if nxt and nxt not in (_SOKUON, _HATSUON, _CHOON) and nxt[0] not in "aiueo":
                out.append("t" if nxt.startswith("ch") else nxt[0])
            continue
        if tok == _HATSUON:
            out.append("m" if nxt[:1] in ("b", "m", "p") else "n")
            prev_absorbed = False
            continue
        last = out[-1] if out else ""
        # 「うえ」（上など）の「う」は長音ではないことが多いので縮めない（いのうえ → Inoue）
        is_ue = tok == "u" and nxt == "e"
        if (
            not prev_absorbed
            and not is_ue
            and last
            and ((last.endswith("o") and tok in ("u", "o")) or (last.endswith("u") and tok == "u"))
        ):
            prev_absorbed = True
            continue
        out.append(tok)
        prev_absorbed = False
    return "".join(out).capitalize()
