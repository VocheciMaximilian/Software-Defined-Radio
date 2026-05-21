import numpy as np


def hann_window(size):
    size = max(1, int(size))
    return np.hanning(size)


def apply_hann_window(samples):
    samples = np.asarray(samples)

    if samples.size == 0:
        return samples.copy()

    return samples * hann_window(samples.size)
