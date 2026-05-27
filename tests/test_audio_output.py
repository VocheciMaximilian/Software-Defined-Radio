import wave

import numpy as np

from backend.audio.audio_output import DECLICK_SAMPLES, AudioOutput
from backend.audio.audio_recorder import AudioRecorder


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
