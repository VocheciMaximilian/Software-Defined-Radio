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
pyrtlsdr[lib]
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

Aplicatia foloseste API-ul Python `pyrtlsdr`, dar acesta incarca in continuare o librarie nativa `librtlsdr`/`rtlsdr.dll`. Arhitectura trebuie sa se potriveasca: Python 64-bit are nevoie de DLL-uri 64-bit, iar Python 32-bit are nevoie de DLL-uri 32-bit. Instalarea recomandata este:

```powershell
python -m pip install --upgrade "pyrtlsdr[lib]"
```

Daca exista DLL-uri RTL-SDR vechi in `PATH` sau in folderul `dll/`, acestea pot fi incarcate inaintea celor bune si pot produce erori de import precum lipsa functiei `rtlsdr_set_dithering`.

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
- configurarea gain-ului manual;
- alegerea modului de demodulare AM/FM;
- modificarea dimensiunii FFT;
- activarea iesirii audio;
- vizualizarea spectrului si waterfall-ului in timp real.

## 10. Probleme intampinate recent si investigatii
### 10.1. Problema cu driverul / libraria RTL-SDR
In timpul integrarii cu dongle-ul RTL-SDR au aparut probleme legate de accesul la dispozitiv si de librariile native folosite de `pyrtlsdr`.

Simptome observate:
- aplicatia poate porni, dar citirea blocurilor IQ poate esua in timpul rularii;
- pot aparea erori de comunicare USB in momentul in care aplicatia incearca sa citeasca esantioane IQ de la dispozitiv;
- in unele configuratii, `pyrtlsdr` poate incarca un `rtlsdr.dll` incompatibil sau prea vechi, ceea ce poate produce erori de import, inclusiv lipsa functiei `rtlsdr_set_dithering`.

Ce s-a incercat pana acum:
- instalarea dependintei cu libraria nativa inclusa:

```powershell
python -m pip install --upgrade "pyrtlsdr[lib]"
```

- verificarea faptului ca Python si DLL-urile RTL-SDR au aceeasi arhitectura, de preferat 64-bit;
- adaugarea suportului pentru folderul local `dll/`, astfel incat aplicatia sa poata incarca librarii RTL-SDR din proiect daca folderul exista;
- tratarea explicita a erorilor de import in `RtlSdrReceiver`, cu mesaje mai clare pentru DLL incompatibil sau lipsa librariei native;
- configurarea dispozitivului cu driver `WinUSB`, necesar in mod obisnuit pe Windows pentru acces prin `librtlsdr`;
- reducerea riscului de stare instabila prin inchiderea receiver-ului daca initializarea esueaza.

Pasi ramasi de verificat:
- testarea dongle-ului cu un utilitar extern, de exemplu `rtl_test`, pentru a confirma ca driverul si dispozitivul functioneaza independent de aplicatie;
- verificarea portului USB si evitarea hub-urilor USB daca apar erori intermitente de tip `LIBUSB_ERROR_IO`;
- incercarea unei dimensiuni mai mici pentru `block_size`, daca eroarea apare la citiri mari.

### 10.2. Problema cu sunetul / iesirea audio
Au aparut probleme si in zona de redare audio, unde semnalul demodulat trebuie trimis catre placa de sunet prin `sounddevice`.

Simptome posibile:
- aplicatia ruleaza si proceseaza semnalul, dar nu se aude nimic;
- audio-ul poate fi intrerupt sau instabil daca pipeline-ul produce esantioane intr-un ritm diferit fata de consumul placii de sunet;
- pot aparea erori daca `sounddevice` nu este instalat corect sau daca backend-ul audio al sistemului nu este disponibil.

Ce s-a incercat pana acum:
- folosirea `sounddevice.OutputStream` cu un callback audio dedicat;
- conversia esantioanelor la `float32`, format potrivit pentru iesirea audio;
- limitarea semnalului audio in intervalul `[-1.0, 1.0]` pentru a evita clipping-ul excesiv;
- introducerea unui buffer intern bazat pe coada, astfel incat callback-ul audio sa poata consuma esantioane fara sa depinda direct de viteza pipeline-ului;
- folosirea unei latente mai mari (`latency="high"`) pentru stabilitate;
- pastrarea iesirii audio pe un singur canal (`channels=1`) si sample rate audio standard de `48_000` Hz.

Pasi ramasi de verificat:
- listarea dispozitivelor audio disponibile in `sounddevice` si alegerea explicita a dispozitivului corect, daca sistemul are mai multe iesiri;
- verificarea ratei audio finale dupa demodulare si resampling, ca sa ramana compatibila cu `48_000` Hz;
- testarea pipeline-ului audio cu un semnal generat software, separat de receptorul RTL-SDR, pentru a izola problema de partea radio.

## 11. Functionalitati implementate
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

## 12. Testare
In prezent, proiectul nu include o suita de teste automate.

Verificarea manuala recomandata:
- rularea verificarii de sintaxa pentru fisierele Python;
- testarea functiilor DSP cu semnale generate artificial;
- conectarea dongle-ului RTL-SDR si rularea `python App.py`;
- verificarea frame-ului audio si a frame-ului de spectru produse de pipeline.
