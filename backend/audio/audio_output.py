from collections import deque
from threading import Lock
from time import sleep

import numpy as np

DECLICK_SAMPLES = 64
DEFAULT_PREBUFFER_SECONDS = 0.25
DEFAULT_TARGET_BUFFER_SECONDS = 0.5


class AudioOutput:
    def __init__(
        self,
        sample_rate=48_000,
        buffer_seconds=1.0,
        prebuffer_seconds=DEFAULT_PREBUFFER_SECONDS,
        target_buffer_seconds=DEFAULT_TARGET_BUFFER_SECONDS,
    ):
        self.sample_rate = int(sample_rate)
        self.buffer_seconds = float(buffer_seconds)
        self.prebuffer_seconds = float(prebuffer_seconds)
        self.target_buffer_seconds = float(target_buffer_seconds)
        self._max_buffer_samples = max(1, int(self.sample_rate * self.buffer_seconds))
        self._prebuffer_samples = max(0, int(self.sample_rate * self.prebuffer_seconds))
        self._target_buffer_samples = max(
            0,
            int(self.sample_rate * self.target_buffer_seconds),
        )
        self._queued_samples = 0
        self._queue = deque()
        self._lock = Lock()
        self._sounddevice = None
        self._stream = None
        self._last_enqueued_sample = 0.0
        self._last_output_sample = 0.0
        self.underrun_count = 0
        self.overrun_count = 0

    @property
    def queued_seconds(self):
        with self._lock:
            return self._queued_samples / self.sample_rate

    def open(self):
        if self._stream is not None:
            return self

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
        audio = np.asarray(samples, dtype=np.float32)

        if audio.size == 0:
            return

        audio = np.nan_to_num(audio, copy=False)
        audio = np.clip(audio, -1.0, 1.0).reshape(-1).copy()
        #audio = self._declick_block_start(audio)
        self._enqueue(audio)

        if self._stream is None and self._has_enough_prebuffer():
            self.open()

        self._throttle_if_buffer_is_full()

    def _has_enough_prebuffer(self):
        with self._lock:
            return self._queued_samples >= self._prebuffer_samples

    def _declick_block_start(self, audio):
        if audio.size == 0:
            return audio

        fade_samples = min(DECLICK_SAMPLES, audio.size)

        if fade_samples > 1:
            discontinuity = self._last_enqueued_sample - float(audio[0])
            fade = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
            audio[:fade_samples] += discontinuity * fade

        self._last_enqueued_sample = float(audio[-1])
        return audio

    def _enqueue(self, samples):
        with self._lock:
            self._queue.append(samples)
            self._queued_samples += samples.size

            while self._queued_samples > self._max_buffer_samples and self._queue:
                self.overrun_count += 1
                excess = self._queued_samples - self._max_buffer_samples
                oldest = self._queue[0]

                if oldest.size <= excess:
                    self._queue.popleft()
                    self._queued_samples -= oldest.size
                else:
                    self._queue[0] = oldest[excess:]
                    self._queued_samples -= excess
                    break

    def _throttle_if_buffer_is_full(self):
        if self._stream is None or self._target_buffer_samples <= 0:
            return

        with self._lock:
            excess = self._queued_samples - self._target_buffer_samples

        if excess > 0:
            sleep(min(excess / self.sample_rate, 0.05))

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

        if written < frames:
            self.underrun_count += 1
            ramp_samples = min(DECLICK_SAMPLES, frames - written)

            if ramp_samples > 1:
                start_sample = output[written - 1] if written > 0 else self._last_output_sample
                output[written : written + ramp_samples] = np.linspace(
                    start_sample,
                    0.0,
                    ramp_samples,
                    dtype=np.float32,
                )

        self._last_output_sample = float(output[-1]) if output.size else 0.0
        outdata[:] = output.reshape(-1, 1)

    def close(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            self._queue.clear()
            self._queued_samples = 0

        self._last_enqueued_sample = 0.0
        self._last_output_sample = 0.0
        self._sounddevice = None
