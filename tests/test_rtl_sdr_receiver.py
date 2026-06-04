import sys
from types import SimpleNamespace

import numpy as np

from backend.receiver.config import ReceiverConfig
from backend.receiver.rtl_sdr_receiver import RtlSdrReceiver


class FakeRtlSdr:
    def __init__(self):
        self.sample_rate = None
        self.center_freq = None
        self.freq_correction = None
        self.gain = None
        self.closed = False

    def read_samples(self, count):
        return np.zeros(count, dtype=np.complex128)

    def close(self):
        self.closed = True


class FakeRtlSdrRejectsZeroPpm(FakeRtlSdr):
    def __init__(self):
        self._freq_correction = None
        super().__init__()

    @property
    def freq_correction(self):
        return self._freq_correction

    @freq_correction.setter
    def freq_correction(self, value):
        if value == 0:
            raise ValueError("invalid param")

        self._freq_correction = value


def test_rtl_sdr_receiver_applies_ppm_correction(monkeypatch):
    monkeypatch.setitem(sys.modules, "rtlsdr", SimpleNamespace(RtlSdr=FakeRtlSdr))
    receiver = RtlSdrReceiver(
        ReceiverConfig(
            center_frequency=100_000_000,
            sample_rate=1_024_000,
            gain=20.0,
            ppm_correction=17,
        )
    )

    receiver.open()

    assert receiver._sdr.freq_correction == 17
    receiver.close()


def test_rtl_sdr_receiver_does_not_apply_zero_ppm_correction(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "rtlsdr",
        SimpleNamespace(RtlSdr=FakeRtlSdrRejectsZeroPpm),
    )
    receiver = RtlSdrReceiver(
        ReceiverConfig(
            center_frequency=100_000_000,
            sample_rate=1_024_000,
            gain=20.0,
            ppm_correction=0,
        )
    )

    receiver.open()

    assert receiver._sdr.freq_correction is None
    receiver.close()
