import numpy as np
from scipy.signal import butter, lfilter, lfilter_zi, sosfilt, sosfilt_zi

from backend.demodulare.am import demodulate_am
from backend.demodulare.fm import demodulate_fm
from backend.dsp.filters import normalize_rms, remove_dc
from backend.dsp.fft import normalize_spectrum, power_spectrum_db
from backend.dsp.frequency import shift_frequency
from backend.dsp.resampling import resample_to_rate
from backend.pipeline.events import PipelineFrame
from backend.signal.models import AudioBlock, SpectrumFrame


DEMODULATORS = {
    "am": demodulate_am,
    "fm": demodulate_fm,
}

FM_DEMOD_SAMPLE_RATE = 240_000
CHANNEL_DOWNSAMPLE_FACTORS = (10, 8, 6, 5, 4, 3, 2, 1)


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
        self._audio_filter_state = None
        self.isolation_enabled = False
        self.isolation_low_offset = -100_000.0
        self.isolation_high_offset = 100_000.0

    def set_isolation_region(self, enabled, low_offset, high_offset):
        self.isolation_enabled = bool(enabled)
        self.isolation_low_offset = float(low_offset)
        self.isolation_high_offset = float(high_offset)

    def process_once(self):
        iq_block = self.receiver.read_block()
        demodulator = DEMODULATORS[self.demodulation_mode]
        demod_samples, demod_sample_rate = self._prepare_demodulation_input(iq_block)
        demodulated = demodulator(demod_samples)
        audio_samples = resample_to_rate(
            demodulated,
            demod_sample_rate,
            self.audio_sample_rate,
        )
        audio_samples = self._process_audio(audio_samples)
        audio_samples = normalize_rms(remove_dc(audio_samples)) * 0.2
        audio_samples = audio_samples.astype("float32")
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

    def _prepare_demodulation_input(self, iq_block):
        if not self.isolation_enabled:
            return iq_block.samples, iq_block.sample_rate

        low_offset = self.isolation_low_offset
        high_offset = self.isolation_high_offset

        if high_offset < low_offset:
            low_offset, high_offset = high_offset, low_offset

        bandwidth = high_offset - low_offset

        if bandwidth <= 0:
            return iq_block.samples, iq_block.sample_rate

        center_offset = (low_offset + high_offset) / 2.0
        centered_samples = shift_frequency(
            iq_block.samples,
            center_offset,
            iq_block.sample_rate,
        )
        target_rate = self._channel_sample_rate(iq_block.sample_rate, bandwidth)

        if self.demodulation_mode == "fm":
            target_rate = min(
                max(target_rate, float(FM_DEMOD_SAMPLE_RATE)),
                iq_block.sample_rate,
            )

        filtered_samples = resample_to_rate(
            centered_samples,
            iq_block.sample_rate,
            target_rate,
        )
        return filtered_samples, target_rate

    def _channel_sample_rate(self, source_rate, bandwidth):
        desired_rate = max(bandwidth * 1.2, self.audio_sample_rate * 2.0)

        if desired_rate >= source_rate:
            return source_rate

        clean_rates = [
            source_rate / factor
            for factor in CHANNEL_DOWNSAMPLE_FACTORS
            if source_rate / factor >= desired_rate
        ]

        if clean_rates:
            return min(clean_rates)

        return source_rate

    def _process_audio(self, samples):
        if self.demodulation_mode != "fm":
            self._audio_filter_state = None
            return samples

        samples = np.asarray(samples, dtype=float)

        if samples.size == 0:
            return samples.copy()

        audio_rate = self.audio_sample_rate
        config = ("fm", audio_rate)

        if (
            self._audio_filter_state is None
            or self._audio_filter_state["config"] != config
        ):
            self._audio_filter_state = self._create_fm_audio_filter_state(
                audio_rate,
                samples[0],
            )

        state = self._audio_filter_state
        filtered, state["lowpass_zi"] = sosfilt(
            state["lowpass_sos"],
            samples,
            zi=state["lowpass_zi"],
        )
        deemphasized, state["deemphasis_zi"] = lfilter(
            state["deemphasis_b"],
            state["deemphasis_a"],
            filtered,
            zi=state["deemphasis_zi"],
        )
        return deemphasized

    def _create_fm_audio_filter_state(self, audio_rate, initial_sample):
        nyquist = audio_rate / 2.0
        cutoff = min(15_000.0, nyquist * 0.85)
        normalized_cutoff = cutoff / nyquist
        lowpass_sos = butter(5, normalized_cutoff, btype="lowpass", output="sos")

        tau = 50e-6
        alpha = np.exp(-1.0 / (audio_rate * tau))
        deemphasis_b = [1.0 - alpha]
        deemphasis_a = [1.0, -alpha]

        return {
            "config": ("fm", audio_rate),
            "lowpass_sos": lowpass_sos,
            "lowpass_zi": sosfilt_zi(lowpass_sos) * initial_sample,
            "deemphasis_b": deemphasis_b,
            "deemphasis_a": deemphasis_a,
            "deemphasis_zi": lfilter_zi(deemphasis_b, deemphasis_a) * initial_sample,
        }

    def run(self, on_frame=None, max_frames=None):
        frames_processed = 0

        while max_frames is None or frames_processed < max_frames:
            frame = self.process_once()
            frames_processed += 1

            if on_frame is not None:
                on_frame(frame)
