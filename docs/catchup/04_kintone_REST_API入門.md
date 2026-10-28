# kintone REST API 入門

このリポジトリのバッチ（`backend/batch/`）は、kintone の REST API でレコードを登録・更新します。サンプルではモック（`/mock-kintone`）を相手にしていますが、リクエストの形は本物に合わせています。

---

## 1. 基本

| 項目 | 内容 |
|---|---|
| URL | `https://<サブドメイン>.cybozu.com/k/v1/<リソース>` |
| 認証（このサンプル） | API トークンを `X-Cybozu-API-Token` ヘッダーに付ける |
| アプリの指定 | アプリID（`app`） |
| フィールドの指定 | **フィールドコード**（画面に表示される名前とは別に設定する） |

API トークンはアプリごとに発行し、「レコード閲覧」「レコード追加」「レコード編集」など、必要な権限だけを付けます。

### 1.1 レコードの形

```json
{
  "申込ID": { "value": "a825f93e-..." },
  "氏名": { "value": "山田 太郎" },
  "本人確認ステータス": { "value": "本人確認OK" }
}
```

フィールドごとに `{ "value": ... }` で包むのが特徴です。取得したレコードには `$id`（レコードID）と `$revision`（更新回数）が付きます。

---

## 2. よく使う API

### 2.1 レコードの一括取得

```bash
curl -G 'http://localhost:8000/mock-kintone/k/v1/records.json' \
  -H 'X-Cybozu-API-Token: dev-kintone-api-token' \
  --data-urlencode 'app=1' \
  --data-urlencode 'query=申込ID in ("a825f93e-...", "259b67c3-...") limit 500'
```

| クエリの例 | 意味 |
|---|---|
| `申込ID = "xxx"` | 一致 |
| `申込ID in ("a", "b")` | いずれかに一致 |
| `本人確認ステータス in ("要確認")` | ドロップダウンの値で絞り込み |
| `order by $id asc limit 500 offset 0` | 並び順と件数 |

### 2.2 レコードの一括登録

```bash
curl -X POST 'http://localhost:8000/mock-kintone/k/v1/records.json' \
  -H 'X-Cybozu-API-Token: dev-kintone-api-token' \
  -H 'Content-Type: application/json' \
  -d '{"app": 1, "records": [ {"申込ID": {"value": "test-1"}, "氏名": {"value": "テスト 太郎"}} ]}'
```

```json
{ "ids": ["6"], "revisions": ["1"] }
```

### 2.3 レコードの一括更新

```bash
curl -X PUT 'http://localhost:8000/mock-kintone/k/v1/records.json' \
  -H 'X-Cybozu-API-Token: dev-kintone-api-token' \
  -H 'Content-Type: application/json' \
  -d '{"app": 1, "records": [ {"id": "6", "record": {"氏名": {"value": "テスト 次郎"}}} ]}'
```

登録したレコードは `http://localhost:8000/mock-kintone/debug/records` で確認できます（モック独自の画面）。

---

## 3. 制限値

| 制限 | 値 | 超えた場合 |
|---|---|---|
| 同時リクエスト数 | 1ドメインにつき100件 | 101件目以降はエラー。原因のアプリだけでなく、**ドメイン全体** の API がエラーになる |
| 1日のリクエスト数 | アプリごとに、スタンダードコース1万件、ワイドコース10万件 | エラーにはならず、管理者に警告メールが届く。日本時間の午前9時にリセット |
| 一括取得 | 1回500件まで | − |
| 一括登録・更新 | 1回100件まで | − |

申込フォームから直接 kintone に書き込む構成だと、申込が集中したときに同時リクエスト数を超えるおそれがあります。このサンプルでフォームから直接書き込まず、バッチで連携する構成にしているのは、こうした制限を避けるためです。

---

## 4. 連携で気をつけること

| 論点 | 対策 | サンプルでの実装 |
|---|---|---|
| 件数制限 | 100件ずつに分ける | `kintone_client.chunked` |
| 二重登録 | キーになる項目を「値の重複を禁止する」にし、登録前に検索する | `find_ids_by_application` |
| 一時障害 | 待ってからリトライ | `KintoneClient._request` |
| 権限 | API トークンの権限を最小限に。アプリのアクセス権で、見られる人を絞る | − |
| 個人情報 | 審査に必要な項目だけ送る | カードの読み取り値は送らない |

---

## 5. モックと本物の違い

| 項目 | モック | 本物 |
|---|---|---|
| クエリ | `申込ID in (...)` と `limit` だけ対応 | 演算子、関数、並び順など多数 |
| エラーコード | `MOCK_` で始まる独自のコード | kintone 独自のコード（`GAIA_...` など） |
| データ | サーバーを止めると消える | 永続化 |
| フィールドの型チェック | なし | フィールドの種類に応じてチェックされる |

---

## 6. AI ツールとの連携

サイボウズが公式に、OSS の kintone MCP サーバーを公開しています。Claude などの AI ツールから、アプリ情報の取得やレコードの操作ができます。業務データを扱うときは、社内のルールに従ってください。

---

## 参考

- cybozu developer network: [kintone API ドキュメント](https://cybozu.dev/ja/kintone/docs/)
- cybozu developer network: [kintone連携サービスのフォームやビューワーを安全に運用する（制限値）](https://cybozu.dev/ja/kintone/tips/best-practices/secure-operation-of-forms-and-viewers)
- cybozu developer network: [kintone MCP サーバー](https://cybozu.dev/ja/kintone/ai/kintone-mcp-server)
