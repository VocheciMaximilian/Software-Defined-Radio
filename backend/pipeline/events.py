from dataclasses import dataclass

from backend.signal.models import AudioBlock, IQBlock, SpectrumFrame


@dataclass(frozen=True)
class PipelineFrame:
    iq: IQBlock
    audio: AudioBlock
    spectrum: SpectrumFrame | None


@dataclass(frozen=True)
class PipelineError:
    message: str
    exception: Exception | None = None
