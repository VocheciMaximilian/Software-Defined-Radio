from dataclasses import dataclass, field

from Config.Defaults import (
    DEFAULT_AUDIO_SAMPLE_RATE,
    DEFAULT_DEMODULATION_MODE,
    DEFAULT_FFT_SIZE,
)
from Backend.Receiver.Config import ReceiverConfig


@dataclass
class AppConfig:
    receiver: ReceiverConfig = field(default_factory=ReceiverConfig)
    demodulation_mode: str = DEFAULT_DEMODULATION_MODE
    audio_sample_rate: float = DEFAULT_AUDIO_SAMPLE_RATE
    fft_size: int = DEFAULT_FFT_SIZE


current_config = AppConfig()
