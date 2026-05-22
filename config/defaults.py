from backend.receiver.config import ReceiverConfig


DEFAULT_RECEIVER_CONFIG = ReceiverConfig(
    center_frequency=100_000_000,
    sample_rate=2_400_000,
    gain="auto",
    block_size=65_536,
)

DEFAULT_DEMODULATION_MODE = "fm"
DEFAULT_AUDIO_SAMPLE_RATE = 48_000
DEFAULT_FFT_SIZE = 1024
