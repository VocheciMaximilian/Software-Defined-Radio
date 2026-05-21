import numpy as np

from Backend.Dsp.Filters import lowpass_moving_avg, normalize_rms, remove_dc


def demodulate_fm(iq_samples, lowpass_size=5):
    iq_samples = np.asarray(iq_samples, dtype=np.complex128)

    if iq_samples.size < 2:
        return np.array([], dtype=float)

    message = np.angle(iq_samples[1:] * np.conj(iq_samples[:-1]))
    message = lowpass_moving_avg(message, lowpass_size)
    message = remove_dc(message)
    return normalize_rms(message)
