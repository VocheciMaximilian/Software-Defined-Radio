from dataclasses import dataclass
from time import time

import numpy as np


@dataclass(frozen=True)
class IQBlock:
    samples: np.ndarray
    sample_rate: float
    center_frequency: float
    timestamp: float

    @classmethod
    def create(cls, samples, sample_rate, center_frequency):
        return cls(
            samples=np.asarray(samples, dtype=np.complex128),
            sample_rate=float(sample_rate),
            center_frequency=float(center_frequency),
            timestamp=time(),
        )


@dataclass(frozen=True)
class AudioBlock:
    samples: np.ndarray
    sample_rate: float
    timestamp: float

    @classmethod
    def create(cls, samples, sample_rate):
        return cls(
            samples=np.asarray(samples, dtype=np.float32),
            sample_rate=float(sample_rate),
            timestamp=time(),
        )


@dataclass(frozen=True)
class SpectrumFrame:
    power_db: np.ndarray
    normalized_power: np.ndarray
    sample_rate: float
    center_frequency: float
    timestamp: float

    @classmethod
    def create(cls, power_db, normalized_power, sample_rate, center_frequency):
        return cls(
            power_db=np.asarray(power_db, dtype=np.float32),
            normalized_power=np.asarray(normalized_power, dtype=np.float32),
            sample_rate=float(sample_rate),
            center_frequency=float(center_frequency),
            timestamp=time(),
        )
