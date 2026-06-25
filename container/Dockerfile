## Python Version:3.12
FROM python:3.12-slim-trixie

ARG PIP_TRUSTED_HOST

# appディレクトリを作成
WORKDIR /app

# 必要なPythonライブラリのインストール
COPY requirements.txt /app
RUN pip install --upgrade pip && pip install -r requirements.txt

# プログラムや設定ファイルなどをコピーする
COPY main.py /app
COPY modules_eis/ /app/modules_eis/
