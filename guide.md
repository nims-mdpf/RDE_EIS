# EIS用テンプレート

## 概要
EIS（Electrochemical Impedance Spectroscopy）データをご利用の方に適したテンプレートです。以下のバリエーションが提供されています。

- DT0020
    - Bio-Logic（.mpt）
- DT0024
    - Scribner（.z）
- DT0025
    - Custom（.txt）

EISの専門家によって監修されたメタ情報を上記ファイルから自動的にRDEが抽出します。導電率データおよびインピーダンスデータの構造化処理、可視化処理を自動実行します。

- Bio-Logic EC-Lab  .mpt フォーマット、Scribner ZView  .z フォーマット、ユーザ定義 .txt フォーマットに対応
- 導電率CSV（conductivity_total / bulk / gb）に対応
- SmartTableモード対応
- マジックネーム対応（データ名を `${filename}` とすると、ファイル名をデータ名にマッピングする）

## メタ情報
- [メタ情報](docs/requirement_analysis/要件定義_EIS.xlsx)

## 基本情報

### コンテナ情報
- 【コンテナ名】nims_mdpf_shared_eis:v1.0

### テンプレート情報

- DT0020:
    - 【データセットテンプレートID】NIMS_DT0020_EIS_Biologic_v1.0
    - 【データセットテンプレート名日本語】EIS Bio-Logic データセットテンプレート
    - 【データセットテンプレート名英語】EIS Bio-Logic dataset-template
    - 【データセットテンプレートの説明】Bio-Logic製 EC-Lab electrochemistry software をご利用の方に適したテンプレートです。.mpt フォーマットのインピーダンスデータおよび導電率CSVを登録できます。EIS専門家監修のメタ情報を自動抽出し、構造化処理および可視化処理を実行します。
    - 【バージョン】1.0
    - 【データセット種別】加工・計測レシピ型
    - 【データ構造化】あり（システム上「あり」を選択）
    - 【取り扱い事業】NIMS研究および共同研究プロジェクト（PROGRAM）
    - 【装置名】（なし。装置情報を紐づける場合はこのテンプレートを複製し、装置情報を設定すること。）

- DT0024:
    - 【データセットテンプレートID】NIMS_DT0024_EIS_Scribner_v1.0
    - 【データセットテンプレート名日本語】EIS Scribner データセットテンプレート
    - 【データセットテンプレート名英語】EIS Scribner dataset-template
    - 【データセットテンプレートの説明】Scribner製 ZView impedance analysis software をご利用の方に適したテンプレートです。.z フォーマットのインピーダンスデータおよび導電率CSVを登録できます。EIS専門家監修のメタ情報を自動抽出し、構造化処理および可視化処理を実行します。
    - 【バージョン】1.0
    - 【データセット種別】加工・計測レシピ型
    - 【データ構造化】あり（システム上「あり」を選択）
    - 【取り扱い事業】NIMS研究および共同研究プロジェクト（PROGRAM）
    - 【装置名】（なし。装置情報を紐づける場合はこのテンプレートを複製し、装置情報を設定すること。）

- DT0025:
    - 【データセットテンプレートID】NIMS_DT0025_EIS_Custom_v1.0
    - 【データセットテンプレート名日本語】EIS Custom データセットテンプレート
    - 【データセットテンプレート名英語】EIS Custom dataset-template
    - 【データセットテンプレートの説明】特定装置・特定ソフトウェアに依存しないユーザ定義 .txt フォーマット向けテンプレートです。導電率CSVおよび .txt 形式のインピーダンスデータを登録できます。EIS専門家監修のメタ情報を自動抽出し、構造化処理および可視化処理を実行します。
    - 【バージョン】1.0
    - 【データセット種別】加工・計測レシピ型
    - 【データ構造化】あり（システム上「あり」を選択）
    - 【取り扱い事業】NIMS研究および共同研究プロジェクト（PROGRAM）
    - 【装置名】（なし。装置情報を紐づける場合はこのテンプレートを複製し、装置情報を設定すること。）

### データ登録方法
- 送り状画面を開いて入力ファイルに関する情報を入力する
- 「登録ファイル」欄に登録したいファイルをドラッグアンドドロップする
- SmartTable登録時は、入力データを zip 化し、`smarttable_*.xlsx/.csv/.tsv` と一緒に登録する
- 「登録開始」ボタンを押して（確認画面経由で）登録を開始する

| カタログ番号  | 対応インピーダンスファイルフォーマット  | 導電率データ（CSV）    | 備考|
| ------------- | ------------------- | --------------- | ------------- |
| **DT0020**    | `.mpt` | （`conductivity_total` 必須、`bulk` / `gb` 任意） | Bio-Logic形式向け |
| **DT0024**    |  `.z`     | （`conductivity_total` 必須、`bulk` / `gb` 任意） | ZView形式向け     |
| **DT0025**    | `.txt`  | （`conductivity_total` 必須、`bulk` / `gb` 任意） | ユーザ定義TXT形式    |


## 構成

### レポジトリ構成

```text
eis
├── README.md
├── container
│   ├── Dockerfile
│   ├── data (入出力データ)
│   ├── main.py
│   ├── modules_eis (EIS向けソースコード)
│   │   ├── Biologic
│   │   │   ├── __init__.py
│   │   │   └── mpt (mptフォーマット用)
│   │   │       ├── __init__.py
│   │   │       ├── inputfile_handler.py (入力ファイル処理)
│   │   │       └── meta_handler.py (メタデータ解析)
│   │   ├── Scribner
│   │   │   ├── __init__.py
│   │   │   └── z (zフォーマット用)
│   │   │       ├── __init__.py
│   │   │       ├── inputfile_handler.py (入力ファイル処理)
│   │   │       └── meta_handler.py (メタデータ解析)
│   │   ├── custom
│   │   │   ├── __init__.py
│   │   │   └── txt (txtフォーマット用)
│   │   │       ├── inputfile_handler.py (入力ファイル処理)
│   │   │       └── meta_handler.py (メタデータ解析)
│   │   ├── datasets_process.py (構造化処理)
│   │   ├── eisdata.py (EISデータ処理)
│   │   ├── factory.py (設定取得)
│   │   ├── inputfile_handler.py (共通入力処理)
│   │   ├── interfaces.py
│   │   ├── meta_handler.py (共通メタ処理)
│   │   └── plot_utils.py (グラフ描画)
│   ├── pip.conf
│   ├── pyproject.toml
│   ├── requirements-test.txt
│   ├── requirements.txt
│   ├── tests (テストコード)
│   └── tox.ini
├── docs (ドキュメント)
├── inputdata (サンプルデータ)
└── templates (テンプレート群)
    ├── Biologic (Biologic向け)
    │   ├── batch.yaml
    │   ├── catalog.schema.json
    │   ├── invoice.schema.json
    │   ├── jobs.template.yaml
    │   ├── metadata-def.json
    │   └── tasksupport
    │       ├── invoice.schema.json
    │       ├── metadata-def.json
    │       └── rdeconfig.yaml
    ├── Custom (Custom向け)
    │   ├── batch.yaml
    │   ├── catalog.schema.json
    │   ├── invoice.schema.json
    │   ├── jobs.template.yaml
    │   ├── metadata-def.json
    │   └── tasksupport
    │       ├── invoice.schema.json
    │       ├── metadata-def.json
    │       └── rdeconfig.yaml
    └── Scribner (Scribner向け)
        ├── batch.yaml
        ├── catalog.schema.json
        ├── invoice.schema.json
        ├── jobs.template.yaml
        ├── metadata-def.json
        └── tasksupport
            ├── invoice.schema.json
            ├── metadata-def.json
            └── rdeconfig.yaml
````

### 動作環境ファイル入出力

* DT0020（Bio-Logic）

```text
container/data
├── attachment
├── inputdata
│   ├── conductivity_total.csv
│   ├── sample_03_1.mpt
│   ├── sample_06_1.mpt
│   └── sample_06_2.mpt
├── invoice
│   └── invoice.json
├── invoice_patch
├── logs
├── main_image
│   └── conductivity_arrhenius_fit_log_sigma_t.png
├── meta
│   └── metadata.json
├── nonshared_raw
│   ├── conductivity_total.csv
│   ├── sample_03_1.mpt
│   ├── sample_06_1.mpt
│   └── sample_06_2.mpt
├── other_image
│   ├── bode_magnitude.png
│   ├── bode_magnitude_normalized.png
│   ├── bode_phase.png
│   ├── bode_phase_inverted.png
│   ├── bode_phase_inverted_normalized.png
│   ├── bode_phase_normalized.png
│   ├── cole_cole.png
│   ├── cole_cole_normalized.png
│   ├── conductivity.png
│   ├── conductivity_arrhenius_fit_log_sigma.png
│   ├── conductivity_arrhenius_log_sigma.png
│   ├── conductivity_arrhenius_log_sigma_t.png
│   ├── conductivity_total_arrhenius_fit_log_sigma.png
│   └── conductivity_total_arrhenius_fit_log_sigma_t.png
├── raw
├── structured
│   ├── conductivity_total_calc.csv
│   ├── conductivity_total_fit.csv
│   ├── eisdata.html
│   ├── sample_03_1.mpt_calc.csv
│   ├── sample_03_1.mpt_data.csv
│   ├── sample_03_1.mpt_norm.csv
│   ├── sample_06_1.mpt_calc.csv
│   ├── sample_06_1.mpt_data.csv
│   ├── sample_06_1.mpt_norm.csv
│   ├── sample_06_2.mpt_calc.csv
│   ├── sample_06_2.mpt_data.csv
│   ├── sample_06_2.mpt_norm.csv
│   └── structured_log.txt
├── tasksupport
│   ├── invoice.schema.json
│   ├── metadata-def.json
│   └── rdeconfig.yaml
├── temp
└── thumbnail
    └── conductivity_arrhenius_fit_log_sigma_t.png
```

* DT0024（Scribner）

```text
container/data
data
├── attachment
├── inputdata
│   ├── conductivity_total.csv
│   ├── sample_03_1.z
│   ├── sample_06_1.z
│   └── sample_06_2.z
├── invoice
│   └── invoice.json
├── invoice_patch
├── logs
│   └── rdesys_20260522_143812.log
├── main_image
│   └── conductivity_arrhenius_fit_log_sigma_t.png
├── meta
│   └── metadata.json
├── nonshared_raw
│   ├── conductivity_total.csv
│   ├── sample_03_1.z
│   ├── sample_06_1.z
│   └── sample_06_2.z
├── other_image
│   ├── bode_magnitude.png
│   ├── bode_magnitude_normalized.png
│   ├── bode_phase.png
│   ├── bode_phase_inverted.png
│   ├── bode_phase_inverted_normalized.png
│   ├── bode_phase_normalized.png
│   ├── cole_cole.png
│   ├── cole_cole_normalized.png
│   ├── conductivity.png
│   ├── conductivity_arrhenius_fit_log_sigma.png
│   ├── conductivity_arrhenius_log_sigma.png
│   ├── conductivity_arrhenius_log_sigma_t.png
│   ├── conductivity_total_arrhenius_fit_log_sigma.png
│   └── conductivity_total_arrhenius_fit_log_sigma_t.png
├── raw
├── structured
│   ├── conductivity_total_calc.csv
│   ├── conductivity_total_fit.csv
│   ├── eisdata.html
│   ├── sample_03_1.mpt_calc.csv
│   ├── sample_03_1.mpt_data.csv
│   ├── sample_03_1.mpt_norm.csv
│   ├── sample_06_1.mpt_calc.csv
│   ├── sample_06_1.mpt_data.csv
│   ├── sample_06_1.mpt_norm.csv
│   ├── sample_06_2.mpt_calc.csv
│   ├── sample_06_2.mpt_data.csv
│   ├── sample_06_2.mpt_norm.csv
│   └── structured_log.txt
├── tasksupport
│   ├── invoice.schema.json
│   ├── metadata-def.json
│   └── rdeconfig.yaml
├── temp
└── thumbnail
    └── conductivity_arrhenius_fit_log_sigma_t.png
```

* DT0025（Custom）

```text
container/data
data
├── attachment
├── inputdata
│   ├── conductivity_total.csv
│   ├── sample_03_1.txt
│   ├── sample_06_1.txt
│   └── sample_06_2.txt
├── invoice
│   └── invoice.json
├── invoice_patch
├── logs
│   └── rdesys_20260522_143812.log
├── main_image
│   └── conductivity_arrhenius_fit_log_sigma_t.png
├── meta
│   └── metadata.json
├── nonshared_raw
│   ├── conductivity_total.csv
│   ├── sample_03_1.txt
│   ├── sample_06_1.txt
│   └── sample_06_2.txt
├── other_image
│   ├── bode_magnitude.png
│   ├── bode_magnitude_normalized.png
│   ├── bode_phase.png
│   ├── bode_phase_inverted.png
│   ├── bode_phase_inverted_normalized.png
│   ├── bode_phase_normalized.png
│   ├── cole_cole.png
│   ├── cole_cole_normalized.png
│   ├── conductivity.png
│   ├── conductivity_arrhenius_fit_log_sigma.png
│   ├── conductivity_arrhenius_log_sigma.png
│   ├── conductivity_arrhenius_log_sigma_t.png
│   ├── conductivity_total_arrhenius_fit_log_sigma.png
│   └── conductivity_total_arrhenius_fit_log_sigma_t.png
├── raw
├── structured
│   ├── conductivity_total_calc.csv
│   ├── conductivity_total_fit.csv
│   ├── eisdata.html
│   ├── sample_03_1.mpt_calc.csv
│   ├── sample_03_1.mpt_data.csv
│   ├── sample_03_1.mpt_norm.csv
│   ├── sample_06_1.mpt_calc.csv
│   ├── sample_06_1.mpt_data.csv
│   ├── sample_06_1.mpt_norm.csv
│   ├── sample_06_2.mpt_calc.csv
│   ├── sample_06_2.mpt_data.csv
│   ├── sample_06_2.mpt_norm.csv
│   └── structured_log.txt
├── tasksupport
│   ├── invoice.schema.json
│   ├── metadata-def.json
│   └── rdeconfig.yaml
├── temp
└── thumbnail
    └── conductivity_arrhenius_fit_log_sigma_t.png
```

## データ閲覧
- データ一覧画面を開く。
- ギャラリー表示タブでは１データがタイル状に並べられている。データ名をクリックして詳細を閲覧する。
- ツリー表示タブではタクソノミーにしたがってデータを階層表示する。データ名をクリックして詳細を閲覧する。

### 動作環境

* Python: 3.12
* RDEToolKit: 1.6.4
