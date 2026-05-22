import ctypes
import os
import platform
from pathlib import Path
from ctypes.util import find_library

import numpy as np

from backend.receiver.base import Receiver
from backend.signal.models import IQBlock


class RtlSdrLibrary:
    def __init__(self):
        self._lib = self._load_library()
        self._configure_functions()

    def _candidate_paths(self):
        project_root = Path(__file__).resolve().parents[2]
        candidate_dirs = [
            project_root,
            project_root / "dll",
            project_root / "bin",
            project_root / "Drivers",
            Path.cwd(),
            Path.home() / "Desktop" / "RTL-SDR" / "sdrsharp-x86",
            Path.home() / "Desktop" / "RTL-SDR" / "sdrsharp-x64",
        ]

        for path_value in os.environ.get("PATH", "").split(os.pathsep):
            if path_value:
                candidate_dirs.append(Path(path_value))

        candidate_dirs.extend(
            [
                Path("C:/Program Files/SDRSharp"),
                Path("C:/Program Files (x86)/SDRSharp"),
                Path("C:/SDRSharp"),
                Path("C:/sdrsharp"),
                Path("C:/SDR"),
            ]
        )

        attempted_paths = []

        for directory in candidate_dirs:
            dll_path = directory / "rtlsdr.dll"
            attempted_paths.append(str(dll_path))

            if dll_path.exists():
                yield dll_path

        found = find_library("rtlsdr")

        if found:
            attempted_paths.append(found)
            yield found

        attempted_paths.append("rtlsdr")
        yield "rtlsdr"

    def _load_library(self):
        attempted = []
        errors = []

        for candidate in self._candidate_paths():
            attempted.append(str(candidate))

            try:
                candidate_path = Path(candidate)

                if candidate_path.exists() and hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(str(candidate_path.parent))

                return ctypes.CDLL(str(candidate))
            except OSError as exc:
                errors.append(f"{candidate}: {exc}")

        architecture = platform.architecture()[0]
        attempted_text = "\n".join(f"- {path}" for path in attempted)
        errors_text = "\n".join(f"- {error}" for error in errors)
        raise OSError(
            "rtlsdr.dll could not be loaded. The DLL must match the Python "
            f"architecture ({architecture}). If your SDRSharp folder is x86 and "
            "Python is 64-bit, install/copy the x64 RTL-SDR DLLs or run a 32-bit "
            "Python environment.\n"
            f"Attempted paths:\n{attempted_text}\n\nErrors:\n{errors_text}"
        )

    def _configure_functions(self):
        dev_pp = ctypes.POINTER(ctypes.c_void_p)
        uint_p = ctypes.POINTER(ctypes.c_uint8)
        int_p = ctypes.POINTER(ctypes.c_int)

        self._lib.rtlsdr_get_device_count.argtypes = []
        self._lib.rtlsdr_get_device_count.restype = ctypes.c_uint32

        self._lib.rtlsdr_open.argtypes = [dev_pp, ctypes.c_uint32]
        self._lib.rtlsdr_open.restype = ctypes.c_int

        self._lib.rtlsdr_close.argtypes = [ctypes.c_void_p]
        self._lib.rtlsdr_close.restype = ctypes.c_int

        self._lib.rtlsdr_set_center_freq.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self._lib.rtlsdr_set_center_freq.restype = ctypes.c_int

        self._lib.rtlsdr_set_sample_rate.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self._lib.rtlsdr_set_sample_rate.restype = ctypes.c_int

        self._lib.rtlsdr_set_tuner_gain_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.rtlsdr_set_tuner_gain_mode.restype = ctypes.c_int

        self._lib.rtlsdr_set_tuner_gain.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self._lib.rtlsdr_set_tuner_gain.restype = ctypes.c_int

        self._lib.rtlsdr_reset_buffer.argtypes = [ctypes.c_void_p]
        self._lib.rtlsdr_reset_buffer.restype = ctypes.c_int

        self._lib.rtlsdr_read_sync.argtypes = [
            ctypes.c_void_p,
            uint_p,
            ctypes.c_int,
            int_p,
        ]
        self._lib.rtlsdr_read_sync.restype = ctypes.c_int

    def _check(self, result, operation):
        if result < 0:
            raise RuntimeError(f"{operation} failed with librtlsdr error code {result}.")

    def device_count(self):
        return int(self._lib.rtlsdr_get_device_count())

    def open(self, index=0):
        device = ctypes.c_void_p()
        self._check(self._lib.rtlsdr_open(ctypes.byref(device), index), "rtlsdr_open")
        return device

    def close(self, device):
        self._lib.rtlsdr_close(device)

    def configure(self, device, config):
        self._check(
            self._lib.rtlsdr_set_sample_rate(device, int(config.sample_rate)),
            "rtlsdr_set_sample_rate",
        )
        self._check(
            self._lib.rtlsdr_set_center_freq(device, int(config.center_frequency)),
            "rtlsdr_set_center_freq",
        )

        if config.gain == "auto":
            self._check(
                self._lib.rtlsdr_set_tuner_gain_mode(device, 0),
                "rtlsdr_set_tuner_gain_mode(auto)",
            )
        else:
            self._check(
                self._lib.rtlsdr_set_tuner_gain_mode(device, 1),
                "rtlsdr_set_tuner_gain_mode(manual)",
            )
            self._check(
                self._lib.rtlsdr_set_tuner_gain(device, int(float(config.gain) * 10)),
                "rtlsdr_set_tuner_gain",
            )

        self._check(self._lib.rtlsdr_reset_buffer(device), "rtlsdr_reset_buffer")

    def read_samples(self, device, sample_count):
        byte_count = int(sample_count) * 2
        buffer = (ctypes.c_uint8 * byte_count)()
        bytes_read = ctypes.c_int()

        self._check(
            self._lib.rtlsdr_read_sync(
                device,
                buffer,
                byte_count,
                ctypes.byref(bytes_read),
            ),
            "rtlsdr_read_sync",
        )

        if bytes_read.value != byte_count:
            raise RuntimeError(
                f"rtlsdr_read_sync returned {bytes_read.value} bytes, expected {byte_count}."
            )

        raw = np.frombuffer(buffer, dtype=np.uint8).astype(np.float32)
        iq = (raw[0::2] - 127.5) / 127.5 + 1j * ((raw[1::2] - 127.5) / 127.5)
        return iq.astype(np.complex128)


class RtlSdrReceiver(Receiver):
    def __init__(self, config=None):
        super().__init__(config)
        self._library = None
        self._device = None

    def open(self):
        try:
            self._library = RtlSdrLibrary()
        except OSError as exc:
            raise RuntimeError("rtlsdr.dll could not be loaded.") from exc

        if self._library.device_count() <= 0:
            raise RuntimeError("No RTL-SDR device found.")

        try:
            self._device = self._library.open(0)
            self._library.configure(self._device, self.config)
        except Exception:
            self.close()
            raise

        return self

    def close(self):
        if self._device is not None and self._library is not None:
            self._library.close(self._device)
            self._device = None

    def read_block(self):
        if self._device is None or self._library is None:
            raise RuntimeError("Receiver is not open.")

        samples = self._library.read_samples(self._device, self.config.block_size)
        return IQBlock.create(
            samples,
            self.config.sample_rate,
            self.config.center_frequency,
        )
