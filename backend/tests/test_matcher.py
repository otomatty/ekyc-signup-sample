from datetime import date

from app.matching import PersonData, evaluate
from app.matching.matcher import FieldResult, match_address, match_gender, match_name
from app.models import ApplicationStatus


def person(**overrides) -> PersonData:
    base = {
        "name": "山田 太郎",
        "birth_date": date(1990, 4, 1),
        "gender": "male",
        "address": "東京都千代田区サンプル町1-2-3",
    }
    return PersonData(**(base | overrides))


def test_all_match_is_verified():
    outcome = evaluate(person(), person(address="東京都千代田区サンプル町一丁目2番3号"))
    assert outcome.overall == ApplicationStatus.VERIFIED
    assert all(c.result == FieldResult.MATCH for c in outcome.checks)


def test_itaiji_name_needs_review():
    outcome = evaluate(person(name="高橋 花子"), person(name="髙橋 花子"))
    assert outcome.overall == ApplicationStatus.NEEDS_REVIEW
    assert match_name("高橋 花子", "髙橋 花子").result == FieldResult.PARTIAL


def test_different_name_is_rejected():
    assert match_name("山田 太郎", "山田 次郎").result == FieldResult.MISMATCH
    assert evaluate(person(), person(name="山田 次郎")).overall == ApplicationStatus.REJECTED


def test_birth_date_mismatch_is_rejected():
    assert evaluate(person(), person(birth_date=date(1990, 4, 2))).overall == ApplicationStatus.REJECTED


def test_building_name_difference_is_partial():
    check = match_address("東京都千代田区サンプル町1-2-3 サンプルハイツ101", "東京都千代田区サンプル町一丁目2番3号")
    assert check.result == FieldResult.PARTIAL


def test_address_number_prefix_is_not_partial():
    # 1-2-3 と 1-2-35 は別の住所。先頭一致でも PARTIAL にしない
    assert match_address("サンプル町1-2-3", "サンプル町1-2-35").result == FieldResult.MISMATCH
    assert match_address("サンプル町1-2-3", "サンプル町1-2-3-4").result == FieldResult.MISMATCH


def test_different_address_is_rejected():
    outcome = evaluate(person(), person(address="大阪府大阪市北区旧住所町3-4-5"))
    assert outcome.overall == ApplicationStatus.REJECTED


def test_gender_skipped_when_not_answered():
    assert match_gender(None, "male").result == FieldResult.SKIPPED
    assert evaluate(person(gender=None), person()).overall == ApplicationStatus.VERIFIED
