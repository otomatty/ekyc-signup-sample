"""照合の前に表記ゆれをそろえる処理。

ここに入れるルールは「同じものを同じとみなす」ためのもので、
どこまでを同じとみなすかは業務判断（docs/design/05_照合ロジック設計書.md）で決める。
"""

import re
import unicodedata

# 異体字 → 標準字体。本番では、ビジネス側・法務と合意した対応表を使う。
ITAIJI_TABLE = str.maketrans(
    {
        "髙": "高",
        "﨑": "崎",
        "嵜": "崎",
        "齋": "斎",
        "齊": "斉",
        "邊": "辺",
        "邉": "辺",
        "澤": "沢",
        "濱": "浜",
        "櫻": "桜",
        "廣": "広",
        "國": "国",
        "實": "実",
        "惠": "恵",
        "眞": "真",
        "德": "徳",
    }
)

_KANJI_DIGITS = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_HYPHENS = "-‐‑‒–—―−ー"


def nfkc(text: str) -> str:
    """全角英数字→半角、全角スペース→半角スペースなどをまとめて正規化する。"""
    return unicodedata.normalize("NFKC", text)


def remove_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)


def normalize_name(name: str) -> str:
    return remove_spaces(nfkc(name))


def fold_itaiji(text: str) -> str:
    return text.translate(ITAIJI_TABLE)


def kanji_to_int(text: str) -> int:
    """'一'〜'九十九' 程度の漢数字を整数にする（住所の丁目・番地用）。"""
    if "十" in text:
        tens, _, ones = text.partition("十")
        return (_KANJI_DIGITS.get(tens, 1) if tens else 1) * 10 + (_KANJI_DIGITS.get(ones, 0) if ones else 0)
    value = 0
    for ch in text:
        value = value * 10 + _KANJI_DIGITS[ch]
    return value


def normalize_address(address: str) -> str:
    s = remove_spaces(nfkc(address))

    # 丁目・番地・番・号の前の漢数字を算用数字に: 一丁目 -> 1丁目
    s = re.sub(
        r"([〇一二三四五六七八九十]+)(?=丁目|番地|番|号)",
        lambda m: str(kanji_to_int(m.group(1))),
        s,
    )
    # 数字にはさまれたハイフン類を '-' にそろえる
    s = re.sub(rf"(?<=\d)[{_HYPHENS}](?=\d)", "-", s)

    # 1丁目2番3号 / 1丁目2番地3 -> 1-2-3
    s = re.sub(r"(\d+)丁目(\d+)番地?(\d+)号?", r"\1-\2-\3", s)
    # 1丁目2番 -> 1-2
    s = re.sub(r"(\d+)丁目(\d+)番地?", r"\1-\2", s)
    # 2番3号 / 2番地3 -> 2-3
    s = re.sub(r"(\d+)番地?(\d+)号?", r"\1-\2", s)
    # 101号室 -> 101
    s = re.sub(r"(\d+)号室", r"\1", s)
    return s
