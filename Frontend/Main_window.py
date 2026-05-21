class MainWindow:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    def show(self):
        raise NotImplementedError("The PySide6 main window will be implemented here.")
