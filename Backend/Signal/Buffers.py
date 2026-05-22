from collections import deque

import numpy as np


class SampleBuffer:
    def __init__(self, max_blocks=32):
        self._blocks = deque(maxlen=max(1, int(max_blocks)))

    def append(self, samples):
        self._blocks.append(np.asarray(samples).copy())

    def clear(self):
        self._blocks.clear()

    def as_array(self):
        if not self._blocks:
            return np.array([])

        return np.concatenate(list(self._blocks))

    def __len__(self):
        return len(self._blocks)
