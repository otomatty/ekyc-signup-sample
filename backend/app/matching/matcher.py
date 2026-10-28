"""申込内容と、カードから取得した基本4情報の照合。

項目ごとに MATCH / PARTIAL / MISMATCH / SKIPPED を判定し、総合判定を決める。

    いずれかが MISMATCH          -> REJECTED      （照合NG）
    MISMATCH はなく PARTIAL あり -> NEEDS_REVIEW  （担当者が目視確認）
    すべて MATCH（か SKIPPED）   -> VERIFIED      （本人確認OK）

この判定表は docs/design/05_照合ロジック設計書.md と対応している。
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from app.models import ApplicationStatus

from .normalize import fold_itaiji, normalize_address, normalize_name


class FieldResult(StrEnum):
    MATCH = "MATCH"
    PARTIAL = "PARTIAL"
    MISMATCH = "MISMATCH"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class PersonData:
    name: str
    birth_date: date
    gender: str | None
    address: str


@dataclass(frozen=True)
class FieldCheck:
    field: str
    label: str
    result: FieldResult
    note: str = ""


@dataclass(frozen=True)
class MatchOutcome:
    overall: ApplicationStatus
    checks: list[FieldCheck] = field(default_factory=list)


def match_name(applied: str, verified: str) -> FieldCheck:
    a, v = normalize_name(applied), normalize_name(verified)
    if a == v:
        return FieldCheck("name", "氏名", FieldResult.MATCH)
    if fold_itaiji(a) == fold_itaiji(v):
        return FieldCheck("name", "氏名", FieldResult.PARTIAL, "異体字の違いのみ")
    return FieldCheck("name", "氏名", FieldResult.MISMATCH, "氏名が一致しません")


def match_birth_date(applied: date, verified: date) -> FieldCheck:
    if applied == verified:
        return FieldCheck("birth_date", "生年月日", FieldResult.MATCH)
    return FieldCheck("birth_date", "生年月日", FieldResult.MISMATCH, "生年月日が一致しません")


def match_gender(applied: str | None, verified: str | None) -> FieldCheck:
    if not applied or not verified:
        return FieldCheck("gender", "性別", FieldResult.SKIPPED, "申込で未回答のため照合しない")
    if applied == verified:
        return FieldCheck("gender", "性別", FieldResult.MATCH)
    return FieldCheck("gender", "性別", FieldResult.MISMATCH, "性別が一致しません")


def match_address(applied: str, verified: str) -> FieldCheck:
    a, v = normalize_address(applied), normalize_address(verified)
    if a == v:
        return FieldCheck("address", "住所", FieldResult.MATCH)

    # 片方がもう片方の先頭部分と一致し、残りが建物名・部屋番号だけと考えられる場合
    shorter, longer = sorted((a, v), key=len)
    if longer.startswith(shorter):
        rest = longer[len(shorter):]
        # 「1-2-3」と「1-2-35」のように番地の途中で切れている場合は一致とみなさない
        if rest and not rest[0].isdigit() and rest[0] != "-":
            return FieldCheck("address", "住所", FieldResult.PARTIAL, "建物名・部屋番号の有無が異なる")
    return FieldCheck("address", "住所", FieldResult.MISMATCH, "住所が一致しません")


def evaluate(applied: PersonData, verified: PersonData) -> MatchOutcome:
    checks = [
        match_name(applied.name, verified.name),
        match_birth_date(applied.birth_date, verified.birth_date),
        match_gender(applied.gender, verified.gender),
        match_address(applied.address, verified.address),
    ]
    results = {c.result for c in checks}
    if FieldResult.MISMATCH in results:
        overall = ApplicationStatus.REJECTED
    elif FieldResult.PARTIAL in results:
        overall = ApplicationStatus.NEEDS_REVIEW
    else:
        overall = ApplicationStatus.VERIFIED
    return MatchOutcome(overall=overall, checks=checks)
