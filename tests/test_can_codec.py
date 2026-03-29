import pytest
from vehicle.can_codec import encode, decode

def test_normal_signal_roundtrip():
    """ENGINE_STATUS_1 — no offset, standard encode/decode."""
    values = {
        'engine_rpm': 3250.0,
        'throttle_pct': 45.5,
        'engine_load_pct': 62.0,
        'ignition_timing': 18.0,
    }
    data = encode(0x0C0, values)
    result = decode(0x0C0, data)
    
    for k, v in values.items():
        assert abs(result[k] - v) < 0.01, f'{k}: {result[k]} != {v}'

def test_offset_signal_roundtrip():
    """ENGINE_STATUS_2 — offset=-40, cold start temperature test."""
    values = {
        "coolant_temp_c":   -25.0,   # cold start
        "oil_temp_c":       -30.0,   # cold start
        "oil_pressure_bar": 3.5,
        "maf_gs":           25.0,
        "map_kpa":          85.0,
    }
    data = encode(0x0C1, values)
    result = decode(0x0C1, data)

    for k, v in values.items():
        assert abs(result[k] - v) < 0.01, f"{k}: expected {v}, got {result[k]}"

def test_negative_physical_value():
    """BMS_STATUS_1 — pack_current_a can be negative (discharge)."""
    values = {
        "pack_voltage_v": 13.8,
        "pack_current_a": -15.5,
        "soc_pct":        87.0,
        "soh_pct":        95.0,
    }
    data = encode(0x310, values)
    result = decode(0x310, data)
 
    for k, v in values.items():
        assert abs(result[k] - v) < 0.01, f"{k}: expected {v}, got {result[k]}"

def test_invalid_can_id():
    """Unknown CAN ID should return empty dict and encode to zero bytes."""
    data = encode(0xFFF, {"some_signal": 1.0})
    assert data == bytes(8)
 
    result = decode(0xFFF, bytes(8))
    assert result == {}

def test_boundary_values():
    """ENGINE_STATUS_1 — min and max boundary values."""
    # Max values
    values_max = {
        "engine_rpm":       8000.0,
        "throttle_pct":     100.0,
        "engine_load_pct":  100.0,
        "ignition_timing":  40.0,
    }
    data = encode(0x0C0, values_max)
    result = decode(0x0C0, data)
    for k, v in values_max.items():
        assert abs(result[k] - v) < 0.1, f"{k}: expected {v}, got {result[k]}"
 
    # Min values
    values_min = {
        "engine_rpm":       0.0,
        "throttle_pct":     0.0,
        "engine_load_pct":  0.0,
        "ignition_timing":  -5.0,
    }
    data = encode(0x0C0, values_min)
    result = decode(0x0C0, data)
    for k, v in values_min.items():
        assert abs(result[k] - v) < 0.1, f"{k}: expected {v}, got {result[k]}"
 