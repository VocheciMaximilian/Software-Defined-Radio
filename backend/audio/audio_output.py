from collections import deque
from threading import Lock

import numpy as np


class AudioOutput:
    def __init__(self, sample_rate=48_000, buffer_seconds=0.5):
        self.sample_rate = int(sample_rate)
        self.buffer_seconds = float(buffer_seconds)
        self._max_buffer_samples = max(1, int(self.sample_rate * self.buffer_seconds))
        self._queued_samples = 0
        self._queue = deque()
        self._lock = Lock()
        self._sounddevice = None
        self._stream = None

    def open(self):
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice is not installed or cannot be imported.") from exc

        self._sounddevice = sd
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=1024,
            latency="high",
            callback=self._audio_callback,
        )
        self._stream.start()
        return self

    def play(self, samples):
        if self._stream is None:
            self.open()

        audio = np.asarray(samples, dtype=np.float32)

        if audio.size == 0:
            return

        audio = np.clip(audio, -1.0, 1.0).reshape(-1).copy()
        self._enqueue(audio)

    def _enqueue(self, samples):
        with self._lock:
            self._queue.append(samples)
            self._queued_samples += samples.size

            while self._queued_samples > self._max_buffer_samples and self._queue:
                excess = self._queued_samples - self._max_buffer_samples
                oldest = self._queue[0]

                if oldest.size <= excess:
                    self._queue.popleft()
                    self._queued_samples -= oldest.size
                else:
                    self._queue[0] = oldest[excess:]
                    self._queued_samples -= excess
                    break

    def _audio_callback(self, outdata, frames, time, status):
        output = np.zeros(frames, dtype=np.float32)
        written = 0

        with self._lock:
            while written < frames and self._queue:
                chunk = self._queue[0]
                take = min(frames - written, chunk.size)
                output[written : written + take] = chunk[:take]
                written += take

                if take == chunk.size:
                    self._queue.popleft()
                else:
                    self._queue[0] = chunk[take:]

                self._queued_samples -= take

        outdata[:] = output.reshape(-1, 1)

    def close(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            self._queue.clear()
            self._queued_samples = 0

        self._sounddevice = None
