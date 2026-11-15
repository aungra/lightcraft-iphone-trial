# LightCraft iPhone試験配信

[LightCraft v0.21.1](https://github.com/storytold/lightcraft/releases/tag/v0.21.1)を基にしたiPhone向けレイアウト修正版と、無改変の公式Web配布物をGitHub Pagesで配信するリポジトリです。開発元による運営・承認・サポートを示すものではありません。

- iPhone向け修正版の公開先: **https://lightcraft.aun-graphic.jp/iphone-r1/?workers=1**
- 無改変の公式版: https://lightcraft.aun-graphic.jp/v0.21.1/?workers=1

修正版は、完全な品質ゲート・成果物レビュー・手動公開を終えるまで利用可能とは扱いません。同じオリジンに置くため、ブラウザ内のライブラリは両版で共有されます。切り替え前にバックアップし、同時に2つのタブで開かないでください。

## 動作と保存先

サーバーはアプリを配信します。写真処理はiPhone側で行い、写真とカタログはブラウザのOPFSまたはIndexedDBに保存します。写真アップロードサービスやアカウント、端末間の自動同期は追加しません。

原本は別に保持し、File → Back Up Library…でバックアップしてください。ブラウザのサイトデータ削除や容量整理により消える場合があります。少数枚・通常タブ1つで試験します。公式バックアップ上限は4GBです。

## ビルド入力の固定

| 入力 | 固定値 |
|---|---|
| LightCraftソース | `361e3bc0c838ffe5e5cea515b1fe5b71951989c6`（v0.21.1） |
| ローカル変更 | `patches/iphone-layout.patch` |
| craft-fonts | `b076417b5880bd4154bd22f00695b1d28c6bea83`（公式v0.21.1と同じ） |
| Rust | `1.100.0` |
| wasm-bindgen CLI | ソースのCargo.lockから取得する完全一致版（現在`0.2.129`） |
| 実行場所 | GitHubの標準`ubuntu-24.04`ランナー |

上流の共有リリースワークフローは`stable`を指定します。本リポジトリでは[2026-11-12公開のRust 1.100.0](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/)へ固定します。日本語BIZ UDPGothicを含むフォントを`CRAFT_FONTS_REQUIRED=1`で必須とし、フォントのないビルドへ自動的に切り替えません。公式配布WASMは修正版に流用せず、パッチを適用したソースから新しいWASMを作ります。

無改変の公式版は次の配布ZIPから毎回作り、サイズとSHA-256を確認します。

- `lightcraft-web-0.21.1.zip`: `74569049` bytes
- SHA-256: `57147383a46eaab3b0cc036acf9443b221450c6a19f5dc303ae165bb9678b8cb`

## 修正版の作成と公開

1. `codex/`ブランチからPRを作ります。**Build and test iPhone candidate**はPRまたは手動で実行され、公開権限を持ちません。
2. 固定ソース・フォントを取得してパッチを適用し、Python梱包試験と、実際のWebページ内モジュールを使うNode viewport試験を実行します。
3. **`cargo xtask ci`を省略せず実行**します。fmt・clippy・HEIF・tests・parity・layers・assets・roots・WASMの全段階成功を要求し、`--quick`の結果では公開できません。実行は1ランナーで順番に進め、ゲートの内部期限は80分、ジョブ全体は150分です。GPUやコーパス等の試験スキップは報告書へ残し、実機合格と同一視しません。
4. 成功後、`cargo xtask web`と公式の梱包スクリプトで修正版を作ります。`scripts/build_site.py`が無改変`/v0.21.1/`と修正版`/iphone-r1/`をまとめます。
5. **`iphone-r1-candidate`**（14日保持）を取得してレビューします。全ファイルのSHA-256を含む`candidate.json`、修正版の`build-provenance.json`、適用パッチ、ライセンスを同梱します。成功／失敗時とも**`iphone-r1-gate-evidence`**へゲート報告書とログを保存します。
6. レビューした内容をPR経由で`main`に統合します。候補のソースツリーと`main`のツリーが一致していることが必要です。レビュー後に内容を変更した場合は新しい候補が必要です。
7. `main`で **Publish reviewed iPhone candidate → Run workflow**を手動実行し、成功した候補の`candidate_run_id`と`candidate.json`内の`build.source_commit`（40桁）を指定します。
8. 公開ジョブは、指定実行がこのリポジトリの成功した候補ビルドであること、ソースとパッチがレビュー済み`main`と一致すること、成果物全ファイルのサイズとハッシュを検証します。再ビルドせず、その成果物をPagesへ公開します。

以前の「公式版だけを再公開する」ワークフローは置き換えました。通常操作で`/iphone-r1/`を消してしまう再公開経路は残しません。旧版への操作上の切り替えは、保持した`/v0.21.1/`を開きます。自動の本番公開・スケジュール更新・最新版追従はありません。公開された`iphone-r1`の内容を後で変更する場合は、別のリビジョン用パスを新しい作業として用意します。

## GitHub Pagesと独自ドメイン

- Settings → Pages → Sourceは**GitHub Actions**。
- Custom domainは`lightcraft.aun-graphic.jp`、このサブドメインのCNAMEだけを`aungra.github.io`へ設定。
- **Enforce HTTPS**を有効にし、`github-pages`環境からの公開を`main`だけに制限。
- 既存のルートドメイン・www・メール設定は変更しません。Actions方式では`CNAME`ファイルだけでは独自ドメイン設定になりません。
- Pagesでは同梱の`_headers`・`.htaccess`は使われません。版ごとのパスと固定された成果物で、旧JSと新WASMが混ざる更新を避けます。

公開後はHTTPS、HTML・JS・WASM・Worker・フォント・ライセンスの応答とファイルハッシュを確認します。WASMのMIME形式は`application/wasm`が必要です。

## ローカルで行う軽い確認

Python梱包試験にはPython 3.11以降の標準ライブラリを使用します。Macで重いRustビルドをする必要はありません。

```sh
python3 -m unittest discover -s tests -v
node tests/test_viewport.mjs /path/to/patched-source/apps/lightcraft-web/index.html
```

公式版だけを新しいローカル出力先に用意する場合は`python3 scripts/build_site.py --output /absolute/new/output`を使えます。公開操作にはなりません。出力先が既存なら上書きを拒否します。ZIP・生成サイト・ユーザーの写真・検証結果はコミットしません。

## iPhone実機での受入確認

対象はiPhone 16 Pro／iOS 26。最初はRICOH GR IIIxのDNGコピーを1枚ずつ使い、JPEGでの結果とも区別します。Nikon NEFは機種・ビット深度・圧縮形式を記録して別判定します。

| 項目 | 確認内容 |
|---|---|
| 縦画面 | メニューが画面内に開き、編集パネルを最後まで操作できる |
| Safariの表示領域 | アドレスバー表示／収納、回転、キーボード表示で重要操作が隠れない |
| 現像 | 露出・ホワイトバランス・トリミングが反映される |
| 書出し | 原寸JPEGの画素数・色・編集結果と所要時間を確認 |
| 再開 | 保存完了後、Safariを閉じて開いて写真・編集内容を保持 |
| バックアップ | Back Up Library…とRestore Library from Backup…で退避・復元 |
| 安定性 | 操作不能、クラッシュ、勝手な再読込み、保存警告を記録 |

iPhone実機結果は公開リポジトリとは別の検証記録に残します。CIの成功はiPhone実機での合格を意味しません。

### RAW本体と埋め込みプレビュー

Editパネルのプレビュー代替警告を確認します。ブラウザ内の`JSON.parse(await lightcraft.command("catalog.query", "{}"))`で写真の`previewOnly`も確認できます。文字列なら代替理由、`null`ならカタログ上は代替なしです。ただし実ローダーで後から代替する経路があり、`null`だけではRAW本体の使用を証明できません。未確認のRAW判定は保留し、表示・操作・書出しの結果と区別します。

問題は元の試験プロジェクトの`feature-backlog.json`に対象版・形式・再現条件・期待結果・受入条件を記録します。原因未確定のまま原本やブラウザ内保存データを消しません。

## 出典と権利表示

[公式ホスティング手順](https://github.com/storytold/lightcraft/blob/v0.21.1/packaging/web/README.md)、[Web版仕様](https://github.com/storytold/lightcraft/blob/v0.21.1/docs/web.md)、[RAW検証](https://github.com/storytold/lightcraft/blob/v0.21.1/docs/raw/coverage.tsv)、[ブランド条件](https://github.com/storytold/lightcraft/blob/v0.21.1/docs/brand/LICENSE-brand.txt)。

修正版はLightCraftを基にした非公式ビルドと明示し、ArtCraftのブランドマークを除去します。MIT／Apache-2.0、NOTICEと各フォントのライセンスは保持します。無改変の公式版は独立したパスにそのまま保持します。
