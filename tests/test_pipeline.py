import numpy as np

from backend.pipeline.pipeline import SDRPipeline
from backend.receiver.config import ReceiverConfig
from backend.receiver.synthetic_receiver import SyntheticReceiver


def test_pipeline_process_once_with_synthetic_receiver_produces_frames():
    receiver = SyntheticReceiver(
        ReceiverConfig(
            center_frequency=100_000_000,
            sample_rate=1_024_000,
            gain=20.0,
            block_size=32_768,
        )
    )
    receiver.open()
    pipeline = SDRPipeline(
        receiver,
        demodulation_mode="fm",
        audio_sample_rate=48_000,
        fft_size=1024,
        audio_output=None,
    )
    pipeline.set_isolation_region(True, -100_000, 100_000)

    frame = pipeline.process_once()

    assert frame.iq.samples.shape == (32_768,)
    assert frame.audio.sample_rate == 48_000
    assert frame.audio.samples.size > 0
    assert frame.audio.samples.dtype == np.float32
    assert np.all(np.isfinite(frame.audio.samples))
    assert frame.spectrum.power_db.shape == (1024,)
    assert frame.spectrum.normalized_power.shape == (1024,)

    receiver.close()


def test_synthetic_receiver_updates_center_frequency():
    receiver = SyntheticReceiver(ReceiverConfig())
    receiver.open()

    receiver.set_center_frequency(101_700_000)
    block = receiver.read_block()

    assert block.center_frequency == 101_700_000
