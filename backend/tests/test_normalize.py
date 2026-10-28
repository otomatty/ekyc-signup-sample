import pytest

from app.matching.normalize import kanji_to_int, normalize_address, normalize_name


@pytest.mark.parametrize(
    ("text", "expected"),
    [("一", 1), ("九", 9), ("十", 10), ("十二", 12), ("二十", 20), ("三十五", 35)],
)
def test_kanji_to_int(text, expected):
    assert kanji_to_int(text) == expected


def test_normalize_name_removes_spaces_and_width():
    assert normalize_name("山田　太郎") == "山田太郎"
    assert normalize_name(" 山田 太郎 ") == "山田太郎"
    assert normalize_name("ＡＢＣ") == "ABC"


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("東京都千代田区サンプル町一丁目2番3号", "東京都千代田区サンプル町1-2-3"),
        ("東京都千代田区サンプル町１－２－３", "東京都千代田区サンプル町1-2-3"),
        ("東京都千代田区サンプル町1丁目2番地3", "東京都千代田区サンプル町1-2-3"),
        ("東京都千代田区サンプル町1ー2ー3", "東京都千代田区サンプル町1-2-3"),
        ("東京都 千代田区 サンプル町 1-2-3", "東京都千代田区サンプル町1-2-3"),
        ("サンプル町一丁目2番3号サンプルハイツ101号室", "サンプル町1-2-3 サンプルハイツ101"),
        ("見本町十二番三号", "見本町12-3"),
    ],
)
def test_normalize_address_equivalents(a, b):
    assert normalize_address(a) == normalize_address(b)


def test_normalize_address_keeps_katakana_long_vowel():
    # 数字にはさまれていない「ー」はハイフンにしない
    assert "サンプルハイツ" in normalize_address("1-2-3サンプルハイツ")
    assert "コーポ" in normalize_address("1-2-3コーポ")
