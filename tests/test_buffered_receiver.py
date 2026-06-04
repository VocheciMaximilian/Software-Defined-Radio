from time import sleep

import numpy as np

from backend.receiver.buffered_receiver import BufferedReceiver
from backend.receiver.config import ReceiverConfig
from backend.signal.models import IQBlock


class FakeReceiver:
    def __init__(self):
        self.config = ReceiverConfig(sample_rate=1_000, block_size=10)
        self.is_open = False
        self.block_index = 0

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def read_block(self):
        if not self.is_open:
            raise RuntimeError("closed")

        block_index = self.block_index
        self.block_index += 1
        return IQBlock.create(
            np.full(self.config.block_size, block_index),
            self.config.sample_rate,
            self.config.center_frequency,
        )

    def set_center_frequency(self, center_frequency):
        self.config.center_frequency = float(center_frequency)


def test_buffered_receiver_reads_blocks_in_order():
    receiver = BufferedReceiver(FakeReceiver(), max_blocks=3)
    receiver.open()

    first = receiver.read_block()
    second = receiver.read_block()
    receiver.close()

    assert first.samples[0] == 0
    assert second.samples[0] == 1


def test_buffered_receiver_limits_queue_and_reports_duration():
    receiver = BufferedReceiver(FakeReceiver(), max_blocks=3)
    receiver.open()
    sleep(0.02)

    assert receiver.queued_blocks == 3
    assert receiver.queued_seconds == 0.03
    receiver.close()


def test_buffered_receiver_clears_old_blocks_after_retune():
    inner = FakeReceiver()
    receiver = BufferedReceiver(inner, max_blocks=3)
    receiver.open()
    sleep(0.02)

    receiver.set_center_frequency(101_700_000)
    block = receiver.read_block()
    receiver.close()

    assert block.center_frequency == 101_700_000
