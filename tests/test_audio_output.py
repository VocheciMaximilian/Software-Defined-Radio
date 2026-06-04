import wave

import numpy as np

from backend.audio.audio_output import DECLICK_SAMPLES, AudioOutput
from backend.audio.audio_recorder import AudioRecorder


class FakeOutputStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False

    def start(self):
        self.started = True


class FakeSoundDevice:
    def __init__(self):
        self.stream = None

    def query_hostapis(self):
        return (
            {"name": "MME", "default_output_device": 3},
            {"name": "Windows WASAPI", "default_output_device": 8},
        )

    def check_output_settings(self, **kwargs):
        assert kwargs == {
            "device": 8,
            "channels": 1,
            "dtype": "float32",
            "samplerate": 48_000,
        }

    def OutputStream(self, **kwargs):
        self.stream = FakeOutputStream(**kwargs)
        return self.stream


def test_declick_block_start_preserves_block_shape_after_boundary():
    output = AudioOutput()
    output._last_enqueued_sample = 0.25
    audio = np.linspace(-0.25, 0.25, 256, dtype=np.float32)
    original = audio.copy()

    result = output._declick_block_start(audio)

    assert result is audio
    assert result[0] == np.float32(0.25)
    assert np.allclose(result[DECLICK_SAMPLES:], original[DECLICK_SAMPLES:])
    assert output._last_enqueued_sample == float(original[-1])


def test_audio_recorder_writes_mono_wav_file(tmp_path):
    recorder = AudioRecorder(
        sample_rate=48_000,
        output_dir=tmp_path,
        filename="isolated.wav",
    )
    samples = np.linspace(-1.0, 1.0, 128, dtype=np.float32)

    recorder.write(samples)
    recorder.close()

    with wave.open(str(tmp_path / "isolated.wav"), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 48_000
        assert wav_file.getnframes() == samples.size


def test_audio_callback_preserves_sample_order_across_chunks():
    output = AudioOutput(sample_rate=8, prebuffer_seconds=0)
    output._enqueue(np.array([1.0, 2.0, 3.0], dtype=np.float32))
    output._enqueue(np.array([4.0, 5.0], dtype=np.float32))
    outdata = np.empty((5, 1), dtype=np.float32)

    output._audio_callback(outdata, 5, None, None)

    assert np.array_equal(outdata[:, 0], [1.0, 2.0, 3.0, 4.0, 5.0])
    assert output.underrun_count == 0


def test_audio_callback_rebuffers_after_underrun():
    output = AudioOutput(
        sample_rate=8,
        buffer_seconds=2,
        prebuffer_seconds=0.5,
        rebuffer_seconds=0.5,
    )
    output._is_prebuffering = False
    output._enqueue(np.array([1.0, 2.0], dtype=np.float32))
    underrun_data = np.empty((4, 1), dtype=np.float32)

    output._audio_callback(underrun_data, 4, None, None)

    assert output.underrun_count == 1
    assert output._is_prebuffering

    output._enqueue(np.array([3.0], dtype=np.float32))
    waiting_data = np.empty((4, 1), dtype=np.float32)
    output._audio_callback(waiting_data, 4, None, None)

    assert np.array_equal(waiting_data[:, 0], np.zeros(4, dtype=np.float32))
    assert output._queued_samples == 3

    output._enqueue(np.array([4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32))
    resumed_data = np.empty((4, 1), dtype=np.float32)
    output._audio_callback(resumed_data, 4, None, None)

    assert np.array_equal(resumed_data[:, 0], [1.0, 2.0, 3.0, 4.0])
    assert not output._is_prebuffering


def test_audio_callback_compensates_for_small_clock_drift():
    output = AudioOutput(sample_rate=48_000, max_clock_correction=0.002)
    output._enqueue(np.zeros(12_000, dtype=np.float32))
    output._is_prebuffering = False
    outdata = np.empty((1_024, 1), dtype=np.float32)

    for _ in range(3_000):
        output._enqueue(np.zeros(1_023, dtype=np.float32))
        output._audio_callback(outdata, 1_024, None, None)

    assert output.underrun_count == 0
    assert output.overrun_count == 0
    assert output._queued_samples > 0


def test_audio_callback_does_not_resample_by_default_when_queue_is_full():
    output = AudioOutput(sample_rate=48_000, prebuffer_seconds=0)
    samples = np.sin(
        2.0 * np.pi * 1_000 * np.arange(48_000) / 48_000
    ).astype(np.float32)
    output._enqueue(samples)
    output._is_prebuffering = False
    outdata = np.empty((1_024, 1), dtype=np.float32)

    output._audio_callback(outdata, 1_024, None, None)

    assert np.array_equal(outdata[:, 0], samples[:1_024])


def test_audio_output_automatic_mode_uses_system_default_device(monkeypatch):
    output = AudioOutput()
    sounddevice = FakeSoundDevice()
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", sounddevice)

    output.open()

    assert sounddevice.stream.started
    assert sounddevice.stream.kwargs["device"] is None
    assert sounddevice.stream.kwargs["blocksize"] == 1024
    assert sounddevice.stream.kwargs["latency"] == "high"


def test_audio_output_uses_explicit_output_device(monkeypatch):
    output = AudioOutput(output_device=4)
    sounddevice = FakeSoundDevice()
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", sounddevice)

    output.open()

    assert sounddevice.stream.kwargs["device"] == 4


def test_audio_output_telemetry_reports_buffer_state():
    output = AudioOutput(sample_rate=8)
    output._enqueue(np.zeros(4, dtype=np.float32))
    output.underrun_count = 2
    output.overrun_count = 3
    output.stream_status_count = 4

    telemetry = output.telemetry()

    assert telemetry == {
        "queued_seconds": 0.5,
        "underrun_count": 2,
        "overrun_count": 3,
        "stream_status_count": 4,
        "is_prebuffering": True,
        "callback_frames": 0,
        "max_callback_frames": 0,
        "prebuffer_target_seconds": 0.5,
    }


def test_audio_output_can_reset_diagnostics():
    output = AudioOutput()
    output.underrun_count = 2
    output.overrun_count = 3
    output.stream_status_count = 4
    output.callback_frames = 512
    output.max_callback_frames = 1024

    output.reset_diagnostics()

    telemetry = output.telemetry()
    assert telemetry["underrun_count"] == 0
    assert telemetry["overrun_count"] == 0
    assert telemetry["stream_status_count"] == 0
    assert telemetry["callback_frames"] == 0
    assert telemetry["max_callback_frames"] == 0


def test_audio_callback_waits_for_two_callback_blocks_after_underrun():
    output = AudioOutput(
        sample_rate=48_000,
        prebuffer_seconds=0,
        rebuffer_seconds=0.05,
    )
    output._is_prebuffering = False
    outdata = np.empty((4_800, 1), dtype=np.float32)

    output._audio_callback(outdata, 4_800, None, None)
    output._enqueue(np.zeros(4_800, dtype=np.float32))
    output._audio_callback(outdata, 4_800, None, None)

    assert output.underrun_count == 1
    assert output._is_prebuffering
    assert output._queued_samples == 4_800
    assert output._prebuffer_target_samples == 9_600

    output._enqueue(np.zeros(4_800, dtype=np.float32))
    output._audio_callback(outdata, 4_800, None, None)

    assert output.underrun_count == 1
    assert not output._is_prebuffering
