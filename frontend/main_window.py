from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from frontend.controls_panel import ControlsPanel
from frontend.spectrum_view import SpectrumView
from frontend.waterfall_view import WaterfallView


class MainWindow(QMainWindow):
    start_requested = Signal(dict)
    stop_requested = Signal()
    settings_changed = Signal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.settings = {}
        self.is_running = False
        self.frames_processed = 0

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        self.setWindowTitle("Software-Defined Radio")
        self.resize(1280, 760)

        self.controls = ControlsPanel(self.config)
        self.controls.settings_changed.connect(self._on_settings_changed)
        self.controls.start_requested.connect(self._emit_start_requested)
        self.controls.stop_requested.connect(self.stop_requested)

        self.spectrum_view = SpectrumView()
        self.spectrum_view.frequency_offset_selected.connect(
            self._on_frequency_offset_selected
        )
        self.spectrum_view.isolation_region_changed.connect(
            self._on_isolation_region_changed
        )
        self.waterfall_view = WaterfallView()

        self.frequency_label = QLabel("100.000.000 Hz")
        self.frequency_label.setObjectName("frequencyDisplay")
        self.state_label = QLabel("Stopped")
        self.state_label.setObjectName("stateBadge")
        self.mode_label = QLabel("FM")
        self.mode_label.setObjectName("modeBadge")
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorMessage")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.error_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 8)
        header_layout.addWidget(self.frequency_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.state_label)
        header_layout.addWidget(self.mode_label)

        display = QWidget()
        display_layout = QVBoxLayout(display)
        display_layout.setContentsMargins(10, 10, 10, 10)
        display_layout.setSpacing(8)
        display_layout.addWidget(header)
        display_layout.addWidget(self.error_label)
        display_layout.addWidget(self.spectrum_view, 3)
        display_layout.addWidget(self.waterfall_view, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.controls)
        splitter.addWidget(display)
        splitter.setSizes([310, 970])
        splitter.setCollapsible(0, False)

        self.setCentralWidget(splitter)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
        self._on_settings_changed(self.controls.current_settings())

    def _apply_style(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0f1318;
                color: #dce3ea;
                font-family: Segoe UI;
                font-size: 10pt;
            }

            #controlsPanel {
                background: #171d24;
                border-right: 1px solid #2b3440;
            }

            QGroupBox {
                border: 1px solid #2b3440;
                border-radius: 6px;
                margin-top: 12px;
                padding: 10px;
                color: #ecf2f8;
                font-weight: 600;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }

            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: #0d1117;
                border: 1px solid #32404f;
                border-radius: 4px;
                padding: 5px;
                color: #f4f8fb;
            }

            QPushButton {
                background: #243142;
                border: 1px solid #3d5065;
                border-radius: 5px;
                padding: 7px 12px;
                color: #f4f8fb;
                font-weight: 600;
            }

            QPushButton:hover {
                background: #2d3e52;
            }

            QPushButton:disabled {
                color: #798592;
                background: #1a2028;
            }

            QCheckBox {
                spacing: 8px;
            }

            #frequencyDisplay {
                color: #f7fbff;
                font-size: 28pt;
                font-weight: 700;
            }

            #modeBadge {
                background: #1f8bb7;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 700;
            }

            #stateBadge {
                background: #3a4250;
                color: #f4f8fb;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 700;
            }

            #errorMessage {
                background: #2a1114;
                border: 1px solid #b83b43;
                border-radius: 5px;
                color: #ffd7dc;
                padding: 8px 10px;
            }

            #panelCaption {
                color: #94a3b3;
                font-size: 9pt;
                font-weight: 600;
                text-transform: uppercase;
            }

            QStatusBar {
                background: #0b0e12;
                color: #aeb8c3;
            }
            """
        )

    def _on_settings_changed(self, settings):
        self.settings = settings
        self.set_center_frequency(settings["center_frequency"])
        self.spectrum_view.set_isolation_visible(settings["isolation_enabled"])
        self.spectrum_view.set_isolation_region(
            settings["isolation_low_offset"],
            settings["isolation_high_offset"],
        )
        self.mode_label.setText(settings["demodulation_mode"].upper())
        self.settings_changed.emit(settings)

    def _emit_start_requested(self):
        self.start_requested.emit(self.controls.current_settings())

    def set_running(self, running):
        self.is_running = running
        self.controls.set_running(running)

        self.frames_processed = 0
        self.state_label.setText("Running" if running else "Stopped")
        self.state_label.setStyleSheet(
            "background: #1c8f62;" if running else "background: #3a4250;"
        )
        if running:
            self.error_label.clear()
            self.error_label.setVisible(False)
        self.status.showMessage("Running RTL-SDR" if running else "Stopped")

    def update_frame(self, frame):
        self.frames_processed += 1
        self.spectrum_view.update_frame(frame.spectrum)
        self.waterfall_view.update_frame(frame.spectrum)
        self.status.showMessage(f"Running RTL-SDR | Frames: {self.frames_processed}")

    def set_center_frequency(self, center_frequency):
        self.frequency_label.setText(f"{center_frequency:,.0f} Hz".replace(",", "."))
        self.controls.set_center_frequency(center_frequency)

    def _on_frequency_offset_selected(self, offset_hz):
        if self.controls.sweep_check.isChecked():
            self.controls.sweep_check.setChecked(False)

        frequency = self.controls.current_settings()["center_frequency"] + offset_hz
        frequency = max(
            self.controls.frequency_spin.minimum(),
            min(self.controls.frequency_spin.maximum(), frequency),
        )
        self.controls.frequency_spin.setValue(frequency)

    def _on_isolation_region_changed(self, low_offset, high_offset):
        self.controls.set_isolation_region(low_offset, high_offset)
        bandwidth = abs(high_offset - low_offset)
        self.status.showMessage(
            f"Isolated region: {low_offset:,.0f} Hz to {high_offset:,.0f} Hz "
            f"({bandwidth:,.0f} Hz wide)".replace(",", ".")
        )

    def show_error(self, message):
        self.state_label.setText("Error")
        self.state_label.setStyleSheet("background: #a83232;")
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        self.status.showMessage(message)

    def closeEvent(self, event):
        self.stop_requested.emit()
        event.accept()
