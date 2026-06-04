from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
)


class AudioDiagnosticsDialog(QDialog):
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio diagnostics")
        self.setMinimumWidth(390)
        self._build_ui()
        self.update_telemetry(None)

    def _build_ui(self):
        root = QVBoxLayout(self)

        self.state_label = QLabel()
        self.state_label.setObjectName("audioDiagnosticsState")
        root.addWidget(self.state_label)

        self.queue_bar = QProgressBar()
        self.queue_bar.setRange(0, 1000)
        self.queue_bar.setTextVisible(True)
        root.addWidget(self.queue_bar)

        form = QFormLayout()
        self.queue_label = QLabel()
        self.underrun_label = QLabel()
        self.overrun_label = QLabel()
        self.portaudio_label = QLabel()
        self.callback_label = QLabel()
        self.max_callback_label = QLabel()
        self.prebuffer_target_label = QLabel()
        self.last_loop_label = QLabel()
        self.max_loop_label = QLabel()
        self.production_rate_label = QLabel()
        self.iq_queue_label = QLabel()
        form.addRow("Queued audio", self.queue_label)
        form.addRow("Underruns", self.underrun_label)
        form.addRow("Overruns", self.overrun_label)
        form.addRow("PortAudio status", self.portaudio_label)
        form.addRow("Callback frames", self.callback_label)
        form.addRow("Maximum callback", self.max_callback_label)
        form.addRow("Resume threshold", self.prebuffer_target_label)
        form.addRow("Last SDR loop", self.last_loop_label)
        form.addRow("Maximum SDR loop", self.max_loop_label)
        form.addRow("Audio production", self.production_rate_label)
        form.addRow("Queued IQ", self.iq_queue_label)
        root.addLayout(form)

        help_text = QLabel(
            "Underruns indicate that playback consumed audio faster than the "
            "pipeline produced it. Overruns indicate that the queue filled up. "
            "PortAudio status counts backend-level warnings."
        )
        help_text.setWordWrap(True)
        root.addWidget(help_text)

        self.reset_button = QPushButton("Reset diagnostics")
        self.reset_button.clicked.connect(self.reset_requested)
        root.addWidget(self.reset_button)

    def update_telemetry(self, telemetry):
        if telemetry is None or not telemetry.get("enabled", False):
            self.state_label.setText("Audio output is disabled or not started.")
            self.queue_bar.setValue(0)
            self.queue_bar.setFormat("0.000 s")
            self.queue_label.setText("0.000 s")
            self.underrun_label.setText("0")
            self.overrun_label.setText("0")
            self.portaudio_label.setText("0")
            self.callback_label.setText("0")
            self.max_callback_label.setText("0")
            self.prebuffer_target_label.setText("0.000 s")
            self.last_loop_label.setText("0.000 s")
            self.max_loop_label.setText("0.000 s")
            self.production_rate_label.setText("0 S/s")
            self.iq_queue_label.setText("0.000 s")
            return

        queued_seconds = float(telemetry["queued_seconds"])
        state = "Buffering" if telemetry["is_prebuffering"] else "Playing"
        self.state_label.setText(state)
        self.queue_bar.setValue(min(1000, int(round(queued_seconds * 1000))))
        self.queue_bar.setFormat(f"{queued_seconds:.3f} s")
        self.queue_label.setText(f"{queued_seconds:.3f} s")
        self.underrun_label.setText(str(telemetry["underrun_count"]))
        self.overrun_label.setText(str(telemetry["overrun_count"]))
        self.portaudio_label.setText(str(telemetry["stream_status_count"]))
        self.callback_label.setText(str(telemetry["callback_frames"]))
        self.max_callback_label.setText(str(telemetry["max_callback_frames"]))
        self.prebuffer_target_label.setText(
            f"{telemetry['prebuffer_target_seconds']:.3f} s"
        )
        self.last_loop_label.setText(
            f"{telemetry.get('last_loop_seconds', 0.0):.3f} s"
        )
        self.max_loop_label.setText(
            f"{telemetry.get('max_loop_seconds', 0.0):.3f} s"
        )
        self.production_rate_label.setText(
            f"{telemetry.get('audio_production_rate', 0.0):,.0f} S/s"
        )
        self.iq_queue_label.setText(
            f"{telemetry.get('iq_queue_seconds', 0.0):.3f} s"
        )
