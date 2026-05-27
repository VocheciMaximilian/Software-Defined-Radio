import numpy as np

from backend.receiver.base import Receiver
from backend.signal.models import IQBlock


class SyntheticReceiver(Receiver):
    """Deterministic IQ source for development and automated tests."""

    def __init__(self, config=None, tone_frequency=12_000.0, audio_frequency=1_000.0):
        super().__init__(config)
        self.tone_frequency = float(tone_frequency)
        self.audio_frequency = float(audio_frequency)
        self._is_open = False
        self._sample_index = 0

    def open(self):
        self._is_open = True
        return self

    def close(self):
        self._is_open = False

    def read_block(self):
        if not self._is_open:
            raise RuntimeError("Receiver is not open.")

        count = int(self.config.block_size)
        indices = self._sample_index + np.arange(count)
        sample_rate = float(self.config.sample_rate)
        time = indices / sample_rate
        message = np.sin(2.0 * np.pi * self.audio_frequency * time)

        phase = (
            2.0 * np.pi * self.tone_frequency * time
            + 1.5 * np.sin(2.0 * np.pi * self.audio_frequency * time)
        )
        carrier = np.exp(1j * phase)
        envelope = 1.0 + 0.35 * message
        samples = envelope * carrier

        self._sample_index += count
        return IQBlock.create(
            samples,
            self.config.sample_rate,
            self.config.center_frequency,
        )

    def set_center_frequency(self, center_frequency):
        if not self._is_open:
            raise RuntimeError("Receiver is not open.")

        self.config.center_frequency = float(center_frequency)
