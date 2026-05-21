import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class WaterfallView(QWidget):
    def __init__(self, max_frames=220, parent=None):
        super().__init__(parent)
        self.max_frames = max(1, int(max_frames))
        self.frames = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot = pg.PlotWidget()
        self.plot.setBackground("#0b0f14")
        self.plot.hideAxis("left")
        self.plot.hideAxis("bottom")
        self.plot.setMouseEnabled(x=False, y=False)

        self.image = pg.ImageItem()
        self.plot.addItem(self.image)
        color_map = pg.colormap.get("CET-L17")
        self.image.setLookupTable(color_map.getLookupTable(0.0, 1.0, 256))
        self.image.setLevels([0.0, 1.0])

        layout.addWidget(self.plot)

    def update_frame(self, spectrum_frame):
        if spectrum_frame.normalized_power.size == 0:
            return

        self.frames.append(spectrum_frame.normalized_power)
        self.frames = self.frames[-self.max_frames :]
        matrix = np.vstack(self.frames)
        self.image.setImage(matrix, autoLevels=False)
