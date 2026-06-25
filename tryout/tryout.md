# RDEデータセットテンプレート `EIS` を試してみる

RDEデータセットテンプレート `EIS` をローカル開発環境で動かす方法を説明します。

なお、入力する測定データ（RAWデータ）は提供していませんので各自でご用意ください。

---

# 準備

以下の開発環境を用意してください。

* Python ver3.11以上

  * RDEの構造化処理プログラムはPythonを用いています
* pyenvなど仮想環境で動作させることを推奨

  * この説明ではpyenvを利用

## ファイル一式の入手

* git clone または download zip でファイル一式を取得
* zipファイルで取得した場合は適宜フォルダに解凍する
* この説明では入手したファイルの解凍先を `work` フォルダと呼ぶことにします

---

# ファイルなどの説明

workフォルダには以下の内容のフォルダが用意されています。

* container

  * 構造化処理プログラム一式が含まれています
  * このフォルダの下でテスト実行します
  * 利用するPythonパッケージは requirements.txt を参照

* docs

  * 説明書など

* templates

  * 構造化処理プログラム以外のデータセットテンプレートを構成するファイルが含まれています
  * テンプレートによって含まれるファイル構成が異なります

* inputdata

  * サンプルデータ配置用フォルダ

---

## 動かしてみる、それと解説

動かしてみるまでの手順は以下の通り

1. 仮想環境作成
2. ファイルの配置
3. プログラムの実行

テンプレートの選択

* RDE_EISデータセットテンプレートは、Bio-Logic製 EC-Lab の .mpt形式、Scribner製 ZView の .z形式、およびユーザ定義 .txt形式のEISデータに対応しています
* 利用時はBiologic、Scribner、Customのいずれかを選択します（複数形式を同時に扱うことはできません）
* templatesフォルダには、Biologic用、Scribner用、Custom用それぞれのテンプレートが収められています

### 仮想環境作成

ターミナルを使ったコマンドラインでの操作で説明します(Ubuntu24.04上)

1. workフォルダに移動

2. containerに移動

   ```cmd
   $ cd container
   ```

3. containerの内容　展開した状態では以下の通り

   ```cmd
   $ ls
   Dockerfile  main.py  modules_eis  pip.conf  pyproject.toml  requirements-test.txt  requirements.txt  tox.ini
   ```

4. 仮想環境作成(pyenvの事例)

   ```cmd
   $ pyenv local 3.12
   $ python -m venv venv
   $ . venv/bin/activate
   (venv) $ pip install pip --upgrade
   ```

5. pythonパッケージの導入(pipとrequirements.txtを利用して)

   * この作業でrdetoolkitなどが導入されます

   ```cmd
   (venv) $ pip install -r requirements.txt
   ```

6. 構造化処理プログラムの入出力用のフォルダを作成

   ```cmd
   (venv) $ mkdir data
   ```

7. 入力ファイル用フォルダを作成

   ```cmd
   (venv) $ mkdir data/inputdata
   ```

8. 送状用フォルダを作成

   ```cmd
   (venv) $ mkdir data/invoice
   ```

9. 構造化処理用補助ファイル用のフォルダを作成

   ```cmd
   (venv) $ mkdir data/tasksupport
   (venv) $ tree data
   data
   ├── inputdata
   ├── invoice
   └── tasksupport
   ```

10. テンプレートファイルの配置

* tasksupportフォルダに以下のようにファイルをコピーします
* ここではBiologic用テンプレートを選択しています

  ```cmd
  (venv) $ cp -p ../templates/Biologic/tasksupport/* data/tasksupport/
  (venv) $ tree data
  data
  ├── inputdata
  ├── invoice
  └── tasksupport
      ├── invoice.schema.json
      ├── metadata-def.json
      └── rdeconfig.yaml
  ```

11. 入力データの配置

    * 入力データをdata/inputdata以下に配置します
    * 入力データは各自ご用意してください
    * この説明ではsample_03_1.mpt、sample_06_1.mpt、sample_06_2.mptというファイルを使っています

```cmd
(venv) $ cp ../inputdata/sample_03_1.mpt data/inputdata/
(venv) $ cp ../inputdata/sample_06_1.mpt data/inputdata/
(venv) $ cp ../inputdata/sample_06_2.mpt data/inputdata/
(venv) $ cp ../inputdata/conductivity_total.csv data/inputdata/
```

12. 送状ファイルの配置

    * 送状ファイル(invoice.json)をdata/invoice以下に配置します
    * テスト用のサンプルを利用してください

    ```cmd
    (venv) $ cp ../tryout/invoice_sample.json data/invoice/invoice.json
    ```

13. ファイル配置の確認

    * 以下のようにファイルが配置されていれば準備完了です

    ```cmd
    (venv) $ tree data
    data
    ├── inputdata
    │   ├── conductivity_total.csv
    │   ├── sample_03_1.mpt
    │   ├── sample_06_1.mpt
    │   └── sample_06_2.mpt
    ├── invoice
    │   └── invoice.json
    └── tasksupport
        ├── invoice.schema.json
        ├── metadata-def.json
        └── rdeconfig.yaml
    ```

14. それでは動かしてみましょう

    * エラーメッセージなど返ってこなければ成功です

    ```cmd
    $ python main.py
    ```

15. 確認

    * 正常終了すると以下のようにファイルが出力されます

    ```cmd
    (venv) $ tree data
    data
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
