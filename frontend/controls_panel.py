from PySide6.QtCore import QSignalBlocker, Signal
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

        sweep_group = QGroupBox("Sweep")
        sweep_layout = QFormLayout(sweep_group)

        self.sweep_check = QCheckBox("Enable sweep")

        self.sweep_start_spin = QDoubleSpinBox()
        self.sweep_start_spin.setRange(100_000, 1_700_000_000)
        self.sweep_start_spin.setDecimals(0)
        self.sweep_start_spin.setSingleStep(100_000)
        self.sweep_start_spin.setSuffix(" Hz")
        self.sweep_start_spin.setValue(
            max(100_000, self._config.receiver.center_frequency - 2_000_000)
        )

        self.sweep_stop_spin = QDoubleSpinBox()
        self.sweep_stop_spin.setRange(100_000, 1_700_000_000)
        self.sweep_stop_spin.setDecimals(0)
        self.sweep_stop_spin.setSingleStep(100_000)
        self.sweep_stop_spin.setSuffix(" Hz")
        self.sweep_stop_spin.setValue(self._config.receiver.center_frequency + 2_000_000)

        self.sweep_step_spin = QDoubleSpinBox()
        self.sweep_step_spin.setRange(1_000, 10_000_000)
        self.sweep_step_spin.setDecimals(0)
        self.sweep_step_spin.setSingleStep(10_000)
        self.sweep_step_spin.setSuffix(" Hz")
        self.sweep_step_spin.setValue(100_000)

        sweep_layout.addRow("", self.sweep_check)
        sweep_layout.addRow("Start", self.sweep_start_spin)
        sweep_layout.addRow("Stop", self.sweep_stop_spin)
        sweep_layout.addRow("Step", self.sweep_step_spin)

        isolation_group = QGroupBox("Signal isolation")
        isolation_layout = QFormLayout(isolation_group)

        self.isolation_check = QCheckBox("Show isolation")
        self.isolation_check.setChecked(True)

        self.isolation_low_spin = QDoubleSpinBox()
        self.isolation_low_spin.setRange(-10_000_000, 10_000_000)
        self.isolation_low_spin.setDecimals(0)
        self.isolation_low_spin.setSingleStep(10_000)
        self.isolation_low_spin.setSuffix(" Hz")
        self.isolation_low_spin.setValue(-100_000)

        self.isolation_high_spin = QDoubleSpinBox()
        self.isolation_high_spin.setRange(-10_000_000, 10_000_000)
        self.isolation_high_spin.setDecimals(0)
        self.isolation_high_spin.setSingleStep(10_000)
        self.isolation_high_spin.setSuffix(" Hz")
        self.isolation_high_spin.setValue(100_000)

        isolation_layout.addRow("", self.isolation_check)
        isolation_layout.addRow("Low offset", self.isolation_low_spin)
        isolation_layout.addRow("High offset", self.isolation_high_spin)

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
        root.addWidget(sweep_group)
        root.addWidget(isolation_group)
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
            self.sweep_check,
            self.sweep_start_spin,
            self.sweep_stop_spin,
            self.sweep_step_spin,
            self.isolation_check,
            self.isolation_low_spin,
            self.isolation_high_spin,
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
            "sweep_enabled": self.sweep_check.isChecked(),
            "sweep_start_frequency": self.sweep_start_spin.value(),
            "sweep_stop_frequency": self.sweep_stop_spin.value(),
            "sweep_step_hz": self.sweep_step_spin.value(),
            "isolation_enabled": self.isolation_check.isChecked(),
            "isolation_low_offset": self.isolation_low_spin.value(),
            "isolation_high_offset": self.isolation_high_spin.value(),
        }

    def set_center_frequency(self, center_frequency):
        with QSignalBlocker(self.frequency_spin):
            self.frequency_spin.setValue(float(center_frequency))

    def set_isolation_region(self, low_offset, high_offset):
        with QSignalBlocker(self.isolation_low_spin):
            self.isolation_low_spin.setValue(float(low_offset))

        with QSignalBlocker(self.isolation_high_spin):
            self.isolation_high_spin.setValue(float(high_offset))

        self._emit_settings()

    def set_running(self, running):
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.frequency_spin.setEnabled(True)
        self.sample_rate_spin.setEnabled(not running)
        self.gain_spin.setEnabled(not running and not self.auto_gain_check.isChecked())
        self.auto_gain_check.setEnabled(not running)
        self.fft_spin.setEnabled(True)
        self.sweep_check.setEnabled(True)
        self.sweep_start_spin.setEnabled(True)
        self.sweep_stop_spin.setEnabled(True)
        self.sweep_step_spin.setEnabled(True)
        self.isolation_check.setEnabled(True)
        self.isolation_low_spin.setEnabled(True)
        self.isolation_high_spin.setEnabled(True)
