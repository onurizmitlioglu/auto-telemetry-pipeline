import pytest
from unittest.mock import MagicMock, patch
from pipeline.processor import Pipeline


@pytest.fixture
def pipeline():
    with patch("pipeline.processor.KafkaConsumer"), \
         patch("pipeline.processor.psycopg2.connect"):
        p = Pipeline()
        p._db = MagicMock()
        p._db.cursor.return_value = MagicMock()
        return p


def test_p0217_triggered(pipeline):
    """P0217 — Trigger when coolant > 108."""
    state = {"coolant_temp_c": 115.0, "lambda": 1.0, "engine_rpm": 1000.0, "engine_load_pct": 30.0}
    pipeline._check_anomalies("VHC-001", state)
    assert "P0217" in pipeline._active_anomalies["VHC-001"]


def test_p0171_triggered(pipeline):
    """P0171 — Trigger when lambda > 1.15."""
    state = {"coolant_temp_c": 80.0, "lambda": 1.20, "engine_rpm": 1000.0, "engine_load_pct": 30.0}
    pipeline._check_anomalies("VHC-001", state)
    assert "P0171" in pipeline._active_anomalies["VHC-001"]


def test_p0300_triggered(pipeline):
    """P0300 — Trigger when both conditions met."""
    state = {"coolant_temp_c": 80.0, "lambda": 1.0, "engine_rpm": 500.0, "engine_load_pct": 70.0}
    pipeline._check_anomalies("VHC-001", state)
    assert "P0300" in pipeline._active_anomalies["VHC-001"]


def test_p0300_not_triggered_low_rpm_only(pipeline):
    """P0300 — Dont trigger when only low rpm, high load should also exist"""
    state = {"coolant_temp_c": 80.0, "lambda": 1.0, "engine_rpm": 500.0, "engine_load_pct": 30.0}
    pipeline._check_anomalies("VHC-001", state)
    assert "P0300" not in pipeline._active_anomalies.get("VHC-001", set())


def test_p0300_not_triggered_high_load_only(pipeline):
    """P0300 — Dont trigger when only high load,low rpm should also exist."""
    state = {"coolant_temp_c": 80.0, "lambda": 1.0, "engine_rpm": 2000.0, "engine_load_pct": 70.0}
    pipeline._check_anomalies("VHC-001", state)
    assert "P0300" not in pipeline._active_anomalies.get("VHC-001", set())


def test_anomaly_not_duplicated(pipeline):
    """Dont write same anomalie twice"""
    state = {"coolant_temp_c": 115.0, "lambda": 1.0, "engine_rpm": 1000.0, "engine_load_pct": 30.0}
    pipeline._check_anomalies("VHC-001", state)
    pipeline._check_anomalies("VHC-001", state)
    assert pipeline._db.cursor().execute.call_count == 1


def test_anomaly_cleared(pipeline):
    """Remove from active anomalies after condition ends"""
    state = {"coolant_temp_c": 115.0, "lambda": 1.0, "engine_rpm": 1000.0, "engine_load_pct": 30.0}
    pipeline._check_anomalies("VHC-001", state)
    assert "P0217" in pipeline._active_anomalies["VHC-001"]

    state["coolant_temp_c"] = 90.0
    pipeline._check_anomalies("VHC-001", state)
    assert "P0217" not in pipeline._active_anomalies["VHC-001"]


def test_missing_signal(pipeline):
    """Dont trigger if signal is missing"""
    state = {"lambda": 1.0, "engine_rpm": 1000.0, "engine_load_pct": 30.0}
    pipeline._check_anomalies("VHC-001", state)
    assert "P0217" not in pipeline._active_anomalies.get("VHC-001", set())