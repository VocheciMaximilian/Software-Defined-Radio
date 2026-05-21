## Software-Defined Radio - Receptor SDR in Python
Un sistem software pentru receptia si procesarea semnalelor radio folosind un dongle RTL-SDR si Python. Scopul aplicatiei este sa ofere o arhitectura clara pentru captarea semnalelor IQ, procesarea digitala, demodularea AM/FM, redarea audio si afisarea spectrului radio.

Aplicatia foloseste `pyrtlsdr` pentru comunicarea cu dispozitivul RTL-SDR, `numpy` si `scipy` pentru procesarea digitala a semnalului, `sounddevice` pentru redarea audio, iar interfata grafica este pregatita pentru `PySide6` si `pyqtgraph`.

## 1. Obiectivul proiectului
Obiectivul proiectului este realizarea unui receptor SDR modular, in care fiecare componenta are o responsabilitate separata:
- receptorul citeste blocuri IQ;
- modulele DSP proceseaza semnalul prin functii pure;
- demodulatoarele extrag semnalul audio;
- pipeline-ul coordoneaza fluxul de date;
- frontend-ul afiseaza controalele, spectrul si waterfall-ul.

Aceasta separare permite testarea mai usoara a fiecarei parti si extinderea proiectului cu moduri noi de demodulare sau surse diferite de semnal.

## 2. Teoria lucrarii
Aceasta sectiune va fi completata ulterior.

Subiecte care pot fi incluse:
- principiul de functionare al unui sistem Software-Defined Radio;
- reprezentarea semnalelor IQ;
- esantionarea si rata de esantionare;
- spectrul de frecvente si transformata Fourier;
- filtrarea digitala a semnalelor;
- demodularea AM si FM;
- rolul resampling-ului in lantul de procesare;
- particularitati ale dispozitivelor RTL-SDR.

## 3. Structura proiectului
```text
Software-Defined-Radio/
|-- App.py
|-- requirements.txt
|-- README.md
|
|-- Backend/
|   |-- Audio/
|   |   `-- Audio_output.py
|   |
|   |-- Demodulare/
|   |   |-- Am.py
|   |   |-- Fm.py
|   |   `-- Modulation.py
|   |
|   |-- Dsp/
|   |   |-- Fft.py
|   |   |-- Filters.py
|   |   |-- Frequency.py
|   |   |-- Resampling.py
|   |   `-- Windowing.py
|   |
|   |-- Pipeline/
|   |   |-- Events.py
|   |   `-- Pipeline.py
|   |
|   |-- Receiver/
|   |   |-- Base.py
|   |   |-- Config.py
|   |   `-- Rtl_sdr_receiver.py
|   |
|   `-- Signal/
|       |-- Buffers.py
|       `-- Models.py
|
|-- Config/
|   |-- Current.py
|   `-- Defaults.py
|
`-- Frontend/
    |-- Controls_panel.py
    |-- Main_window.py
    |-- Spectrum_view.py
    `-- Waterfall_view.py
```

## 4. Rolul modulelor
### 4.1. `Backend/Signal`
Contine modelele de date folosite intre componente.

- `IQBlock` - bloc de esantioane complexe IQ, impreuna cu sample rate, frecventa centrala si timestamp;
- `AudioBlock` - bloc de esantioane audio normalizate;
- `SpectrumFrame` - frame de spectru folosit pentru afisare;
- `SampleBuffer` - buffer simplu pentru pastrarea ultimelor blocuri de esantioane.

### 4.2. `Backend/Dsp`
Contine functii pure de procesare digitala a semnalului. Aceste functii nu modifica starea aplicatiei si primesc datele explicit ca parametri.

- `Fft.py` - putere, spectru in dB, normalizare spectru si spectrograma;
- `Filters.py` - moving average, eliminare DC si normalizare RMS;
- `Frequency.py` - axa de frecvente, estimare de banda ocupata si shift de frecventa;
- `Resampling.py` - calcul factor de decimare si decimare;
- `Windowing.py` - ferestre Hann pentru analiza spectrala.

### 4.3. `Backend/Demodulare`
Contine logica de modulare si demodulare.

- `Am.py` - demodulare AM prin detectie de anvelopa;
- `Fm.py` - demodulare FM prin diferenta de faza intre esantioane consecutive;
- `Modulation.py` - modulare AM pentru semnale generate software.

### 4.4. `Backend/Receiver`
Contine contractul pentru receptoare si implementarea pentru RTL-SDR.

- `ReceiverConfig` - frecventa centrala, sample rate, gain si block size;
- `Receiver` - clasa abstracta pentru orice sursa IQ;
- `RtlSdrReceiver` - implementarea concreta pentru dongle RTL-SDR.

### 4.5. `Backend/Audio`
Contine iesirea audio.

- `AudioOutput` - trimite esantioanele audio catre placa de sunet folosind `sounddevice`.

### 4.6. `Backend/Pipeline`
Contine coordonarea fluxului SDR.

- `PipelineFrame` - rezultatul unei iteratii: IQ, audio si spectru;
- `SDRPipeline` - citeste din receiver, demoduleaza, calculeaza spectrul si trimite audio la iesire.

### 4.7. `Config`
Contine configurarea implicita si configurarea curenta a aplicatiei.

### 4.8. `Frontend`
Contine interfata grafica desktop inspirata de aplicatii SDR clasice precum SDRSharp.

- `Main_window.py` - fereastra principala, layout-ul general, pornirea si oprirea pipeline-ului;
- `Controls_panel.py` - panou lateral pentru frecventa, sample rate, gain, mod AM/FM, FFT si audio;
- `Spectrum_view.py` - grafic de spectru realizat cu `pyqtgraph`;
- `Waterfall_view.py` - afisare waterfall pe baza frame-urilor de spectru normalizate.

## 5. Fluxul aplicatiei
```text
RTL-SDR
   |
   v
RtlSdrReceiver
   |
   v
IQBlock
   |
   v
SDRPipeline
   |-- demodulare AM/FM -> AudioBlock -> AudioOutput
   |
   `-- FFT + normalizare -> SpectrumFrame -> Spectrum/Waterfall UI
```

Pipeline-ul este singurul strat care leaga componentele intre ele. Modulele DSP raman independente si pot fi testate separat cu semnale generate artificial.

## 6. Dependente
Dependentele proiectului sunt definite in `requirements.txt`:

```text
numpy
scipy
pyrtlsdr
sounddevice
PySide6
pyqtgraph
```

## 7. Setup Python
Creare mediu virtual:

```powershell
python -m venv .venv
```

Activare mediu virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalare dependente:

```powershell
python -m pip install -r requirements.txt
```

## 8. Configurare RTL-SDR
Pentru rularea aplicatiei cu un dongle RTL-SDR este necesara instalarea driverelor potrivite pentru sistemul de operare.

Pe Windows, dispozitivul trebuie configurat astfel incat sa poata fi accesat de libraria RTL-SDR. In mod obisnuit, acest lucru presupune instalarea driverului `WinUSB` pentru dispozitivul RTL-SDR.

Setarile importante sunt definite prin `ReceiverConfig`:
- `center_frequency`;
- `sample_rate`;
- `gain`;
- `block_size`.

## 9. Rulare
Aplicatia se ruleaza din radacina proiectului, dupa activarea mediului virtual:

```powershell
python App.py
```

Entrypoint-ul porneste interfata grafica si conecteaza controalele la backend-ul SDR. Frontend-ul nu instantiaza receiver-ul si nu cunoaste pipeline-ul; el doar emite setarile selectate si afiseaza frame-urile primite.

Interfata permite:
- pornirea si oprirea pipeline-ului;
- selectarea frecventei centrale;
- selectarea ratei de esantionare;
- configurarea gain-ului manual sau automat;
- alegerea modului de demodulare AM/FM;
- modificarea dimensiunii FFT;
- activarea iesirii audio;
- vizualizarea spectrului si waterfall-ului in timp real.

## 10. Functionalitati implementate
- Modele de date pentru blocuri IQ, audio si spectru.
- Functii pure pentru FFT, putere, normalizare spectru si spectrograma.
- Functii pure pentru eliminare DC, moving average si normalizare RMS.
- Estimare de banda ocupata si shift de frecventa.
- Demodulare AM.
- Demodulare FM.
- Modulare AM.
- Contract abstract pentru receptoare.
- Implementare RTL-SDR.
- Iesire audio prin `sounddevice`.
- Pipeline SDR pentru procesarea unui frame complet.
- Interfata grafica desktop cu panou de control, spectrum view si waterfall view.

## 11. Testare
In prezent, proiectul nu include o suita de teste automate.

Verificarea manuala recomandata:
- rularea verificarii de sintaxa pentru fisierele Python;
- testarea functiilor DSP cu semnale generate artificial;
- conectarea dongle-ului RTL-SDR si rularea `python App.py`;
- verificarea frame-ului audio si a frame-ului de spectru produse de pipeline.
