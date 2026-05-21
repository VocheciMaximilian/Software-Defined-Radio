import traceback

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

from Backend.Audio.Audio_output import AudioOutput
from Backend.Pipeline.Pipeline import SDRPipeline
from Backend.Receiver.Config import ReceiverConfig
from Backend.Receiver.Rtl_sdr_receiver import RtlSdrReceiver
from Config.Current import current_config
from Frontend.Main_window import MainWindow


class SDRApplicationController(QObject):
    def __init__(self, window, config):
        super().__init__()
        self.window = window
        self.config = config
        self.receiver = None
        self.audio_output = None
        self.pipeline = None

        self.timer = QTimer(self)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.process_frame)

        self.window.start_requested.connect(self.start)
        self.window.stop_requested.connect(self.stop)
        self.window.settings_changed.connect(self.update_settings)

    def _report_error(self, prefix, exc):
        message = f"{prefix}: {exc}"

        with open("sdr_error.log", "w", encoding="utf-8") as log_file:
            log_file.write(message)
            log_file.write("\n\n")
            log_file.write(traceback.format_exc())

        print(message)
        traceback.print_exc()
        self.window.show_error(message)

    def start(self, settings):
        if self.pipeline is not None:
            return

        try:
            receiver_config = ReceiverConfig(
                center_frequency=settings["center_frequency"],
                sample_rate=settings["sample_rate"],
                gain=settings["gain"],
                block_size=self.config.receiver.block_size,
            )

            self.receiver = RtlSdrReceiver(receiver_config)
            self.receiver.open()

            self.audio_output = (
                AudioOutput(self.config.audio_sample_rate)
                if settings["audio_enabled"]
                else None
            )
            self.pipeline = SDRPipeline(
                receiver=self.receiver,
                demodulation_mode=settings["demodulation_mode"],
                audio_sample_rate=self.config.audio_sample_rate,
                fft_size=settings["fft_size"],
                audio_output=self.audio_output,
            )
        except Exception as exc:
            self.stop()
            self._report_error("Start failed", exc)
            return

        self.window.set_running(True)
        self.timer.start()

    def update_settings(self, settings):
        if self.pipeline is None:
            return

        self.pipeline.demodulation_mode = settings["demodulation_mode"]
        self.pipeline.fft_size = settings["fft_size"]

        if settings["audio_enabled"] and self.audio_output is None:
            try:
                self.audio_output = AudioOutput(self.config.audio_sample_rate)
                self.audio_output.open()
                self.pipeline.audio_output = self.audio_output
                self.window.status.showMessage("Audio enabled")
            except Exception as exc:
                self.audio_output = None
                self.pipeline.audio_output = None
                self._report_error("Audio failed", exc)

        if not settings["audio_enabled"] and self.audio_output is not None:
            self.audio_output.close()
            self.audio_output = None
            self.pipeline.audio_output = None
            self.window.status.showMessage("Audio disabled")

    def stop(self):
        self.timer.stop()

        if self.audio_output is not None:
            self.audio_output.close()
            self.audio_output = None

        if self.receiver is not None:
            self.receiver.close()
            self.receiver = None

        self.pipeline = None
        self.window.set_running(False)

    def process_frame(self):
        if self.pipeline is None:
            return

        try:
            frame = self.pipeline.process_once()
        except Exception as exc:
            self.stop()
            self._report_error("Pipeline error", exc)
            return

        self.window.update_frame(frame)


def main():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(current_config)
    controller = SDRApplicationController(window, current_config)
    app.controller = controller
    window.show()
    QTimer.singleShot(250, lambda: controller.start(window.controls.current_settings()))
    app.exec()


if __name__ == "__main__":
    main()
