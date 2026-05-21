from Backend.Demodulare.Am import demodulate_am
from Backend.Demodulare.Fm import demodulate_fm
from Backend.Dsp.Fft import normalize_spectrum, power_spectrum_db
from Backend.Pipeline.Events import PipelineFrame
from Backend.Signal.Models import AudioBlock, SpectrumFrame


DEMODULATORS = {
    "am": demodulate_am,
    "fm": demodulate_fm,
}


class SDRPipeline:
    def __init__(
        self,
        receiver,
        demodulation_mode="fm",
        audio_sample_rate=48_000,
        fft_size=1024,
        audio_output=None,
    ):
        if demodulation_mode not in DEMODULATORS:
            raise ValueError(f"Unsupported demodulation mode: {demodulation_mode}")

        self.receiver = receiver
        self.demodulation_mode = demodulation_mode
        self.audio_sample_rate = float(audio_sample_rate)
        self.fft_size = int(fft_size)
        self.audio_output = audio_output

    def process_once(self):
        iq_block = self.receiver.read_block()
        demodulator = DEMODULATORS[self.demodulation_mode]
        audio_samples = demodulator(iq_block.samples)
        audio_block = AudioBlock.create(audio_samples, self.audio_sample_rate)

        power_db = power_spectrum_db(iq_block.samples, self.fft_size)
        spectrum = SpectrumFrame.create(
            power_db,
            normalize_spectrum(power_db),
            iq_block.sample_rate,
            iq_block.center_frequency,
        )

        if self.audio_output is not None:
            self.audio_output.play(audio_block.samples)

        return PipelineFrame(iq=iq_block, audio=audio_block, spectrum=spectrum)

    def run(self, on_frame=None, max_frames=None):
        frames_processed = 0

        while max_frames is None or frames_processed < max_frames:
            frame = self.process_once()
            frames_processed += 1

            if on_frame is not None:
                on_frame(frame)
