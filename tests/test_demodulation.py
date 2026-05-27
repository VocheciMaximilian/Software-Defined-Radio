import numpy as np

from backend.demodulare.am import demodulate_am
from backend.demodulare.fm import demodulate_fm


def test_am_demodulation_recovers_envelope_variation():
    message = np.sin(np.linspace(0.0, 4.0 * np.pi, 2048))
    carrier = np.exp(1j * np.linspace(0.0, 24.0 * np.pi, message.size))
    samples = (1.0 + 0.5 * message) * carrier

    demodulated = demodulate_am(samples)

    assert demodulated.shape == message.shape
    assert np.corrcoef(message, demodulated)[0, 1] > 0.99
    assert abs(float(np.mean(demodulated))) < 1e-12


def test_fm_demodulation_returns_constant_phase_step_for_tone():
    sample_rate = 48_000
    tone_frequency = 1_200
    indices = np.arange(4096)
    samples = np.exp(2j * np.pi * tone_frequency * indices / sample_rate)

    demodulated = demodulate_fm(samples)

    expected = 2.0 * np.pi * tone_frequency / sample_rate
    assert demodulated.shape == (samples.size - 1,)
    assert np.allclose(demodulated, expected, atol=1e-12)
