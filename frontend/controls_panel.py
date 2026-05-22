from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ControlsPanel(QWidget):
    settings_changed = Signal(dict)
    start_requested = Signal()
    stop_requested = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._build_ui()
        self._connect_signals()
        self._emit_settings()

    def _build_ui(self):
        self.setObjectName("controlsPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        frequency_group = QGroupBox("Radio")
        frequency_layout = QFormLayout(frequency_group)

        self.frequency_spin = QDoubleSpinBox()
        self.frequency_spin.setRange(100_000, 1_700_000_000)
        self.frequency_spin.setDecimals(0)
        self.frequency_spin.setSingleStep(100_000)
        self.frequency_spin.setSuffix(" Hz")
        self.frequency_spin.setValue(self._config.receiver.center_frequency)

        self.sample_rate_spin = QDoubleSpinBox()
        self.sample_rate_spin.setRange(250_000, 3_200_000)
        self.sample_rate_spin.setDecimals(0)
        self.sample_rate_spin.setSingleStep(100_000)
        self.sample_rate_spin.setSuffix(" S/s")
        self.sample_rate_spin.setValue(self._config.receiver.sample_rate)

        self.gain_spin = QDoubleSpinBox()
        self.gain_spin.setRange(0, 50)
        self.gain_spin.setDecimals(1)
        self.gain_spin.setSingleStep(0.5)
        self.gain_spin.setSuffix(" dB")
        self.gain_spin.setValue(20)

        self.auto_gain_check = QCheckBox("Auto gain")
        self.auto_gain_check.setChecked(self._config.receiver.gain == "auto")
        self.gain_spin.setEnabled(not self.auto_gain_check.isChecked())

        frequency_layout.addRow("Frequency", self.frequency_spin)
        frequency_layout.addRow("Sample rate", self.sample_rate_spin)
        frequency_layout.addRow("Gain", self.gain_spin)
        frequency_layout.addRow("", self.auto_gain_check)

        demod_group = QGroupBox("Demodulation")
        demod_layout = QFormLayout(demod_group)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["fm", "am"])
        self.mode_combo.setCurrentText(self._config.demodulation_mode)

        self.fft_spin = QSpinBox()
        self.fft_spin.setRange(256, 8192)
        self.fft_spin.setSingleStep(256)
        self.fft_spin.setValue(self._config.fft_size)

        self.audio_check = QCheckBox("Enable audio")
        self.audio_check.setChecked(True)

        demod_layout.addRow("Mode", self.mode_combo)
        demod_layout.addRow("FFT size", self.fft_spin)
        demod_layout.addRow("", self.audio_check)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)

        hint = QLabel("Receiver controls")
        hint.setObjectName("panelCaption")

        root.addWidget(hint)
        root.addWidget(frequency_group)
        root.addWidget(demod_group)
        root.addLayout(buttons)
        root.addWidget(separator)
        root.addStretch(1)

    def _connect_signals(self):
        widgets = [
            self.frequency_spin,
            self.sample_rate_spin,
            self.gain_spin,
            self.mode_combo,
            self.fft_spin,
            self.audio_check,
        ]

        for widget in widgets:
            if hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(self._emit_settings)
            elif hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._emit_settings)
            elif hasattr(widget, "toggled"):
                widget.toggled.connect(self._emit_settings)

        self.auto_gain_check.toggled.connect(self._on_auto_gain_toggled)
        self.start_button.clicked.connect(self.start_requested)
        self.stop_button.clicked.connect(self.stop_requested)

    def _on_auto_gain_toggled(self, checked):
        self.gain_spin.setEnabled(not checked)
        self._emit_settings()

    def _emit_settings(self):
        self.settings_changed.emit(self.current_settings())

    def current_settings(self):
        gain = "auto" if self.auto_gain_check.isChecked() else self.gain_spin.value()
        return {
            "center_frequency": self.frequency_spin.value(),
            "sample_rate": self.sample_rate_spin.value(),
            "gain": gain,
            "demodulation_mode": self.mode_combo.currentText(),
            "fft_size": self.fft_spin.value(),
            "audio_enabled": self.audio_check.isChecked(),
        }

    def set_running(self, running):
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.frequency_spin.setEnabled(not running)
        self.sample_rate_spin.setEnabled(not running)
        self.gain_spin.setEnabled(not running and not self.auto_gain_check.isChecked())
        self.auto_gain_check.setEnabled(not running)
        self.fft_spin.setEnabled(not running)
