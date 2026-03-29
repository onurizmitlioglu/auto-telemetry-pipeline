from vehicle.can_bus import MESSAGE_CATALOGUE, SignalDef
from typing import Dict

def encode(can_id: int, signal_values: Dict[str, float]) -> bytes:
    """
    Encode physical signal values into an 8-byte CAN frame payload.
    physical = raw * factor + offset  →  raw = (physical - offset) / factor
    """
    signals = MESSAGE_CATALOGUE.get(can_id, [])
    raw_int = 0

    for sig in signals:
        physical = signal_values.get(sig.name)
        if physical is None:
            continue

        raw = int(round((physical - sig.offset) / sig.factor))
        mask = (1 << sig.length) - 1
        raw_int |= (raw & mask) << sig.start_bit

    return raw_int.to_bytes(8, byteorder="little")

def decode(can_id: int, data: bytes) -> Dict[str, float]:
    """
    Decode an 8-byte CAN frame payload into physical signal values.
    physical = raw * factor + offset
    """
    result: Dict[str, float] = {}

    signals = MESSAGE_CATALOGUE.get(can_id, [])
    raw_int = int.from_bytes(data, byteorder="little")
    for sig in signals:
        mask = (1 << sig.length) - 1
        raw = (raw_int >> sig.start_bit) & mask
        result[sig.name] = round((raw * sig.factor) + sig.offset, 4)

    return result