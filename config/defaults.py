from backend.receiver.config import ReceiverConfig


DEFAULT_RECEIVER_CONFIG = ReceiverConfig(
    center_frequency=100_000_000,
    sample_rate=2_048_000,
    gain=20.0,
    block_size=131_072,
)

DEFAULT_DEMODULATION_MODE = "fm"
DEFAULT_AUDIO_SAMPLE_RATE = 48_000
DEFAULT_FFT_SIZE = 1024
