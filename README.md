# LightCraft iPhone試験配信

公式LightCraft v0.21.1のWeb配布物を改変せずにGitHub Pagesで配信するための小さなリポジトリです。LightCraft自体のソースフォークではありません。

予定URL: **https://lightcraft.aun-graphic.jp/v0.21.1/?workers=1**

公開設定・DNS・証明書が完了するまでは、このURLの利用可能性を保証しません。

## 動作と保存先

GitHub Pagesはアプリを配信します。写真処理はiPhoneのCPUで実行され、写真とカタログはブラウザのOPFSまたはIndexedDBに保存されます。写真のサーバーアップロード、アカウント、端末間同期は追加しません。

Safari対応・RAW現像の実用性は実機検証が必要です。アプリが起動したこととRAWが実用的に現像できたことは別々に記録します。原本は別に保持し、File → Back Up Library…でバックアップしてください。通常タブを1つ使用し、少数枚で試験します。バックアップの公式上限は4GBです。

## 固定する配布物

- [公式v0.21.1リリース](https://github.com/storytold/lightcraft/releases/tag/v0.21.1)
- ファイル: `lightcraft-web-0.21.1.zip`
- バイト数: `74569049`
- SHA-256: `57147383a46eaab3b0cc036acf9443b221450c6a19f5dc303ae165bb9678b8cb`
- ソースコミット: `361e3bc0c838ffe5e5cea515b1fe5b71951989c6`

`scripts/build_site.py`はサイズ・SHA-256を検証した後、ZIP内の全ファイルを`_site/v0.21.1/`へ展開します。アプリ本体・フォント・ライセンス・NOTICEの内容は変更しません。パストラバーサル、リンク、重複エントリー、想定外の展開量を拒否します。各アプリファイルのサイズとSHA-256は`_site/deployment.json`に記録します。写真、秘密情報、ローカルのカタログを公開物へ収集する処理はありません。

## GitHub Pagesへの手動公開

1. このディレクトリの内容だけを公開リポジトリ`lightcraft-iphone-trial`に配置します。アプリZIP・写真・ローカル作業記録はコミットしません。
2. リポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** に設定します。
3. **Custom domain** に`lightcraft.aun-graphic.jp`を指定します。DNS側ではこのサブドメインだけをリポジトリ所有者の`<owner>.github.io`へCNAME設定します。既存のルートドメイン・www・メール設定は変更しません。
4. DNSが確認され証明書が発行されたら **Enforce HTTPS** を有効にします。GitHub Actions方式では`CNAME`ファイルを置くだけでは独自ドメイン設定になりません。
5. **Actions → Deploy pinned LightCraft → Run workflow** を手動実行します。`github-pages`環境は公開元ブランチだけに制限します。
6. 成功後、HTTPSの入口、`v0.21.1/index.html`、JS、WASM、Worker、フォントの応答を確認します。WASMは`Content-Type: application/wasm`であることを確認します。

ワークフローは手動実行だけです。push・スケジュール・最新リリース追従はありません。各Actionは2026-11-15に公式リポジトリのタグから確認したコミットSHAに固定しています。

GitHub Pagesでは同梱の`_headers`と`.htaccess`は適用されません。代わりにアプリのパスを`/v0.21.1/`へ固定し、同じパスの内容を更新しないことで旧JSと新WASMの混在を避けます。独自ドメイン移行は保存領域のオリジンが変わるため、写真を取り込む前に公開URLを確定します。将来の更新はバックアップ後の別作業です。

## ローカルで配布物を準備する場合

Python 3.11以降、標準ライブラリだけを使います。独自のRustビルドは不要です。

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_site.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

`http://localhost:8765/`で確認します。`file://`では動作しません。出力先が存在する場合は上書きせず停止するため、再検証は`--output /absolute/new/output`で新しい出力先を指定します。既存ZIPを使う場合は`--archive /absolute/path/lightcraft-web-0.21.1.zip`を指定できますが、同じ固定ハッシュで必ず検証します。

生成される`_site`は一般のHTTPS静的ホストへもそのまま配置できます。約35MiBのWASMを配信でき、正しいMIME形式を返せるホストが必要です。

## iPhone 16 Pro／iOS 26での受入確認

最初はRICOH GR IIIxのDNGコピーを1枚ずつ使います。Nikon NEFはカメラ型番・ビット深度・圧縮方式を記録し、形式ごとに別判定します。GR IIIx HDF、すべてのNEF、Apple ProRAWへ結果を一般化しません。

| 確認 | 合格条件／記録する内容 |
|---|---|
| 起動 | Safari通常タブで画面が表示され、起動秒数・iOS詳細版を記録 |
| 取込み | 「ファイル」から元のDNGを選択し、ファイル名・サイズ・画素数を確認 |
| 現像 | 露出・ホワイトバランス・トリミングが反映され、待ち時間を記録 |
| 書出し | 原寸JPEGをダウンロードし、画素数・色・編集反映・書出し秒数を確認 |
| 再開 |保存完了後にSafariを閉じて開き直し、写真・編集が保持される |
| 退避 | Back Up Library…から別の場所へ保存し、Restore Library from Backup…で復元できる |
| 操作性 | 縦／横画面の操作不能、異常終了、自動再読込み、保存警告の有無を記録 |

実機結果はローカルの`results/`等へ保存し、個人のファイル名・画像・撮影位置をこの公開リポジトリにコミットしません。

### RAW本体と埋め込みJPEGを区別する

Editパネルのプレビュー代替警告を確認します。ブラウザ開発者ツールを使える場合、同じページで次を確認できます。

```js
JSON.parse(await lightcraft.command("catalog.query", "{}"))
```

各写真の`previewOnly`が文字列ならプレビュー代替理由です。`null`はカタログ上で代替なしを示しますが、実ロード時の後段フォールバックを完全には否定できません。公式ZIPの公開コマンドでは実ローダーの`SourceInfo.raw`を直接観測する経路は確認できていません。RAW本体の使用を確認できない場合、RAW対応の判定は保留し、「読込み・現像操作・原寸書出し、警告なし」までを区別して記録します。

問題は元の試験プロジェクトの`feature-backlog.json`へ、対象版・形式・再現手順・期待結果・受入条件を添えて記録します。原因未確定のまま写真の原本を書き換えたり、Safariの保存データを消したりしません。

## 出典と権利表示

- [公式ホスティング手順](https://github.com/storytold/lightcraft/blob/v0.21.1/packaging/web/README.md)
- [Web版の仕様と制限](https://github.com/storytold/lightcraft/blob/v0.21.1/docs/web.md)
- [RAW検証記録](https://github.com/storytold/lightcraft/blob/v0.21.1/docs/raw/coverage.tsv)
- [RAW状態の照会実装](https://github.com/storytold/lightcraft/blob/v0.21.1/crates/engine/src/cmd/query.rs)
- [実ロードのフォールバック実装](https://github.com/storytold/lightcraft/blob/v0.21.1/crates/engine/src/files/load.rs)
- [MIT](https://github.com/storytold/lightcraft/blob/v0.21.1/LICENSE-MIT)／[Apache-2.0](https://github.com/storytold/lightcraft/blob/v0.21.1/LICENSE-APACHE)／[NOTICE](https://github.com/storytold/lightcraft/blob/v0.21.1/NOTICE)
- [ブランド条件](https://github.com/storytold/lightcraft/blob/v0.21.1/docs/brand/LICENSE-brand.txt)

LightCraftの権利は開発元および各権利者に帰属します。本サイトは非公式の個人試験配信で、開発元の運営・承認・サポートを示しません。アプリ内の表示・配布物のライセンスは保持し、入口ページに開発元のロゴは追加しません。
