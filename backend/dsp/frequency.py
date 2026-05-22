import numpy as np

from backend.dsp.fft import power
from backend.dsp.filters import lowpass_moving_avg


def frequency_axis(sample_count, sample_rate):
    return np.fft.fftshift(np.fft.fftfreq(sample_count, d=1 / sample_rate))


def shift_frequency(samples, frequency_offset, sample_rate):
    samples = np.asarray(samples, dtype=np.complex128)

    if samples.size == 0:
        return samples.copy()

    n = np.arange(samples.size)
    return samples * np.exp(-2j * np.pi * frequency_offset * n / sample_rate)


def estimate_occupied_band(samples, sample_rate, threshold_percentile=75, smooth_size=5):
    samples = np.asarray(samples, dtype=np.complex128)

    if samples.size == 0:
        return None

    spectrum = np.fft.fftshift(np.fft.fft(samples))
    spectrum_power = lowpass_moving_avg(power(spectrum), smooth_size)
    threshold = np.percentile(spectrum_power, threshold_percentile)
    active_indices = np.where(spectrum_power > threshold)[0]

    if active_indices.size == 0:
        return None

    frequencies = frequency_axis(samples.size, sample_rate)
    f_min = frequencies[active_indices[0]]
    f_max = frequencies[active_indices[-1]]

    return {
        "center_frequency_offset": float((f_min + f_max) / 2),
        "bandwidth": float(f_max - f_min),
        "f_min": float(f_min),
        "f_max": float(f_max),
    }
