from dataclasses import dataclass


@dataclass
class ReceiverConfig:
    center_frequency: float = 100_000_000
    sample_rate: float = 1_024_000
    gain: float = 20.0
    block_size: int = 131_072

    def validate(self):
        if self.center_frequency <= 0:
            raise ValueError("center_frequency must be positive.")

        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive.")

        if self.block_size <= 0:
            raise ValueError("block_size must be positive.")
