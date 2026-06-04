from PySide6.QtCore import QSettings, QSignalBlocker, Signal
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


def available_audio_output_devices():
    try:
        import sounddevice as sd
    except (ImportError, OSError):
        return []

    try:
        devices = sd.query_devices()
    except Exception:
        return []

    return [
        (index, str(device["name"]))
        for index, device in enumerate(devices)
        if int(device["max_output_channels"]) > 0
    ]


class ControlsPanel(QWidget):
    settings_changed = Signal(dict)
    start_requested = Signal()
    stop_requested = Signal()
    audio_diagnostics_requested = Signal()
    SETTINGS_KEYS = (
        "center_frequency",
        "source",
        "sample_rate",
        "gain",
        "ppm_correction",
        "demodulation_mode",
        "fft_size",
        "audio_enabled",
        "audio_output_device",
        "recording_enabled",
        "sweep_enabled",
        "sweep_start_frequency",
        "sweep_stop_frequency",
        "sweep_step_hz",
        "isolation_enabled",
        "isolation_low_offset",
        "isolation_high_offset",
    )

    def __init__(self, config, parent=None, settings_store=None):
        super().__init__(parent)
        self._config = config
        self._settings_store = settings_store or QSettings(
            "SoftwareDefinedRadio",
            "Receiver",
        )
        self._build_ui()
        self._restore_settings()
        self._connect_signals()
        self._emit_settings()

    def _build_ui(self):
        self.setObjectName("controlsPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        frequency_group = QGroupBox("Radio")
        frequency_layout = QFormLayout(frequency_group)
        self._configure_form(frequency_layout)

        self.frequency_spin = QDoubleSpinBox()
        self.frequency_spin.setRange(100_000, 1_700_000_000)
        self.frequency_spin.setDecimals(0)
        self.frequency_spin.setSingleStep(100_000)
        self.frequency_spin.setSuffix(" Hz")
        self.frequency_spin.setValue(self._config.receiver.center_frequency)

        self.source_combo = QComboBox()
        self.source_combo.addItem("RTL-SDR", "rtl_sdr")
        self.source_combo.addItem("Synthetic", "synthetic")

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
        self.gain_spin.setValue(float(self._config.receiver.gain))

        self.ppm_spin = QSpinBox()
        self.ppm_spin.setRange(-200, 200)
        self.ppm_spin.setSuffix(" ppm")
        self.ppm_spin.setValue(int(round(self._config.receiver.ppm_correction)))

        frequency_layout.addRow("Source", self.source_combo)
        frequency_layout.addRow("Frequency", self.frequency_spin)
        frequency_layout.addRow("Sample rate", self.sample_rate_spin)
        frequency_layout.addRow("Gain", self.gain_spin)
        frequency_layout.addRow("PPM correction", self.ppm_spin)

        sweep_group = QGroupBox("Sweep")
        sweep_layout = QFormLayout(sweep_group)
        self._configure_form(sweep_layout)

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
        self._configure_form(isolation_layout)

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
        self._configure_form(demod_layout)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["fm", "am"])
        self.mode_combo.setCurrentText(self._config.demodulation_mode)

        self.fft_spin = QSpinBox()
        self.fft_spin.setRange(256, 8192)
        self.fft_spin.setSingleStep(256)
        self.fft_spin.setValue(self._config.fft_size)

        self.audio_check = QCheckBox("Enable audio")
        self.audio_check.setChecked(True)
        self.audio_output_combo = QComboBox()
        self.audio_output_combo.addItem("Automatic", None)

        for device_index, device_name in available_audio_output_devices():
            self.audio_output_combo.addItem(f"{device_index}: {device_name}", device_index)

        self.recording_check = QCheckBox("Record WAV")
        self.recording_check.setChecked(False)

        demod_layout.addRow("Mode", self.mode_combo)
        demod_layout.addRow("FFT size", self.fft_spin)
        demod_layout.addRow("", self.audio_check)
        demod_layout.addRow("Audio output", self.audio_output_combo)
        demod_layout.addRow("", self.recording_check)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("primaryAction")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.reset_defaults_button = QPushButton("Reset defaults")
        self.reset_defaults_button.setObjectName("secondaryAction")
        self.audio_diagnostics_button = QPushButton("Audio diagnostics")
        self.audio_diagnostics_button.setObjectName("secondaryAction")
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)

        hint = QLabel("Configure the receiver, sweep range and audio output.")
        hint.setObjectName("panelCaption")
        hint.setWordWrap(True)

        root.addWidget(hint)
        root.addLayout(buttons)
        root.addWidget(self.reset_defaults_button)
        root.addWidget(self.audio_diagnostics_button)
        root.addWidget(separator)
        root.addWidget(frequency_group)
        root.addWidget(sweep_group)
        root.addWidget(isolation_group)
        root.addWidget(demod_group)
        root.addStretch(1)

    def _configure_form(self, layout):
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

    def _connect_signals(self):
        widgets = [
            self.frequency_spin,
            self.source_combo,
            self.sample_rate_spin,
            self.gain_spin,
            self.ppm_spin,
            self.mode_combo,
            self.fft_spin,
            self.audio_check,
            self.audio_output_combo,
            self.recording_check,
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

        self.start_button.clicked.connect(self.start_requested)
        self.stop_button.clicked.connect(self.stop_requested)
        self.reset_defaults_button.clicked.connect(self.reset_to_defaults)
        self.audio_diagnostics_button.clicked.connect(self.audio_diagnostics_requested)

    def _emit_settings(self):
        settings = self.current_settings()
        self._save_settings(settings)
        self.settings_changed.emit(settings)

    def current_settings(self):
        return {
            "center_frequency": self.frequency_spin.value(),
            "source": self.source_combo.currentData(),
            "sample_rate": self.sample_rate_spin.value(),
            "gain": self.gain_spin.value(),
            "ppm_correction": self.ppm_spin.value(),
            "demodulation_mode": self.mode_combo.currentText(),
            "fft_size": self.fft_spin.value(),
            "audio_enabled": self.audio_check.isChecked(),
            "audio_output_device": self.audio_output_combo.currentData(),
            "recording_enabled": self.recording_check.isChecked(),
            "sweep_enabled": self.sweep_check.isChecked(),
            "sweep_start_frequency": self.sweep_start_spin.value(),
            "sweep_stop_frequency": self.sweep_stop_spin.value(),
            "sweep_step_hz": self.sweep_step_spin.value(),
            "isolation_enabled": self.isolation_check.isChecked(),
            "isolation_low_offset": self.isolation_low_spin.value(),
            "isolation_high_offset": self.isolation_high_spin.value(),
        }

    def reset_to_defaults(self):
        for key in self.SETTINGS_KEYS:
            self._settings_store.remove(key)

        self._apply_settings(self._default_settings())
        self._emit_settings()

    def _default_settings(self):
        center_frequency = float(self._config.receiver.center_frequency)

        return {
            "center_frequency": center_frequency,
            "source": "rtl_sdr",
            "sample_rate": float(self._config.receiver.sample_rate),
            "gain": float(self._config.receiver.gain),
            "ppm_correction": int(round(self._config.receiver.ppm_correction)),
            "demodulation_mode": self._config.demodulation_mode,
            "fft_size": int(self._config.fft_size),
            "audio_enabled": True,
            "audio_output_device": None,
            "recording_enabled": False,
            "sweep_enabled": False,
            "sweep_start_frequency": max(100_000.0, center_frequency - 2_000_000.0),
            "sweep_stop_frequency": center_frequency + 2_000_000.0,
            "sweep_step_hz": 100_000.0,
            "isolation_enabled": True,
            "isolation_low_offset": -100_000.0,
            "isolation_high_offset": 100_000.0,
        }

    def _apply_settings(self, settings):
        blockers = [
            QSignalBlocker(self.frequency_spin),
            QSignalBlocker(self.source_combo),
            QSignalBlocker(self.sample_rate_spin),
            QSignalBlocker(self.gain_spin),
            QSignalBlocker(self.ppm_spin),
            QSignalBlocker(self.mode_combo),
            QSignalBlocker(self.fft_spin),
            QSignalBlocker(self.audio_check),
            QSignalBlocker(self.audio_output_combo),
            QSignalBlocker(self.recording_check),
            QSignalBlocker(self.sweep_check),
            QSignalBlocker(self.sweep_start_spin),
            QSignalBlocker(self.sweep_stop_spin),
            QSignalBlocker(self.sweep_step_spin),
            QSignalBlocker(self.isolation_check),
            QSignalBlocker(self.isolation_low_spin),
            QSignalBlocker(self.isolation_high_spin),
        ]

        self._set_combo_to_data(self.source_combo, settings["source"])
        self.frequency_spin.setValue(settings["center_frequency"])
        self.sample_rate_spin.setValue(settings["sample_rate"])
        self.gain_spin.setValue(settings["gain"])
        self.ppm_spin.setValue(settings["ppm_correction"])
        self.mode_combo.setCurrentText(settings["demodulation_mode"])
        self.fft_spin.setValue(settings["fft_size"])
        self.audio_check.setChecked(settings["audio_enabled"])
        self._set_combo_to_data(self.audio_output_combo, settings["audio_output_device"])
        self.recording_check.setChecked(settings["recording_enabled"])
        self.sweep_check.setChecked(settings["sweep_enabled"])
        self.sweep_start_spin.setValue(settings["sweep_start_frequency"])
        self.sweep_stop_spin.setValue(settings["sweep_stop_frequency"])
        self.sweep_step_spin.setValue(settings["sweep_step_hz"])
        self.isolation_check.setChecked(settings["isolation_enabled"])
        self.isolation_low_spin.setValue(settings["isolation_low_offset"])
        self.isolation_high_spin.setValue(settings["isolation_high_offset"])

        del blockers

    def _restore_settings(self):
        self._set_combo_data("source", self.source_combo)
        self.frequency_spin.setValue(self._saved_float("center_frequency"))
        self.sample_rate_spin.setValue(self._saved_float("sample_rate"))
        self.gain_spin.setValue(self._saved_float("gain"))
        self.ppm_spin.setValue(self._saved_int("ppm_correction"))
        self.mode_combo.setCurrentText(
            str(self._settings_store.value("demodulation_mode", self.mode_combo.currentText()))
        )
        self.fft_spin.setValue(self._saved_int("fft_size"))
        self.audio_check.setChecked(self._saved_bool("audio_enabled"))
        self._set_combo_data("audio_output_device", self.audio_output_combo, int)
        self.recording_check.setChecked(self._saved_bool("recording_enabled"))
        self.sweep_check.setChecked(self._saved_bool("sweep_enabled"))
        self.sweep_start_spin.setValue(self._saved_float("sweep_start_frequency"))
        self.sweep_stop_spin.setValue(self._saved_float("sweep_stop_frequency"))
        self.sweep_step_spin.setValue(self._saved_float("sweep_step_hz"))
        self.isolation_check.setChecked(self._saved_bool("isolation_enabled"))
        self.isolation_low_spin.setValue(self._saved_float("isolation_low_offset"))
        self.isolation_high_spin.setValue(self._saved_float("isolation_high_offset"))

    def _save_settings(self, settings):
        for key, value in settings.items():
            self._settings_store.setValue(key, value)

    def _saved_float(self, key):
        default = self.current_settings()[key]
        return float(self._settings_store.value(key, default))

    def _saved_int(self, key):
        default = self.current_settings()[key]
        return int(self._settings_store.value(key, default))

    def _saved_bool(self, key):
        default = self.current_settings()[key]
        value = self._settings_store.value(key, default)

        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes")

        return bool(value)

    def _set_combo_data(self, key, combo, cast=None):
        value = self._settings_store.value(key)

        if value is None:
            return

        if cast is not None:
            try:
                value = cast(value)
            except (TypeError, ValueError):
                return

        index = combo.findData(value)

        if index >= 0:
            combo.setCurrentIndex(index)

    def _set_combo_to_data(self, combo, value):
        index = combo.findData(value)

        if index >= 0:
            combo.setCurrentIndex(index)

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
        self.source_combo.setEnabled(not running)
        self.sample_rate_spin.setEnabled(not running)
        self.gain_spin.setEnabled(not running)
        self.ppm_spin.setEnabled(not running)
        self.fft_spin.setEnabled(True)
        self.audio_output_combo.setEnabled(not running)
        self.recording_check.setEnabled(True)
        self.sweep_check.setEnabled(True)
        self.sweep_start_spin.setEnabled(True)
        self.sweep_stop_spin.setEnabled(True)
        self.sweep_step_spin.setEnabled(True)
        self.isolation_check.setEnabled(True)
        self.isolation_low_spin.setEnabled(True)
        self.isolation_high_spin.setEnabled(True)
