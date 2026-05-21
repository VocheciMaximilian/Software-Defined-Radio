import numpy as np

from Backend.Receiver.Base import Receiver
from Backend.Signal.Models import IQBlock


class RtlSdrReceiver(Receiver):
    def __init__(self, config=None):
        super().__init__(config)
        self._device = None

    def open(self):
        try:
            from rtlsdr import RtlSdr
        except ImportError as exc:
            raise RuntimeError("pyrtlsdr is not installed or cannot be imported.") from exc

        self._device = RtlSdr()
        self._device.sample_rate = self.config.sample_rate
        self._device.center_freq = self.config.center_frequency
        self._device.gain = self.config.gain
        return self

    def close(self):
        if self._device is not None:
            self._device.close()
            self._device = None

    def read_block(self):
        if self._device is None:
            raise RuntimeError("Receiver is not open.")

        samples = self._device.read_samples(self.config.block_size)
        return IQBlock.create(
            np.asarray(samples, dtype=np.complex128),
            self.config.sample_rate,
            self.config.center_frequency,
        )
