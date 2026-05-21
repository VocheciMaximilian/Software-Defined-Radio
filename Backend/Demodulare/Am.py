import numpy as np

from Backend.Dsp.Filters import remove_dc


def demodulate_am(iq_samples):
    iq_samples = np.asarray(iq_samples, dtype=np.complex128)

    if iq_samples.size == 0:
        return np.array([], dtype=float)

    message = np.abs(iq_samples)
    return remove_dc(message)
