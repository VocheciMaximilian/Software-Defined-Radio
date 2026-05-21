import numpy as np


class AudioOutput:
    def __init__(self, sample_rate=48_000):
        self.sample_rate = float(sample_rate)
        self._sounddevice = None

    def open(self):
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice is not installed or cannot be imported.") from exc

        self._sounddevice = sd
        return self

    def play(self, samples):
        if self._sounddevice is None:
            self.open()

        audio = np.asarray(samples, dtype=np.float32)

        if audio.size == 0:
            return

        self._sounddevice.play(audio, samplerate=int(self.sample_rate), blocking=False)

    def close(self):
        if self._sounddevice is not None:
            self._sounddevice.stop()
            self._sounddevice = None
