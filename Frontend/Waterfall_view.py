class WaterfallView:
    def __init__(self, max_frames=200):
        self.max_frames = max(1, int(max_frames))
        self.frames = []

    def update_frame(self, spectrum_frame):
        self.frames.append(spectrum_frame.normalized_power)
        self.frames = self.frames[-self.max_frames :]
