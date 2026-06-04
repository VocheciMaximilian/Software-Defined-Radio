import numpy as np
from scipy.signal import sosfreqz

from backend.demodulare.fm import demodulate_fm
from backend.pipeline.pipeline import FM_AUDIO_LOWPASS, FM_DEMOD_SAMPLE_RATE, SDRPipeline
from backend.receiver.config import ReceiverConfig
from backend.receiver.synthetic_receiver import SyntheticReceiver
from backend.signal.models import IQBlock


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


def test_pipeline_can_skip_spectrum_without_skipping_audio():
    receiver = SyntheticReceiver(ReceiverConfig(block_size=32_768))
    receiver.open()
    pipeline = SDRPipeline(receiver)

    frame = pipeline.process_once(include_spectrum=False)

    assert frame.audio.samples.size > 0
    assert frame.spectrum is None
    receiver.close()


def test_fm_audio_filter_rejects_frequencies_above_mono_band():
    pipeline = SDRPipeline(receiver=None, audio_sample_rate=48_000)
    state = pipeline._create_fm_audio_filter_state(48_000, 0.0)

    frequencies, response = sosfreqz(
        state["lowpass_sos"],
        worN=[1_000, FM_AUDIO_LOWPASS, 19_000],
        fs=48_000,
    )

    assert np.array_equal(frequencies, [1_000, FM_AUDIO_LOWPASS, 19_000])
    assert abs(response[0]) > 0.99
    assert 0.65 < abs(response[1]) < 0.75
    assert abs(response[2]) < 0.2


def test_fm_channel_is_filtered_even_without_visible_isolation():
    pipeline = SDRPipeline(receiver=None)
    sample_rate = 1_024_000
    iq_block = IQBlock.create(np.ones(32_768), sample_rate, 100_000_000)

    filtered, filtered_rate = pipeline._prepare_demodulation_input(iq_block)

    assert filtered_rate == FM_DEMOD_SAMPLE_RATE
    assert 0 < filtered.size < iq_block.samples.size


def test_fm_iq_dc_blocker_reduces_discriminator_distortion():
    sample_rate = 240_000
    time = np.arange(sample_rate) / sample_rate
    message = np.sin(2.0 * np.pi * 1_000 * time)
    phase = np.cumsum(2.0 * np.pi * 75_000 * 0.7 * message / sample_rate)
    iq_samples = np.exp(1j * phase) + 0.6
    pipeline = SDRPipeline(receiver=None)

    raw_audio = demodulate_fm(iq_samples)
    filtered_iq = pipeline._block_fm_iq_dc(iq_samples, sample_rate)
    filtered_audio = demodulate_fm(filtered_iq)
    reference = message[1:]
    warmup = 2_000

    raw_correlation = np.corrcoef(raw_audio[warmup:], reference[warmup:])[0, 1]
    filtered_correlation = np.corrcoef(
        filtered_audio[warmup:],
        reference[warmup:],
    )[0, 1]

    assert raw_correlation < 0.95
    assert filtered_correlation > 0.99
