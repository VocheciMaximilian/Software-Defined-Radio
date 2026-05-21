## Software-Defined Radio - Receptor SDR in Python
Un sistem software pentru receptia si procesarea semnalelor radio folosind un dongle RTL-SDR si Python. Scopul aplicatiei este sa permita captarea semnalelor IQ, procesarea digitala a acestora, demodularea AM/FM si afisarea spectrului radio intr-o interfata grafica.

Aplicatia foloseste `pyrtlsdr` pentru comunicarea cu dispozitivul RTL-SDR, `numpy` si `scipy` pentru procesarea digitala a semnalului, `sounddevice` pentru redarea audio, iar interfata grafica este realizata cu `PySide6` si `pyqtgraph`.

## 1. Obiectivul proiectului
Obiectivul proiectului este realizarea unui receptor SDR care poate prelua esantioane IQ de la un dispozitiv RTL-SDR si le poate procesa in timp real.

Aplicatia urmareste sa ofere un flux complet de lucru pentru receptie radio: configurarea frecventei, captarea semnalului, filtrarea si resampling-ul datelor, demodularea semnalului si afisarea informatiilor relevante in interfata grafica.

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
|   |   `-- Fm.py
|   |
|   |-- Dsp/
|   |   |-- Fft.py
|   |   |-- Filters.py
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
### 4.1. `App.py`
Reprezinta punctul principal de pornire al aplicatiei. Acest fisier va initializa configurarea, backend-ul de procesare si interfata grafica.

### 4.2. `Backend/Receiver`
Contine componentele responsabile de comunicarea cu receptorul radio.

- `Base.py` - defineste interfata comuna pentru receptoare;
- `Config.py` - contine structurile de configurare pentru frecventa, gain si rata de esantionare;
- `Rtl_sdr_receiver.py` - implementeaza receptia datelor IQ printr-un dongle RTL-SDR.

### 4.3. `Backend/Signal`
Contine modelele si bufferele folosite pentru transportul datelor intre etapele aplicatiei.

- `Models.py` - defineste reprezentarea blocurilor de semnal;
- `Buffers.py` - gestioneaza stocarea temporara a esantioanelor procesate.

### 4.4. `Backend/Dsp`
Contine operatiile de procesare digitala a semnalului.

- `Fft.py` - calculeaza spectrul semnalului folosind transformata Fourier;
- `Filters.py` - contine filtre digitale pentru izolarea benzii utile;
- `Resampling.py` - adapteaza rata de esantionare pentru etapele urmatoare;
- `Windowing.py` - aplica functii de fereastra pentru analiza spectrala.

### 4.5. `Backend/Demodulare`
Contine modulele pentru extragerea informatiei utile din semnalul radio.

- `am.py` - demodulare pentru semnale AM;
- `fm.py` - demodulare pentru semnale FM.

### 4.6. `Backend/Audio`
Contine logica pentru redarea semnalului audio rezultat dupa demodulare.

- `Audio_output.py` - trimite esantioanele audio catre placa de sunet prin `sounddevice`.

### 4.7. `Backend/Pipeline`
Contine lantul principal de procesare si evenimentele interne ale aplicatiei.

- `Pipeline.py` - coordoneaza receptia, procesarea, demodularea si iesirea audio;
- `Events.py` - defineste evenimentele transmise intre backend si interfata.

### 4.8. `Config`
Contine configurarea implicita si configurarea curenta a aplicatiei.

- `Defaults.py` - valori implicite pentru frecventa, sample rate, gain si mod de demodulare;
- `Current.py` - configurarea folosita la rulare.

### 4.9. `Frontend`
Contine interfata grafica a aplicatiei.

- `Main_window.py` - fereastra principala;
- `Controls_panel.py` - controalele pentru frecventa, gain, mod de demodulare si volum;
- `Spectrum_view.py` - afisarea spectrului de frecventa;
- `Waterfall_view.py` - afisarea evolutiei spectrului in timp.

## 5. Dependente
Dependentele proiectului sunt definite in `requirements.txt`:

```text
numpy
scipy
pyrtlsdr
sounddevice
PySide6
pyqtgraph
```

Rolul principal al dependentelor:
- `numpy` - operatii pe vectori si esantioane numerice;
- `scipy` - functii pentru filtrare, resampling si procesare de semnal;
- `pyrtlsdr` - interfata Python pentru dispozitive RTL-SDR;
- `sounddevice` - redarea semnalului audio;
- `PySide6` - interfata grafica desktop;
- `pyqtgraph` - grafice rapide pentru spectru si waterfall.

## 6. Setup Python
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

## 7. Configurare RTL-SDR
Pentru rularea aplicatiei cu un dongle RTL-SDR este necesara instalarea driverelor potrivite pentru sistemul de operare.

Pe Windows, dispozitivul trebuie configurat astfel incat sa poata fi accesat de libraria RTL-SDR. In mod obisnuit, acest lucru presupune instalarea driverului `WinUSB` pentru dispozitivul RTL-SDR.

Setarile importante pentru receptie sunt:
- frecventa centrala;
- rata de esantionare;
- gain-ul receptorului;
- modul de demodulare;
- latimea de banda procesata.