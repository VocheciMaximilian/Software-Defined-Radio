from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QDialog, QScrollArea, QVBoxLayout


class ReceiverControlsDialog(QDialog):
    visibility_changed = Signal(bool)

    def __init__(self, controls, parent=None):
        super().__init__(parent)
        self.setObjectName("receiverControlsDialog")
        self.setWindowTitle("Receiver controls")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setMinimumWidth(390)
        self.resize(430, 720)

        scroll = QScrollArea()
        scroll.setObjectName("controlsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(controls)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self.visibility_changed.emit(True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibility_changed.emit(False)
