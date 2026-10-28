# FastAPI 復習ガイド

このリポジトリの `backend/` を教材に、FastAPI と「外部と連携する API」の勘所を復習します。

---

## 1. 全体像

```mermaid
flowchart LR
  R["リクエスト"] --> V["Pydantic で<br>入力チェック"]
  V --> D["Depends で<br>必要なものを注入"]
  D --> H["エンドポイント関数"]
  H --> S["レスポンスモデルで<br>出力を整形"]
  S --> O["JSON"]
```

FastAPI は、関数の **型ヒント** から入力チェック、ドキュメント（`/docs`）、レスポンスの整形を自動で行います。

---

## 2. エンドポイント

```python
# app/routers/applications.py
router = APIRouter(prefix="/api/applications", tags=["applications"])

@router.post("", status_code=201, response_model=ApplicationCreated)
def create_application(
    body: ApplicationCreate,                         # 本文（JSON）→ Pydantic で検証
    conn: sqlite3.Connection = Depends(get_conn),    # 依存性の注入
    settings: Settings = Depends(get_app_settings),
) -> ApplicationCreated:
    ...
```

| 引数の書き方 | 値の取り出し元 |
|---|---|
| `application_id: str`（パスに `{application_id}` がある） | パス |
| `q: str = ""`（パスにない単純な型） | クエリ文字列 |
| `body: SomeModel`（Pydantic モデル） | JSON 本文 |
| `x: str = Header(...)` | ヘッダー |
| `x: str = Form(...)` | フォーム（`python-multipart` が必要） |
| `request: Request` | 生のリクエスト（Webhook の生本文など） |

`response_model` を指定すると、モデルにない項目は返されません。うっかり内部の値を返してしまう事故を防げます。

---

## 3. Pydantic v2

```python
# app/models.py
class ApplicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    birth_date: date                                  # "1990-04-01" を date に変換
    postal_code: str = Field(pattern=r"^\d{3}-?\d{4}$")

    @field_validator("birth_date")
    @classmethod
    def check_age(cls, v: date) -> date:
        if age(v) < 18:
            raise ValueError("18歳以上の方のみお申込みいただけます")
        return v
```

| v1 の書き方 | v2 の書き方 |
|---|---|
| `@validator` | `@field_validator` |
| `@root_validator` | `@model_validator(mode="after")` |
| `Model.parse_raw(s)` | `Model.model_validate_json(s)` |
| `obj.dict()` | `obj.model_dump()` |
| `class Config:` | `model_config = ConfigDict(...)` |

設定値は `pydantic-settings` の `BaseSettings` で、環境変数や `.env` から読みます（`app/config.py`）。

---

## 4. Depends（依存性の注入）

```python
# app/deps.py
def get_conn(settings: Settings = Depends(get_app_settings)) -> Iterator[sqlite3.Connection]:
    conn = connect(settings.db_path)
    try:
        yield conn          # ここでエンドポイントが動く
    finally:
        conn.close()        # 終わったら必ず閉じる

def application_id_from_bearer(authorization: str | None = Header(default=None), ...) -> str:
    # ヘッダーのトークンを検証して申込IDを返す。だめなら 401
```

- 依存性は入れ子にできる（`get_conn` が `get_app_settings` を使う）
- `yield` を使うと、後片付けを書ける
- テストでは `app.dependency_overrides[get_vendor_client] = ...` で差し替えられる（`tests/conftest.py`）

---

## 5. `async def` と `def`

| | 使いどころ |
|---|---|
| `async def` | 中で `await` するとき（httpx の非同期クライアントなど） |
| `def` | ブロッキングな処理だけのとき。FastAPI がスレッドで実行してくれる |

**注意:** `async def` の中でブロッキングな処理（`requests.get`、`time.sleep` など）をすると、サーバー全体が止まります。このサンプルでは `ekyc.py` が `async def` の中で sqlite3 を呼んでいますが、処理が軽いので許容しています。本番では非同期対応のドライバを使うか、`def` にします。

---

## 6. 外部 API を呼ぶときの型

```python
# app/services/ekyc_vendor.py（要点）
async with httpx.AsyncClient(timeout=self.timeout) as client:
    for attempt in range(1, self.max_attempts + 1):
        try:
            res = await client.post(url, json=body, headers=headers)
        except httpx.TransportError:
            ...                                   # 通信エラー → リトライ
        else:
            if res.status_code < 400:
                return parse(res)
            if res.status_code not in {429, 500, 502, 503, 504}:
                raise VendorError(...)            # 4xx → リトライしない
        await asyncio.sleep(backoff * 2 ** (attempt - 1))  # 0.5秒、1秒…と間隔を広げる
```

| 原則 | 理由 |
|---|---|
| タイムアウトを必ず指定する | 相手が応答しないと、こちらも詰まる |
| 一時的な失敗だけリトライする | 4xx はこちらの誤りなので、何度送っても失敗する |
| 間隔を広げながらリトライする（指数バックオフ） | 相手の回復を待つ。一斉に再送しない |
| 失敗したら利用者向けのメッセージに変える | 内部エラーをそのまま見せない（502 と案内文） |

---

## 7. Webhook を受けるときの型

```python
# app/routers/ekyc.py（要点）
@router.post("/callback")
async def receive_callback(request: Request, ...):
    raw = await request.body()                       # 1. 生の本文を取る
    verify_webhook(raw, secret, signature, timestamp, tolerance)  # 2. 署名と時刻を検証
    callback = VendorCallback.model_validate_json(raw)            # 3. 形式を検証
    ...
    if not repository.save_result(...):              # 4. event_id が重複なら保存しない
        return {"status": "duplicate"}               #    それでも 200 を返す
    return {"status": "accepted"}
```

| 原則 | 理由 |
|---|---|
| 署名は生の本文で検証する | JSON として読み直すと、順序や空白が変わって署名が合わなくなる |
| タイムスタンプも検証する | 盗まれた通信の再送（リプレイ）を防ぐ |
| 冪等にする（同じイベントは1回だけ処理） | 送り手は、成功の応答を受け取れなければ再送してくる |
| 重複にも 200 を返す | エラーを返すと、送り手が再送し続ける |
| 処理は短く、重い処理は後回し | 送り手のタイムアウトで再送されるのを防ぐ |

---

## 8. テスト

```python
# tests/conftest.py（要点）
@pytest.fixture
def app(settings):
    app = create_app(settings)                       # テスト用の設定（一時DB）で作る
    app.dependency_overrides[get_vendor_client] = lambda: EkycVendorClient(
        ..., transport=httpx.ASGITransport(app=app)  # 外部呼び出しを同じアプリ内のモックへ
    )
    return app

@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c
```

- `TestClient` はサーバーを立てずに API を呼べる
- `monkeypatch` で関数を差し替え、外部送信を横取りできる（`captured_callbacks`）
- テスト名を日本語の仕様のように読めるようにしておくと、仕様書の代わりになる

```bash
cd backend
pytest -v                           # 全テスト
pytest tests/test_matcher.py -v     # ファイル単位
pytest -k duplicate -v              # 名前で絞り込み
```

---

## 9. 手で API を叩いてみる

```bash
# 申込
curl -s -X POST http://localhost:8000/api/applications \
  -H 'Content-Type: application/json' \
  -d '{"name":"山田 太郎","birth_date":"1990-04-01","gender":"male","postal_code":"100-0001",
       "address":"東京都千代田区サンプル町1-2-3","phone":"090-1234-5678",
       "email":"taro@example.com","plan":"standard"}'

# 上で返った application_id と handoff_token を入れて状態を見る
curl -s http://localhost:8000/api/applications/<application_id> \
  -H 'Authorization: Bearer <handoff_token>'

# 入力エラー（18歳未満）の応答を見る
curl -s -X POST http://localhost:8000/api/applications \
  -H 'Content-Type: application/json' -d '{"name":"x","birth_date":"2015-01-01"}'
```

`http://localhost:8000/docs` の「Try it out」からも同じことができます。

---

## 10. よくある落とし穴

| 落とし穴 | 対策 |
|---|---|
| `async def` の中でブロッキング処理 | 5章 |
| レスポンスに内部の値が混ざる | `response_model` を指定する |
| エラー時に例外の中身をそのまま返す | `HTTPException` で利用者向けの文言にする。詳細はログへ |
| 設定値をコードに直書き | `BaseSettings` で環境変数から読む |
| 外部 API を毎回本物で叩くテスト | 依存性の差し替えやモックで切り離す |

---

## 11. 参考

- FastAPI 公式（日本語あり）: https://fastapi.tiangolo.com/ja/
- Pydantic: https://docs.pydantic.dev/
- HTTPX: https://www.python-httpx.org/
