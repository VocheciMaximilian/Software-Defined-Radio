from dataclasses import dataclass

from Backend.Signal.Models import AudioBlock, IQBlock, SpectrumFrame


@dataclass(frozen=True)
class PipelineFrame:
    iq: IQBlock
    audio: AudioBlock
    spectrum: SpectrumFrame


@dataclass(frozen=True)
class PipelineError:
    message: str
    exception: Exception | None = None
