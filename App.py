from Backend.Audio.Audio_output import AudioOutput
from Backend.Pipeline.Pipeline import SDRPipeline
from Backend.Receiver.Rtl_sdr_receiver import RtlSdrReceiver
from Config.Current import current_config


def main():
    receiver = RtlSdrReceiver(current_config.receiver)
    audio_output = AudioOutput(current_config.audio_sample_rate)

    with receiver:
        try:
            pipeline = SDRPipeline(
                receiver=receiver,
                demodulation_mode=current_config.demodulation_mode,
                audio_sample_rate=current_config.audio_sample_rate,
                fft_size=current_config.fft_size,
                audio_output=audio_output,
            )
            pipeline.run(max_frames=1)
        finally:
            audio_output.close()


if __name__ == "__main__":
    main()
