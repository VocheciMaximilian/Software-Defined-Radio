import numpy as np


class AudioOutput:
    def __init__(self, sample_rate=48_000):
        self.sample_rate = float(sample_rate)
        self._sounddevice = None
        self._stream = None

    def open(self):
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice is not installed or cannot be imported.") from exc

        self._sounddevice = sd
        self._stream = sd.OutputStream(
            samplerate=int(self.sample_rate),
            channels=1,
            dtype="float32",
            blocksize=0,
        )
        self._stream.start()
        return self

    def play(self, samples):
        if self._stream is None:
            self.open()

        audio = np.asarray(samples, dtype=np.float32)

        if audio.size == 0:
            return

        audio = np.clip(audio, -1.0, 1.0).reshape(-1, 1)
        self._stream.write(audio)

    def close(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._sounddevice = None
