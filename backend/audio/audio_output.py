from collections import deque
from threading import Lock

import numpy as np

DECLICK_SAMPLES = 64
DEFAULT_PREBUFFER_SECONDS = 0.5
DEFAULT_REBUFFER_SECONDS = 0.05
DEFAULT_TARGET_BUFFER_SECONDS = 0.4
DEFAULT_MAX_CLOCK_CORRECTION = 0.0


class AudioOutput:
    def __init__(
        self,
        sample_rate=48_000,
        buffer_seconds=1.0,
        prebuffer_seconds=DEFAULT_PREBUFFER_SECONDS,
        rebuffer_seconds=DEFAULT_REBUFFER_SECONDS,
        target_buffer_seconds=DEFAULT_TARGET_BUFFER_SECONDS,
        max_clock_correction=DEFAULT_MAX_CLOCK_CORRECTION,
        output_device=None,
        stream_latency="high",
    ):
        self.sample_rate = int(sample_rate)
        self.buffer_seconds = float(buffer_seconds)
        self.prebuffer_seconds = float(prebuffer_seconds)
        self.rebuffer_seconds = float(rebuffer_seconds)
        self.target_buffer_seconds = float(target_buffer_seconds)
        self.max_clock_correction = float(max_clock_correction)
        self.output_device = output_device
        self.stream_latency = stream_latency
        self._max_buffer_samples = max(1, int(self.sample_rate * self.buffer_seconds))
        self._prebuffer_samples = max(0, int(self.sample_rate * self.prebuffer_seconds))
        self._rebuffer_samples = max(0, int(self.sample_rate * self.rebuffer_seconds))
        self._target_buffer_samples = max(
            0,
            int(self.sample_rate * self.target_buffer_seconds),
        )
        self._queued_samples = 0
        self._queue = deque()
        self._lock = Lock()
        self._sounddevice = None
        self._stream = None
        self._is_prebuffering = True
        self._prebuffer_target_samples = self._prebuffer_samples
        self._last_enqueued_sample = 0.0
        self._last_output_sample = 0.0
        self.underrun_count = 0
        self.overrun_count = 0
        self.stream_status_count = 0
        self.callback_frames = 0
        self.max_callback_frames = 0

    @property
    def queued_seconds(self):
        with self._lock:
            return self._queued_samples / self.sample_rate

    def telemetry(self):
        with self._lock:
            return {
                "queued_seconds": self._queued_samples / self.sample_rate,
                "underrun_count": self.underrun_count,
                "overrun_count": self.overrun_count,
                "stream_status_count": self.stream_status_count,
                "is_prebuffering": self._is_prebuffering,
                "callback_frames": self.callback_frames,
                "max_callback_frames": self.max_callback_frames,
                "prebuffer_target_seconds": (
                    self._prebuffer_target_samples / self.sample_rate
                ),
            }

    def reset_diagnostics(self):
        with self._lock:
            self.underrun_count = 0
            self.overrun_count = 0
            self.stream_status_count = 0
            self.callback_frames = 0
            self.max_callback_frames = 0

    def open(self):
        if self._stream is not None:
            return self

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RuntimeError("sounddevice is not installed or cannot be imported.") from exc

        self._sounddevice = sd
        self._stream = sd.OutputStream(
            device=self.output_device,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=1024,
            latency=self.stream_latency,
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

    def _audio_callback(self, outdata, frames, time, status):
        if status:
            self.stream_status_count += 1

        output = np.zeros(frames, dtype=np.float32)
        source = None

        with self._lock:
            self.callback_frames = frames
            self.max_callback_frames = max(self.max_callback_frames, frames)

            if self._is_prebuffering:
                self._is_prebuffering = (
                    self._queued_samples
                    < max(self._prebuffer_target_samples, frames)
                )

            if not self._is_prebuffering:
                source_frames = frames + self._clock_correction(frames)

                if self._queued_samples >= source_frames:
                    source = self._dequeue(source_frames)
                else:
                    self.underrun_count += 1
                    self._is_prebuffering = True
                    self._prebuffer_target_samples = max(
                        self._rebuffer_samples,
                        frames * 2,
                    )

        if source is None:
            ramp_samples = min(DECLICK_SAMPLES, frames)

            if ramp_samples > 1:
                output[:ramp_samples] = np.linspace(
                    self._last_output_sample,
                    0.0,
                    ramp_samples,
                    dtype=np.float32,
                )
        elif source.size == frames:
            output[:] = source
        else:
            positions = np.linspace(0.0, source.size - 1, frames)
            output[:] = np.interp(positions, np.arange(source.size), source)

        self._last_output_sample = float(output[-1]) if output.size else 0.0
        outdata[:] = output.reshape(-1, 1)

    def _clock_correction(self, frames):
        max_adjustment = max(0, int(round(frames * self.max_clock_correction)))

        if max_adjustment == 0 or self._target_buffer_samples <= 0:
            return 0

        error = self._queued_samples - self._target_buffer_samples
        deadband = max(1, int(self.sample_rate * 0.02))

        if abs(error) <= deadband:
            return 0

        return max(-max_adjustment, min(max_adjustment, error // deadband))

    def _dequeue(self, sample_count):
        output = np.empty(sample_count, dtype=np.float32)
        written = 0

        while written < sample_count and self._queue:
            chunk = self._queue[0]
            take = min(sample_count - written, chunk.size)
            output[written : written + take] = chunk[:take]
            written += take

            if take == chunk.size:
                self._queue.popleft()
            else:
                self._queue[0] = chunk[take:]

            self._queued_samples -= take

        return output[:written]

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
        self._is_prebuffering = True
        self._prebuffer_target_samples = self._prebuffer_samples
        self._sounddevice = None
