from queue import Empty, Full, Queue
from threading import Event, Lock, Thread


class BufferedReceiver:
    """Reads IQ blocks continuously so short DSP stalls do not interrupt audio."""

    def __init__(self, receiver, max_blocks=8):
        self.receiver = receiver
        self.config = receiver.config
        self.max_blocks = max(1, int(max_blocks))
        self._blocks = Queue(maxsize=self.max_blocks)
        self._stop_requested = Event()
        self._device_lock = Lock()
        self._reader_thread = None
        self._reader_error = None
        self._generation = 0

    @property
    def queued_blocks(self):
        return self._blocks.qsize()

    @property
    def queued_seconds(self):
        return self.queued_blocks * self.config.block_size / self.config.sample_rate

    def open(self):
        self.receiver.open()
        self._stop_requested.clear()
        self._reader_error = None
        self._reader_thread = Thread(
            target=self._read_blocks,
            name="rtl-sdr-reader",
            daemon=True,
        )
        self._reader_thread.start()
        return self

    def close(self):
        self._stop_requested.set()
        self.receiver.close()

        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None

        self._clear_blocks()

    def read_block(self):
        while not self._stop_requested.is_set():
            try:
                generation, block = self._blocks.get(timeout=0.1)

                if generation == self._generation:
                    return block
            except Empty:
                if self._reader_error is not None:
                    raise RuntimeError("Buffered receiver read failed.") from self._reader_error

        if self._reader_error is not None:
            raise RuntimeError("Buffered receiver read failed.") from self._reader_error

        raise RuntimeError("Receiver is closed.")

    def set_center_frequency(self, center_frequency):
        with self._device_lock:
            self._generation += 1
            self.receiver.set_center_frequency(center_frequency)

        self._clear_blocks()

    def _read_blocks(self):
        try:
            while not self._stop_requested.is_set():
                with self._device_lock:
                    block = self.receiver.read_block()
                    generation = self._generation

                while not self._stop_requested.is_set():
                    if generation != self._generation:
                        break

                    try:
                        self._blocks.put((generation, block), timeout=0.1)
                        break
                    except Full:
                        continue
        except Exception as exc:
            if not self._stop_requested.is_set():
                self._reader_error = exc

    def _clear_blocks(self):
        while True:
            try:
                self._blocks.get_nowait()
            except Empty:
                return
