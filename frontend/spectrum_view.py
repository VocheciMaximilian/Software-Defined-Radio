import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget


class SpectrumView(QWidget):
    frequency_offset_selected = Signal(float)
    isolation_region_changed = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_frame = None
        self._updating_region = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("#101419")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setLabel("left", "Power", units="dB")
        self.plot.setLabel("bottom", "Frequency offset", units="MHz")
        self.plot.setYRange(-130, 40)
        self.plot.enableAutoRange(axis="x", enable=False)
        self.isolation_region = pg.LinearRegionItem(
            values=(-0.1, 0.1),
            orientation="vertical",
            brush=pg.mkBrush(160, 170, 180, 45),
            pen=pg.mkPen("#c4ccd6", width=1.4),
            hoverPen=pg.mkPen("#ffffff", width=1.6),
            movable=True,
        )
        self.isolation_region.setZValue(5)
        self.isolation_region.sigRegionChangeFinished.connect(
            self._on_isolation_region_changed
        )
        self.plot.addItem(self.isolation_region)
        self.curve = self.plot.plot(pen=pg.mkPen("#50d2ff", width=1.4))
        self.plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)

        layout.addWidget(self.plot)

    def update_frame(self, spectrum_frame):
        self.last_frame = spectrum_frame
        power_db = spectrum_frame.power_db

        if power_db.size == 0:
            self.curve.setData([], [])
            return

        freqs = np.fft.fftshift(
            np.fft.fftfreq(power_db.size, d=1 / spectrum_frame.sample_rate)
        ) / 1_000_000
        bandwidth_mhz = spectrum_frame.sample_rate / 2_000_000
        self.plot.setXRange(-bandwidth_mhz, bandwidth_mhz, padding=0)
        self.isolation_region.setBounds((-bandwidth_mhz, bandwidth_mhz))
        self.curve.setData(freqs, power_db)

    def set_isolation_region(self, lower_hz, upper_hz):
        lower_mhz = float(lower_hz) / 1_000_000
        upper_mhz = float(upper_hz) / 1_000_000

        if upper_mhz < lower_mhz:
            lower_mhz, upper_mhz = upper_mhz, lower_mhz

        self._updating_region = True
        self.isolation_region.setRegion((lower_mhz, upper_mhz))
        self._updating_region = False

    def set_isolation_visible(self, visible):
        self.isolation_region.setVisible(visible)

    def _on_mouse_clicked(self, event):
        plot_item = self.plot.getPlotItem()

        if not plot_item.sceneBoundingRect().contains(event.scenePos()):
            return

        point = plot_item.vb.mapSceneToView(event.scenePos())
        self.frequency_offset_selected.emit(point.x() * 1_000_000)

    def _on_isolation_region_changed(self):
        if self._updating_region:
            return

        lower_mhz, upper_mhz = self.isolation_region.getRegion()
        self.isolation_region_changed.emit(lower_mhz * 1_000_000, upper_mhz * 1_000_000)
