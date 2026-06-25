import os
import shutil
from typing import Union, List


def setup_inputdata_folder(
    inputdata_name: Union[str, List[str]],
    format_name: str = "Biologic",
    case_name: str = "case1",
):
    """テスト用でdataフォルダ群の作成とrawファイルの準備

    Args:
        inputdata_name (Union[str, List[str]]): rawファイル名
        format_name (str): 使用するフォーマット名（Biologic, Scribnerなど）
        case_name (str): case名（case1 など）
    """

    # destination: <project_root>/data
    destination_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data"
    )
    if os.path.exists(destination_path):
        shutil.rmtree(destination_path)

    os.makedirs(os.path.join(destination_path, "inputdata"), exist_ok=True)
    os.makedirs(os.path.join(destination_path, "invoice"), exist_ok=True)

    # rawfile root
    raw_root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "inputdata",
        format_name,
        case_name,
    )

    inputdata_original_path = os.path.join(raw_root, "inputdata")
    invoice_original_path = os.path.join(raw_root, "invoice")

    # inputdata コピー
    if isinstance(inputdata_name, list):
        for fname in inputdata_name:
            shutil.copy(
                os.path.join(inputdata_original_path, fname),
                os.path.join(destination_path, "inputdata"),
            )
    else:
        shutil.copy(
            os.path.join(inputdata_original_path, inputdata_name),
            os.path.join(destination_path, "inputdata"),
        )

    # invoice コピー
    shutil.copy(
        os.path.join(invoice_original_path, "invoice.json"),
        os.path.join(destination_path, "invoice"),
    )

    tasksupport_original_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "templates",
        format_name,
        "tasksupport",
    )
    tasksupport_dest_path = os.path.join(destination_path, "tasksupport")
    os.makedirs(tasksupport_dest_path, exist_ok=True)

    for fname in os.listdir(tasksupport_original_path):
        src = os.path.join(tasksupport_original_path, fname)
        dst = os.path.join(tasksupport_dest_path, fname)

        if os.path.isfile(src):
            shutil.copy(src, dst)


class TestOutputCase1:
    """case1
    Bio-Logic測定データ（.mptファイル）と導電率ファイル（CSV）の入力ケース。
    データ登録モード: インボイスモード
        "sample_03_1.mpt",
        "sample_06_1.mpt",
        "sample_06_2.mpt",
        "conductivity_total.csv",

    """

    inputdata: Union[str, List[str]] = [
        "sample_03_1.mpt",
        "sample_06_1.mpt",
        "sample_06_2.mpt",
        "conductivity_total.csv"
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="Biologic", case_name="case1")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_03_1.mpt"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_06_1.mpt"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_06_2.mpt"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "conductivity_total.csv"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "conductivity_arrhenius_fit_log_sigma_t.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma_t.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma_t.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "sample_03_1.mpt_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_03_1.mpt_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_03_1.mpt_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_1.mpt_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_1.mpt_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_1.mpt_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_2.mpt_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_2.mpt_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_2.mpt_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_fit.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "eisdata.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "structured_log.txt"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "conductivity_arrhenius_fit_log_sigma_t.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase2:
    """case2
    ユーザ定義インピーダンスファイル(.txtファイル) と導電率ファイル(CSV)の入力ケース。
    データ登録モード: インボイスモード
        "sample_T30.TXT",
        "sample_T35.TXT",
        "sample_T40.TXT",
        "conductivity_bulk.csv",
        "conductivity_total.csv",

    """

    inputdata: Union[str, List[str]] = [
        "sample_T30.TXT",
        "sample_T35.TXT",
        "sample_T40.TXT",
        "conductivity_bulk.csv",
        "conductivity_total.csv"
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="Custom", case_name="case1")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_T30.TXT"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_T35.TXT"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_T40.TXT"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "conductivity_bulk.csv"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "conductivity_total.csv"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "conductivity_arrhenius_fit_log_sigma_t.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma_t.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_bulk_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_bulk_arrhenius_fit_log_sigma_t.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma_t.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T30.TXT_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T30.TXT_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T30.TXT_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T35.TXT_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T35.TXT_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T35.TXT_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T40.TXT_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T40.TXT_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T40.TXT_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_bulk_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_bulk_fit.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_fit.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "eisdata.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "structured_log.txt"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "conductivity_arrhenius_fit_log_sigma_t.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase3:
    """case3
    Scribner測定データ（.zファイル）の入力ケース。
    データ登録モード: インボイスモード
        "sample_1.z",
        "sample_2.z",
        "sample_3.z",
    """

    inputdata: Union[str, List[str]] = [
        "sample_1.z",
        "sample_2.z",
        "sample_3.z",
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="Scribner", case_name="case1")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_1.z"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_2.z"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_3.z"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "cole_cole.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole_normalized.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "eisdata.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_1.z_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_1.z_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_1.z_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_2.z_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_2.z_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_2.z_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_3.z_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_3.z_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_3.z_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "structured_log.txt"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase4:
    """case4
    Biologic測定データ(.mptファイル)と導電率ファイル（CSV）の入力ケース。
    データ登録モード: スマートテーブルモード
        "inputdata.zip",
        "smarttable_EIS.xlsx",
    """

    inputdata: Union[str, List[str]] = [
        "inputdata.zip",
        "smarttable_EIS.xlsx"
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="Biologic", case_name="case2")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_03_1.mpt"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_06_1.mpt"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_06_2.mpt"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "conductivity_total.csv"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "conductivity_arrhenius_fit_log_sigma_t.png"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma_t.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma_t.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "sample_03_1.mpt_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_03_1.mpt_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_03_1.mpt_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_1.mpt_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_1.mpt_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_1.mpt_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_2.mpt_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_2.mpt_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_06_2.mpt_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_fit.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "eisdata.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "structured_log.txt"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "conductivity_arrhenius_fit_log_sigma_t.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))


class TestOutputCase5:
    """case5
    ユーザ定義インピーダンスファイル(.txtファイル) と導電率ファイル(CSV)の入力ケース。
    データ登録モード: スマートテーブルモード
        "inputdata.zip",
        "smarttable_EIS.xlsx",
    """

    inputdata: Union[str, List[str]] = [
        "inputdata.zip",
        "smarttable_EIS.xlsx"
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="Custom", case_name="case2")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_T30.TXT"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_T35.TXT"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_T40.TXT"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "conductivity_total.csv"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "conductivity_bulk.csv"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_arrhenius_log_sigma_t.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_bulk_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_bulk_arrhenius_fit_log_sigma_t.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "conductivity_total_arrhenius_fit_log_sigma_t.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T30.TXT_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T30.TXT_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T30.TXT_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T35.TXT_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T35.TXT_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T35.TXT_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T40.TXT_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T40.TXT_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_T40.TXT_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_bulk_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_bulk_fit.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "conductivity_total_fit.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "eisdata.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "structured_log.txt"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "conductivity_arrhenius_fit_log_sigma_t.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "conductivity_arrhenius_fit_log_sigma_t.png"))


class TestOutputCase6:
    """case6
    Scribner測定データ（.zファイル）の入力ケース。
    データ登録モード: スマートテーブルモード
        "inputdata.zip",
        "smarttable_EIS.xlsx",
    """

    inputdata: Union[str, List[str]] = [
        "inputdata.zip",
        "smarttable_EIS.xlsx"
    ]

    def test_setup(self):
        setup_inputdata_folder(self.inputdata, format_name="Scribner", case_name="case2")

    def test_raw_data(self, setup_main, data_path):
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_1.z"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_2.z"))
        assert os.path.exists(os.path.join(data_path, "nonshared_raw", "sample_3.z"))

    def test_main_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "main_image", "cole_cole.png"))

    def test_meta(self, data_path):
        assert os.path.exists(os.path.join(data_path, "meta", "metadata.json"))

    def test_other_image(self, data_path):
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_magnitude_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_inverted_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "bode_phase_normalized.png"))
        assert os.path.exists(os.path.join(data_path, "other_image", "cole_cole_normalized.png"))

    def test_structured(self, data_path):
        assert os.path.exists(os.path.join(data_path, "structured", "eisdata.html"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_1.z_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_1.z_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_1.z_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_2.z_calc.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_2.z_data.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "sample_2.z_norm.csv"))
        assert os.path.exists(os.path.join(data_path, "structured", "structured_log.txt"))

    def test_thumbnail(self, data_path):
        assert os.path.exists(os.path.join(data_path, "thumbnail", "cole_cole.png"))
