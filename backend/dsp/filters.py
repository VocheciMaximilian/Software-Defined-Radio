import numpy as np


def moving_average(samples, kernel_size=5):
    samples = np.asarray(samples)
    kernel_size = max(1, int(kernel_size))

    if samples.size == 0:
        return samples.copy()

    kernel = np.ones(kernel_size, dtype=float) / kernel_size
    return np.convolve(samples, kernel, mode="same")


def lowpass_moving_avg(samples, kernel_size=5):
    return moving_average(samples, kernel_size)


def remove_dc(samples):
    samples = np.asarray(samples)

    if samples.size == 0:
        return samples.copy()

    return samples - np.mean(samples)


def normalize_rms(samples, eps=1e-12):
    samples = np.asarray(samples)

    if samples.size == 0:
        return samples.copy()

    rms = np.sqrt(np.mean(np.abs(samples) ** 2))
    return samples / (rms + eps)
