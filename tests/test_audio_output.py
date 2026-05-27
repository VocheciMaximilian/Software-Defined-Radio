import numpy as np

from backend.audio.audio_output import DECLICK_SAMPLES, AudioOutput


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
