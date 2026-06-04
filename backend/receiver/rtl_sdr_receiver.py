import os
from pathlib import Path

import numpy as np

from backend.receiver.base import Receiver
from backend.signal.models import IQBlock


def _add_project_dll_directory():
    if not hasattr(os, "add_dll_directory"):
        return

    project_root = Path(__file__).resolve().parents[2]
    dll_dir = project_root / "dll"

    if dll_dir.exists():
        os.add_dll_directory(str(dll_dir))


class RtlSdrReceiver(Receiver):
    def __init__(self, config=None):
        super().__init__(config)
        self._sdr = None

    def open(self):
        _add_project_dll_directory()

        try:
            from rtlsdr import RtlSdr
        except AttributeError as exc:
            raise RuntimeError(
                "pyrtlsdr loaded an incompatible rtlsdr.dll. Install matching "
                "64-bit librtlsdr binaries, preferably with `pip install "
                "--upgrade \"pyrtlsdr[lib]\"`, or replace the DLL files in the "
                "project dll folder."
            ) from exc
        except ImportError as exc:
            raise RuntimeError(
                "pyrtlsdr could not load librtlsdr. Install pyrtlsdr with its "
                "bundled native library using `pip install \"pyrtlsdr[lib]\"`, "
                "or make sure 64-bit rtlsdr.dll and its dependencies are on PATH."
            ) from exc

        try:
            self._sdr = RtlSdr()
            self._configure_device()
        except Exception:
            self.close()
            raise

        return self

    def close(self):
        if self._sdr is not None:
            self._sdr.close()
            self._sdr = None

    def read_block(self):
        if self._sdr is None:
            raise RuntimeError("Receiver is not open.")

        samples = self._sdr.read_samples(int(self.config.block_size))
        samples = np.asarray(samples, dtype=np.complex128)
        return IQBlock.create(
            samples,
            self.config.sample_rate,
            self.config.center_frequency,
        )

    def set_center_frequency(self, center_frequency):
        if self._sdr is None:
            raise RuntimeError("Receiver is not open.")

        self._sdr.center_freq = int(center_frequency)
        self._sdr.read_samples(1024)
        self.config.center_frequency = float(center_frequency)

    def _configure_device(self):
        self._sdr.sample_rate = int(self.config.sample_rate)
        self._sdr.center_freq = int(self.config.center_frequency)
        ppm_correction = int(round(self.config.ppm_correction))

        if ppm_correction != 0:
            self._sdr.freq_correction = ppm_correction

        self._sdr.gain = self.config.gain
        self._sdr.read_samples(1024)
