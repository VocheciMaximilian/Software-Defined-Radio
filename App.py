import traceback
from threading import Event, Lock

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QApplication

from backend.audio.audio_output import AudioOutput
from backend.pipeline.pipeline import SDRPipeline
from backend.receiver.config import ReceiverConfig
from backend.receiver.rtl_sdr_receiver import RtlSdrReceiver
from backend.receiver.synthetic_receiver import SyntheticReceiver
from config.current import current_config
from frontend.main_window import MainWindow


class SDRPipelineWorker(QThread):
    frame_ready = Signal(object)
    frequency_changed = Signal(float)
    started_ok = Signal()
    stopped = Signal()
    error = Signal(str, object, str)

    def __init__(self, settings, config, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)
        self._config = config
        self._stop_requested = Event()
        self._settings_lock = Lock()
        self._receiver = None
        self._audio_output = None
        self._pipeline = None
        self._active_frequency = None
        self._sweep_frequency = None
        self._sweep_params = None

    def update_settings(self, settings):
        with self._settings_lock:
            self._settings.update(settings)

    def request_stop(self):
        self._stop_requested.set()

        if self._receiver is not None:
            self._receiver.close()

    def run(self):
        try:
            self._start_pipeline()
            self.started_ok.emit()

            while not self._stop_requested.is_set():
                if self._pipeline is None:
                    break

                self._apply_settings()
                frame = self._pipeline.process_once()
                self.frame_ready.emit(frame)
                self._advance_sweep()
        except Exception as exc:
            if not self._stop_requested.is_set():
                self.error.emit("Pipeline error", exc, traceback.format_exc())
        finally:
            self._cleanup()
            self.stopped.emit()

    def _start_pipeline(self):
        with self._settings_lock:
            settings = dict(self._settings)

        receiver_config = ReceiverConfig(
            center_frequency=settings["center_frequency"],
            sample_rate=settings["sample_rate"],
            gain=settings["gain"],
            block_size=self._config.receiver.block_size,
        )

        self._receiver = self._create_receiver(settings["source"], receiver_config)
        self._receiver.open()
        self._active_frequency = float(settings["center_frequency"])

        self._audio_output = (
            AudioOutput(self._config.audio_sample_rate)
            if settings["audio_enabled"]
            else None
        )
        self._pipeline = SDRPipeline(
            receiver=self._receiver,
            demodulation_mode=settings["demodulation_mode"],
            audio_sample_rate=self._config.audio_sample_rate,
            fft_size=settings["fft_size"],
            audio_output=self._audio_output,
        )
        self._pipeline.set_isolation_region(
            settings["isolation_enabled"],
            settings["isolation_low_offset"],
            settings["isolation_high_offset"],
        )

    def _apply_settings(self):
        with self._settings_lock:
            settings = dict(self._settings)

        self._pipeline.demodulation_mode = settings["demodulation_mode"]
        self._pipeline.fft_size = settings["fft_size"]
        self._pipeline.set_isolation_region(
            settings["isolation_enabled"],
            settings["isolation_low_offset"],
            settings["isolation_high_offset"],
        )
        target_frequency = self._target_frequency(settings)

        if target_frequency != self._active_frequency:
            self._receiver.set_center_frequency(target_frequency)
            self._active_frequency = target_frequency
            self.frequency_changed.emit(target_frequency)

        if not settings["audio_enabled"] or settings["sweep_enabled"]:
            self._close_audio()
            self._pipeline.audio_output = None
        elif self._audio_output is None:
            self._audio_output = AudioOutput(self._config.audio_sample_rate)
            self._pipeline.audio_output = self._audio_output

    def _create_receiver(self, source, receiver_config):
        if source == "synthetic":
            return SyntheticReceiver(receiver_config)

        return RtlSdrReceiver(receiver_config)

    def _target_frequency(self, settings):
        if not settings["sweep_enabled"]:
            self._sweep_frequency = None
            self._sweep_params = None
            return float(settings["center_frequency"])

        start = float(settings["sweep_start_frequency"])
        stop = float(settings["sweep_stop_frequency"])
        step = max(1.0, float(settings["sweep_step_hz"]))

        if stop < start:
            start, stop = stop, start

        params = (start, stop, step)
        if self._sweep_params != params or self._sweep_frequency is None:
            self._sweep_params = params
            self._sweep_frequency = start

        return self._sweep_frequency

    def _advance_sweep(self):
        with self._settings_lock:
            settings = dict(self._settings)

        if not settings["sweep_enabled"] or self._sweep_params is None:
            return

        start, stop, step = self._sweep_params
        next_frequency = self._sweep_frequency + step

        if next_frequency > stop:
            next_frequency = start

        self._sweep_frequency = next_frequency

    def _close_audio(self):
        if self._audio_output is not None:
            self._audio_output.close()
            self._audio_output = None

    def _cleanup(self):
        self._close_audio()

        if self._receiver is not None:
            self._receiver.close()
            self._receiver = None

        self._pipeline = None


class SDRApplicationController(QObject):
    def __init__(self, window, config):
        super().__init__()
        self.window = window
        self.config = config
        self.worker = None

        self.window.start_requested.connect(self.start)
        self.window.stop_requested.connect(self.stop)
        self.window.settings_changed.connect(self.update_settings)

    def _report_error(self, prefix, exc, traceback_text=None):
        message = f"{prefix}: {exc}"

        with open("sdr_error.log", "w", encoding="utf-8") as log_file:
            log_file.write(message)
            log_file.write("\n\n")
            log_file.write(traceback_text or traceback.format_exc())

        print(message)
        if traceback_text is not None:
            print(traceback_text)
        else:
            traceback.print_exc()
        self.window.show_error(message)

    def start(self, settings):
        if self.worker is not None:
            return

        self.worker = SDRPipelineWorker(settings, self.config, self)
        self.worker.started_ok.connect(
            lambda: self.window.status.showMessage("Running RTL-SDR")
        )
        self.worker.frame_ready.connect(self.window.update_frame)
        self.worker.frequency_changed.connect(self.window.set_center_frequency)
        self.worker.error.connect(self._handle_worker_error)
        self.worker.stopped.connect(self._handle_worker_stopped)
        self.window.set_running(True)
        self.worker.start()

    def update_settings(self, settings):
        if self.worker is None:
            return

        self.worker.update_settings(settings)

    def stop(self):
        if self.worker is not None:
            self.worker.request_stop()
            self.worker.wait(1500)

        self.window.set_running(False)

    def _handle_worker_error(self, prefix, exc, traceback_text):
        self.stop()
        self._report_error(prefix, exc, traceback_text)

    def _handle_worker_stopped(self):
        worker = self.sender()

        if worker is not None:
            worker.deleteLater()

        if worker is self.worker:
            self.worker = None
            self.window.set_running(False)


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(current_config)
    controller = SDRApplicationController(window, current_config)
    app.controller = controller
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
