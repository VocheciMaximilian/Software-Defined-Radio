import argparse
import statistics
from collections import defaultdict
from time import perf_counter

from backend.demodulare.am import demodulate_am
from backend.demodulare.fm import demodulate_fm
from backend.dsp.fft import normalize_spectrum, power_spectrum_db
from backend.pipeline.events import PipelineFrame
from backend.pipeline.pipeline import SDRPipeline
from backend.receiver.config import ReceiverConfig
from backend.receiver.rtl_sdr_receiver import RtlSdrReceiver
from backend.receiver.synthetic_receiver import SyntheticReceiver
from backend.signal.models import AudioBlock, SpectrumFrame


DEMODULATORS = {
    "am": demodulate_am,
    "fm": demodulate_fm,
}


class TimedSDRPipeline(SDRPipeline):
    def process_once_timed(self):
        timings = {}
        total_start = perf_counter()

        stage_start = perf_counter()
        iq_block = self.receiver.read_block()
        timings["read_block"] = perf_counter() - stage_start

        demodulator = DEMODULATORS[self.demodulation_mode]

        stage_start = perf_counter()
        demod_samples, demod_sample_rate = self._prepare_demodulation_input(iq_block)
        timings["prepare_demod_input"] = perf_counter() - stage_start

        stage_start = perf_counter()
        if self.demodulation_mode == "fm":
            demod_samples = self._join_fm_blocks(demod_samples)
        else:
            self._fm_last_sample = None
        timings["join_fm_blocks"] = perf_counter() - stage_start

        stage_start = perf_counter()
        demodulated = demodulator(demod_samples)
        timings["demodulate"] = perf_counter() - stage_start

        stage_start = perf_counter()
        audio_samples = self._resample_audio(demodulated, demod_sample_rate)
        timings["resample_audio"] = perf_counter() - stage_start

        stage_start = perf_counter()
        audio_samples = self._process_audio(audio_samples)
        timings["process_fm_audio"] = perf_counter() - stage_start

        stage_start = perf_counter()
        audio_samples = self._condition_audio(audio_samples)
        timings["condition_audio"] = perf_counter() - stage_start

        stage_start = perf_counter()
        audio_samples = audio_samples.astype("float32")
        audio_block = AudioBlock.create(audio_samples, self.audio_sample_rate)
        timings["audio_block"] = perf_counter() - stage_start

        stage_start = perf_counter()
        if self.audio_output is not None:
            self.audio_output.play(audio_block.samples)
        timings["audio_output"] = perf_counter() - stage_start

        stage_start = perf_counter()
        power_db = power_spectrum_db(iq_block.samples, self.fft_size)
        timings["spectrum_fft"] = perf_counter() - stage_start

        stage_start = perf_counter()
        spectrum = SpectrumFrame.create(
            power_db,
            normalize_spectrum(power_db),
            iq_block.sample_rate,
            iq_block.center_frequency,
        )
        timings["spectrum_frame"] = perf_counter() - stage_start

        timings["total"] = perf_counter() - total_start
        frame = PipelineFrame(iq=iq_block, audio=audio_block, spectrum=spectrum)
        return frame, timings


def parse_args():
    parser = argparse.ArgumentParser(
        description="Masoara timing-ul pe etape pentru SDRPipeline.",
    )
    parser.add_argument("--source", choices=("rtl", "synthetic"), default="rtl")
    parser.add_argument("--mode", choices=("fm", "am"), default="fm")
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--frequency", type=float, default=100_600_000)
    parser.add_argument("--sample-rate", type=float, default=1_024_000)
    parser.add_argument("--gain", type=float, default=20.0)
    parser.add_argument("--block-size", type=int, default=131_072)
    parser.add_argument("--audio-rate", type=float, default=48_000)
    parser.add_argument("--fft-size", type=int, default=1024)
    parser.add_argument("--isolate", action="store_true")
    parser.add_argument("--low-offset", type=float, default=-100_000)
    parser.add_argument("--high-offset", type=float, default=100_000)
    return parser.parse_args()


def create_receiver(args):
    config = ReceiverConfig(
        center_frequency=args.frequency,
        sample_rate=args.sample_rate,
        gain=args.gain,
        block_size=args.block_size,
    )

    if args.source == "synthetic":
        return SyntheticReceiver(config)

    return RtlSdrReceiver(config)


def percentile(values, percent):
    if not values:
        return 0.0

    ordered = sorted(values)
    index = round((len(ordered) - 1) * percent / 100.0)
    return ordered[index]


def print_summary(samples, block_seconds):
    totals = samples["total"]
    mean_total = statistics.fmean(totals)
    utilization = mean_total / block_seconds if block_seconds > 0 else 0.0

    print()
    print("=== Pipeline timing summary ===")
    print(f"RF block duration: {block_seconds * 1000.0:8.3f} ms")
    print(f"Mean loop time:     {mean_total * 1000.0:8.3f} ms")
    print(f"P95 loop time:      {percentile(totals, 95) * 1000.0:8.3f} ms")
    print(f"Max loop time:      {max(totals) * 1000.0:8.3f} ms")
    print(f"Utilization:        {utilization * 100.0:8.1f} %")

    if utilization >= 1.0:
        print("Status: loop-ul este mai lent decat timpul real al blocului.")
    elif utilization >= 0.75:
        print("Status: loop-ul este aproape de limita; pot aparea blocaje.")
    else:
        print("Status: loop-ul are rezerva de timp.")

    print()
    print("Stage                         mean ms    p95 ms    max ms   share")
    print("---------------------------------------------------------------")

    total_mean = max(mean_total, 1e-12)
    for name, values in sorted(
        samples.items(),
        key=lambda item: statistics.fmean(item[1]),
        reverse=True,
    ):
        mean = statistics.fmean(values)
        p95 = percentile(values, 95)
        maximum = max(values)
        share = mean / total_mean * 100.0
        print(
            f"{name:<28}"
            f"{mean * 1000.0:8.3f}"
            f"{p95 * 1000.0:10.3f}"
            f"{maximum * 1000.0:10.3f}"
            f"{share:8.1f}%"
        )


def main():
    args = parse_args()
    receiver = create_receiver(args)
    samples = defaultdict(list)
    block_seconds = args.block_size / args.sample_rate

    pipeline = TimedSDRPipeline(
        receiver,
        demodulation_mode=args.mode,
        audio_sample_rate=args.audio_rate,
        fft_size=args.fft_size,
        audio_output=None,
    )
    pipeline.set_isolation_region(
        args.isolate,
        args.low_offset,
        args.high_offset,
    )

    print("Opening receiver...")
    receiver.open()

    try:
        total_frames = args.warmup + args.frames
        for index in range(total_frames):
            _, timings = pipeline.process_once_timed()

            if index >= args.warmup:
                for name, value in timings.items():
                    samples[name].append(value)

            completed = index + 1
            if completed % 10 == 0 or completed == total_frames:
                print(f"Processed {completed}/{total_frames} frames", end="\r")

        print()
        print_summary(samples, block_seconds)
    finally:
        receiver.close()


if __name__ == "__main__":
    main()
