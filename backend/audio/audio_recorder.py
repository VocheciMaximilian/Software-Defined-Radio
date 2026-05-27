from pathlib import Path
from time import strftime
import wave

import numpy as np


class AudioRecorder:
    def __init__(self, sample_rate=48_000, output_dir="recordings", filename=None):
        self.sample_rate = int(sample_rate)
        self.output_dir = Path(output_dir)
        self.filename = filename or self._timestamped_filename()
        self.path = self.output_dir / self.filename
        self._wave_file = None
        self.samples_written = 0

    def open(self):
        if self._wave_file is not None:
            return self

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._wave_file = wave.open(str(self.path), "wb")
        self._wave_file.setnchannels(1)
        self._wave_file.setsampwidth(2)
        self._wave_file.setframerate(self.sample_rate)
        return self

    def write(self, samples):
        audio = np.asarray(samples, dtype=np.float32)

        if audio.size == 0:
            return

        if self._wave_file is None:
            self.open()

        audio = np.nan_to_num(audio, copy=False)
        audio = np.clip(audio.reshape(-1), -1.0, 1.0)
        pcm = (audio * np.iinfo(np.int16).max).astype("<i2")
        self._wave_file.writeframes(pcm.tobytes())
        self.samples_written += pcm.size

    def close(self):
        if self._wave_file is not None:
            self._wave_file.close()
            self._wave_file = None

    @staticmethod
    def _timestamped_filename():
        return f"isolated_audio_{strftime('%Y%m%d_%H%M%S')}.wav"
