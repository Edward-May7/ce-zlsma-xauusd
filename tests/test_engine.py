import unittest
from pathlib import Path

import pandas as pd

from ce_zlsma_xauusd import baseline_config, engine


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "XAUUSD_M5_202505010100_202604302255.csv"


class EngineDataTests(unittest.TestCase):
    def test_dataset_loads_with_expected_schema(self) -> None:
        df = engine.read_ohlcv_csv(DATASET)

        self.assertEqual(len(df), 70167)
        self.assertTrue(df.index.is_monotonic_increasing)
        self.assertIsInstance(df.index, pd.DatetimeIndex)
        self.assertEqual(str(df.index[0]), "2025-05-01 01:00:00")
        self.assertEqual(str(df.index[-1]), "2026-04-30 22:55:00")
        self.assertTrue({"Open", "High", "Low", "Close", "Volume", "SpreadPoints"}.issubset(df.columns))

    def test_signal_frame_builds_core_indicators(self) -> None:
        raw = engine.read_ohlcv_csv(DATASET).head(300)
        signals = engine.build_signal_frame(raw)

        for column in ["ha_Open", "ha_High", "ha_Low", "ha_Close", "zlsma", "ce_buy", "ce_sell", "atr14"]:
            self.assertIn(column, signals.columns)

        self.assertGreater(signals["zlsma"].notna().sum(), 100)
        self.assertGreater(signals["atr14"].notna().sum(), 250)
        self.assertEqual(engine.PARTIAL_TP_R, 1.5)

    def test_synthetic_data_path_is_available_for_offline_smoke_tests(self) -> None:
        raw = engine.synthetic_ohlcv(n=180, freq="5min", seed=7)
        signals = engine.build_signal_frame(raw)

        self.assertEqual(len(raw), 180)
        self.assertEqual(len(signals), 180)
        self.assertGreater(signals["zlsma"].notna().sum(), 50)

    def test_baseline_config_uses_packaged_m5_dataset(self) -> None:
        cfg = baseline_config(ROOT)

        self.assertEqual(cfg.data.csv_path, DATASET)
        self.assertEqual(cfg.data.csv_cn_offset_hours, 5)
        self.assertEqual(cfg.risk.partial_tp_r, 1.5)


if __name__ == "__main__":
    unittest.main()
