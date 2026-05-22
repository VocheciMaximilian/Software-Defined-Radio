import numpy as np


def power(samples):
    return np.abs(samples) ** 2


def power_spectrum_db(samples, fft_size=1024):
    samples = np.asarray(samples)

    if samples.size == 0:
        return np.array([], dtype=np.float32)

    fft_size = min(max(1, int(fft_size)), samples.size)
    frame_count = samples.size // fft_size
    usable_samples = samples[: frame_count * fft_size]
    frames = usable_samples.reshape(frame_count, fft_size)
    window = np.hanning(fft_size)
    spectra = np.fft.fftshift(np.fft.fft(frames * window, axis=1), axes=1)
    mean_power = np.mean(power(spectra), axis=0)
    return (10 * np.log10(mean_power + 1e-18)).astype(np.float32)


def normalize_spectrum(power_db, floor_percentile=5, ceiling_percentile=98):
    power_db = np.asarray(power_db)

    if power_db.size == 0:
        return np.array([], dtype=np.float32)

    floor = float(np.percentile(power_db, floor_percentile))
    ceiling = float(np.percentile(power_db, ceiling_percentile))

    if ceiling <= floor:
        ceiling = floor + 1.0

    return np.clip((power_db - floor) / (ceiling - floor), 0.0, 1.0)


def spectrogram_matrix(samples, fft_size=1024):
    samples = np.asarray(samples)
    fft_size = int(fft_size)

    if fft_size <= 0:
        raise ValueError("fft_size must be positive.")

    num_rows = len(samples) // fft_size
    result = np.zeros((num_rows, fft_size))

    for i in range(num_rows):
        start = i * fft_size
        stop = start + fft_size
        result[i, :] = power_spectrum_db(samples[start:stop], fft_size)

    return result


def spectrogram(samples, fft_size=1024):
    return spectrogram_matrix(samples, fft_size)
