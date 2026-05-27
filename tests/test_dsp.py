import numpy as np

from backend.dsp.fft import normalize_spectrum, power_spectrum_db
from backend.dsp.resampling import StreamingResampler, resample_to_rate


def test_power_spectrum_db_has_expected_fft_size():
    sample_rate = 1024
    indices = np.arange(4096)
    samples = np.exp(2j * np.pi * 128 * indices / sample_rate)

    spectrum = power_spectrum_db(samples, fft_size=512)
    normalized = normalize_spectrum(spectrum)

    assert spectrum.shape == (512,)
    assert normalized.shape == (512,)
    assert np.all((0.0 <= normalized) & (normalized <= 1.0))


def test_resample_to_rate_changes_sample_count_by_ratio():
    samples = np.arange(1000, dtype=float)

    resampled = resample_to_rate(samples, 1000, 500)

    assert abs(resampled.size - 500) <= 1


def test_streaming_resampler_preserves_passthrough_samples():
    samples = np.linspace(-1.0, 1.0, 64)
    resampler = StreamingResampler(48_000, 48_000)

    assert np.array_equal(resampler.process(samples), samples)
