import numpy as np


def modulate_am(
    message,
    sample_rate,
    modulation_index=0.5,
    carrier_amplitude=1.0,
    carrier_frequency=2_000_000,
):
    message = np.asarray(message, dtype=float)

    if message.size == 0:
        return np.array([], dtype=float)

    max_value = np.max(np.abs(message))

    if max_value > 0:
        message = message / max_value

    samples = np.arange(len(message))
    carrier = np.cos(2 * np.pi * carrier_frequency * samples / sample_rate)
    return carrier_amplitude * (1 + modulation_index * message) * carrier
