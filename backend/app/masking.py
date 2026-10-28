"""個人情報のマスキング。

ログ、画面、連携先に出すときに使う。
原則: ログには個人情報を出さない。どうしても識別が要る場面だけマスクして出す。
"""

import re

MASK = "＊"


def mask_name(name: str) -> str:
    """'山田 太郎' -> '山田 ＊＊'、スペースがなければ先頭1文字だけ残す。"""
    name = name.strip()
    if not name:
        return ""
    parts = re.split(r"[ 　]+", name, maxsplit=1)
    if len(parts) == 2:
        return f"{parts[0]} {MASK * len(parts[1])}"
    return name[0] + MASK * (len(name) - 1)


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 4:
        return MASK * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return MASK * 3
    return f"{local[:1]}***@{domain}"


def mask_address(address: str) -> str:
    """都道府県＋市区町村まで残し、それ以降を伏せる。"""
    m = re.match(r"^(.{2,3}?[都道府県])?(.+?[市区町村])", address)
    if m:
        return m.group(0) + "…"
    return address[:4] + "…"


def mask_birth_date(birth_date: str) -> str:
    return birth_date[:4] + "-**-**" if len(birth_date) >= 4 else "****"
