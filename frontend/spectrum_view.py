import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class SpectrumView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_frame = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("#101419")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setLabel("left", "Power", units="dB")
        self.plot.setLabel("bottom", "Frequency offset", units="Hz")
        self.plot.setYRange(-130, 40)
        self.curve = self.plot.plot(pen=pg.mkPen("#50d2ff", width=1.4))

        layout.addWidget(self.plot)

    def update_frame(self, spectrum_frame):
        self.last_frame = spectrum_frame
        power_db = spectrum_frame.power_db

        if power_db.size == 0:
            self.curve.setData([], [])
            return

        freqs = np.fft.fftshift(
            np.fft.fftfreq(power_db.size, d=1 / spectrum_frame.sample_rate)
        )
        self.curve.setData(freqs, power_db)
