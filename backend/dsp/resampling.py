import numpy as np
from scipy.signal import resample_poly


def decimation_factor(fs, band, alpha=2.0):
    if band is None or band <= 0:
        return 1

    factor = fs / (alpha * band)
    return max(1, int(factor))


def decimate(x, fs, factor):
    x = np.asarray(x)
    factor = max(1, int(factor))
    return x[::factor], fs / factor


def decimate_by_band(x, fs, band, alpha=2.0):
    factor = decimation_factor(fs, band, alpha)
    return decimate(x, fs, factor)


def resample_to_rate(samples, source_rate, target_rate):
    samples = np.asarray(samples)

    if samples.size == 0:
        return samples.copy()

    source_rate = int(round(source_rate))
    target_rate = int(round(target_rate))

    if source_rate <= 0:
        raise ValueError("source_rate must be positive.")

    if target_rate <= 0:
        raise ValueError("target_rate must be positive.")

    if source_rate == target_rate:
        return samples.copy()

    gcd = np.gcd(source_rate, target_rate)
    up = target_rate // gcd
    down = source_rate // gcd
    return resample_poly(samples, up, down)
