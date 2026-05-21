import numpy as np


def demodulate_fm(iq_samples):
    iq_samples = np.asarray(iq_samples, dtype=np.complex128)

    if iq_samples.size < 2:
        return np.array([], dtype=float)

    return np.angle(iq_samples[1:] * np.conj(iq_samples[:-1]))
