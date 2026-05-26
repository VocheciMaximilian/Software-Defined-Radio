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


class StreamingResampler:
    def __init__(self, source_rate, target_rate, overlap_samples=None):
        self.source_rate = int(round(source_rate))
        self.target_rate = int(round(target_rate))

        if self.source_rate <= 0:
            raise ValueError("source_rate must be positive.")

        if self.target_rate <= 0:
            raise ValueError("target_rate must be positive.")

        self._passthrough = self.source_rate == self.target_rate
        gcd = np.gcd(self.source_rate, self.target_rate)
        self._up = self.target_rate // gcd
        self._down = self.source_rate // gcd
        self._pending = np.array([], dtype=float)
        self._input_position = 0
        self._output_position = 0

        if overlap_samples is None:
            overlap_samples = min(
                10 * max(self._up, self._down),
                int(self.source_rate * 0.01),
            )

        self._overlap_samples = max(1, int(overlap_samples))

    @property
    def config(self):
        return (self.source_rate, self.target_rate)

    def process(self, samples):
        samples = np.asarray(samples)

        if samples.size == 0:
            return samples.copy()

        if self._passthrough:
            return samples.copy()

        data = np.concatenate((self._pending, samples))
        keep = min(self._overlap_samples, data.size)
        stable_input_size = data.size - keep
        self._pending = data[stable_input_size:].copy()

        if stable_input_size <= 0:
            return np.array([], dtype=data.dtype)

        resampled = resample_poly(data, self._up, self._down, padtype="line")
        self._input_position += stable_input_size
        target_output_position = (
            self._input_position * self.target_rate
        ) // self.source_rate
        output_size = target_output_position - self._output_position
        self._output_position = target_output_position

        if output_size <= 0:
            return np.array([], dtype=resampled.dtype)

        return resampled[:output_size]
