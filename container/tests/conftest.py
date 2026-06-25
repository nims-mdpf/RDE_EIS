import json
import os
import sys
import importlib

import pytest


@pytest.fixture
def data_path():
    """
    テストで使用する data ディレクトリのパス
    """
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@pytest.fixture
def setup_main():
    """
    main.py を pytest プロセス内で実行するフィクスチャ

    - subprocess は使わない（coverage を有効にするため）
    - import-time 実行を毎回発生させるため reload を使用
    - fixture scope は function（順序依存を防ぐ）
    """

    # 念のため main の import キャッシュを削除
    sys.modules.pop("main", None)

    # main.py を import（= 実行）
    import main  # noqa: F401

    # import-time 実行を強制的にやり直す
    importlib.reload(main)

    # yield しない（終了処理なし）


@pytest.fixture
def setup_metadatadef_json():
    """
    metadata-def.json を読み込むフィクスチャ
    """
    metadata_filename = "metadata-def.json"

    test_specification_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data",
        "tasksupport",
        metadata_filename,
    )

    with open(test_specification_path, mode="r", encoding="utf-8") as f:
        contents = json.load(f)

    yield contents
