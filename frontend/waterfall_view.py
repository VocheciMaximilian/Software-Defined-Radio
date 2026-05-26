import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget


class WaterfallView(QWidget):
    def __init__(self, max_frames=220, parent=None):
        super().__init__(parent)
        self.max_frames = max(1, int(max_frames))
        self.frames = []
        self._level_floor = None
        self._level_ceiling = None
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
        if spectrum_frame.power_db.size == 0:
            return

        power_db = np.asarray(spectrum_frame.power_db, dtype=np.float32)
        self._update_levels(power_db)

        normalized = np.clip(
            (power_db - self._level_floor) / (self._level_ceiling - self._level_floor),
            0.0,
            1.0,
        )

        self.frames.append(normalized)
        self.frames = self.frames[-self.max_frames :]
        matrix = np.vstack(self.frames)
        self.image.setImage(matrix, autoLevels=False)

    def _update_levels(self, power_db):
        floor = float(np.percentile(power_db, 5))
        ceiling = float(np.percentile(power_db, 99))

        if ceiling <= floor:
            ceiling = floor + 1.0

        if self._level_floor is None or self._level_ceiling is None:
            self._level_floor = floor
            self._level_ceiling = ceiling
            return

        smoothing = 0.08
        self._level_floor += smoothing * (floor - self._level_floor)
        self._level_ceiling += smoothing * (ceiling - self._level_ceiling)
