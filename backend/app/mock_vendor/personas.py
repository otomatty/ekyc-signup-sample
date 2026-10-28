"""モックベンダーで選べる「テスト用カード」。

実物のマイナンバーカードを読む代わりに、カードに入っている情報をここで定義する。
フロントの「サンプル入力」ボタン（frontend/src/samples.ts）と組み合わせると、各ケースを再現できる。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CardIdentity:
    name: str
    birth_date: str
    gender: str | None
    address: str


@dataclass(frozen=True)
class Persona:
    key: str
    label: str
    description: str
    identity: CardIdentity | None = None
    failure_reason: str | None = None


PERSONAS: dict[str, Persona] = {
    p.key: p
    for p in [
        Persona(
            key="match",
            label="山田 太郎",
            description="申込と一致するケース（住所の書き方だけ違う）",
            identity=CardIdentity(
                name="山田 太郎",
                birth_date="1990-04-01",
                gender="male",
                address="東京都千代田区サンプル町一丁目2番3号サンプルハイツ101号室",
            ),
        ),
        Persona(
            key="itaiji",
            label="髙橋 花子",
            description="カードの氏名が異体字（髙）のケース",
            identity=CardIdentity(
                name="髙橋 花子",
                birth_date="1985-11-20",
                gender="female",
                address="神奈川県横浜市西区みなと見本二丁目5番8号",
            ),
        ),
        Persona(
            key="building",
            label="鈴木 一郎",
            description="カードに建物名がないケース",
            identity=CardIdentity(
                name="鈴木 一郎",
                birth_date="1972-02-29",
                gender="male",
                address="埼玉県さいたま市大宮区見本台四丁目5番6号",
            ),
        ),
        Persona(
            key="moved",
            label="佐藤 次郎",
            description="引っ越し後、カードの住所が古いままのケース",
            identity=CardIdentity(
                name="佐藤 次郎",
                birth_date="1978-07-15",
                gender="male",
                address="大阪府大阪市北区旧住所町三丁目4番5号",
            ),
        ),
        Persona(
            key="revoked",
            label="電子証明書が失効",
            description="証明書が失効していて本人確認できないケース",
            failure_reason="CERT_REVOKED",
        ),
        Persona(
            key="locked",
            label="パスワードロック",
            description="署名用パスワードを間違えすぎてロックされたケース",
            failure_reason="PIN_LOCKED",
        ),
    ]
}
