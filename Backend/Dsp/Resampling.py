import numpy as np


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
