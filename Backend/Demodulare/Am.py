import numpy as np

from Backend.Dsp.Filters import lowpass_moving_avg, normalize_rms, remove_dc


def demodulate_am(iq_samples, lowpass_size=5):
    iq_samples = np.asarray(iq_samples, dtype=np.complex128)

    if iq_samples.size == 0:
        return np.array([], dtype=float)

    message = np.abs(iq_samples)
    message = lowpass_moving_avg(message, lowpass_size)
    message = remove_dc(message)
    return normalize_rms(message)
