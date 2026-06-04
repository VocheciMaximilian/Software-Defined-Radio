# Software-Defined Radio - Receptor SDR in Python
Acest proiect este un receptor radio software construit in Python. Poate lucra cu un dongle RTL-SDR real, dar poate genera si un semnal sintetic local, ca sa poti porni aplicatia si fara hardware conectat.

Aplicatia urmareste tot drumul semnalului: receptie IQ, filtrare, translatare in frecventa, demodulare AM/FM, redare si inregistrare audio, spectru si waterfall. Codul este impartit in componente mici, astfel incat fiecare etapa sa poata fi inteleasa, testata si modificata separat.

Aplicatia foloseste `pyrtlsdr` pentru comunicarea cu dispozitivul RTL-SDR, `numpy` si `scipy` pentru procesarea digitala a semnalului, `sounddevice` pentru redarea audio, iar interfata grafica este realizata cu `PySide6` si `pyqtgraph`.

Documentatie actualizata la `4 iunie 2026`. Pentru o prima rulare, incepe cu [pornirea rapida fara hardware](#101-pornire-rapida-fara-hardware). Pentru explicatiile de fundal, continua cu [teoria lucrarii](#2-teoria-lucrarii).

## Cuprins
- [1. Obiectivul proiectului](#1-obiectivul-proiectului)
- [2. Teoria lucrarii](#2-teoria-lucrarii)
  - [2.1. Esantionarea IQ](#21-esantionarea-iq)
  - [2.2. Rata de esantionare si conditia Nyquist](#22-rata-de-esantionare-si-conditia-nyquist)
  - [2.3. Translatarea in frecventa](#23-translatarea-in-frecventa)
  - [2.4. Analiza in frecventa cu FFT](#24-analiza-in-frecventa-cu-fft)
  - [2.5. Izolarea canalului si resampling](#25-izolarea-canalului-si-resampling)
  - [2.6. Modularea si demodularea AM](#26-modularea-si-demodularea-am)
  - [2.7. Modularea si demodularea FM](#27-modularea-si-demodularea-fm)
  - [2.8. Conditionarea semnalului audio](#28-conditionarea-semnalului-audio)
    - [2.8.1. Redarea audio in timp real](#281-redarea-audio-in-timp-real)
  - [2.9. Ferestre de analiza si fereastra Hann](#29-ferestre-de-analiza-si-fereastra-hann)
  - [2.10. Spectrograma](#210-spectrograma)
  - [2.11. Waterfall](#211-waterfall)
  - [2.12. Media mobila si netezirea semnalului](#212-media-mobila-si-netezirea-semnalului)
  - [2.13. Eliminarea componentei DC](#213-eliminarea-componentei-dc)
  - [2.14. Normalizarea RMS](#214-normalizarea-rms)
  - [2.15. Estimarea benzii ocupate](#215-estimarea-benzii-ocupate)
  - [2.16. Scanarea unei benzi de frecventa](#216-scanarea-unei-benzi-de-frecventa)
- [3. Structura proiectului](#3-structura-proiectului)
- [4. Rolul modulelor](#4-rolul-modulelor)
- [5. Fluxul aplicatiei](#5-fluxul-aplicatiei)
- [6. Threading si concurenta](#6-threading-si-concurenta)
- [7. Dependente](#7-dependente)
- [8. Setup Python](#8-setup-python)
- [9. Configurare RTL-SDR](#9-configurare-rtl-sdr)
- [10. Rulare](#10-rulare)
  - [10.1. Pornire rapida fara hardware](#101-pornire-rapida-fara-hardware)
  - [10.2. Utilizarea interfetei](#102-utilizarea-interfetei)
- [11. Depanare](#11-depanare)
- [12. Functionalitati implementate](#12-functionalitati-implementate)
- [13. Testare](#13-testare)
- [14. Profilarea pipeline-ului](#14-profilarea-pipeline-ului)
- [15. Limite actuale si directii de extindere](#15-limite-actuale-si-directii-de-extindere)
- [16. Referinte si documentatie externa](#16-referinte-si-documentatie-externa)
- [17. Ce am invatat din proiect](#17-ce-am-invatat-din-proiect)
- [18. Dificultati intampinate](#18-dificultati-intampinate)

## 1. Obiectivul proiectului
Obiectivul proiectului este realizarea unui receptor SDR modular, usor de urmarit si de depanat. Fiecare componenta are o responsabilitate clara:
- receptorul citeste blocuri IQ;
- modulele DSP proceseaza semnalul prin functii pure;
- demodulatoarele extrag semnalul audio;
- pipeline-ul coordoneaza fluxul de date;
- frontend-ul afiseaza controalele, spectrul si waterfall-ul.

Aceasta separare face proiectul mai prietenos la lucru: poti testa o parte fara sa pornesti tot lantul radio si poti adauga mai tarziu moduri noi de demodulare sau surse diferite de semnal.

## 2. Teoria lucrarii
Un receptor SDR muta cat mai multa logica radio din hardware in software. In loc ca semnalul sa fie filtrat, demodulat si transformat in audio de circuite analogice dedicate, dongle-ul RTL-SDR face conversia initiala in esantioane digitale, iar aplicatia Python proceseaza numeric aceste esantioane. Fluxul principal este:

```text
semnal RF -> conversie in banda de baza IQ -> procesare DSP -> demodulare -> audio/spectru
```

### 2.1. Esantionarea IQ
Semnalul radio receptionat este un semnal real de frecventa inalta. Pentru a putea fi procesat eficient, receptorul il translateaza in jurul frecventei centrale selectate si il reprezinta in banda de baza prin doua componente:
- `I` - componenta in faza;
- `Q` - componenta in cuadratura, defazata cu 90 de grade.

Un esantion IQ este reprezentat ca numar complex:

$$
x[n] = I[n] + jQ[n]
$$

unde `n` este indexul esantionului, iar `j` este unitatea imaginara. Aceasta reprezentare pastreaza simultan informatia de amplitudine si de faza a semnalului. Amplitudinea instantanee este:

$$
|x[n]| = \sqrt{I[n]^2 + Q[n]^2}
$$

iar faza instantanee este:

$$
\varphi[n] = \mathrm{atan2}(Q[n], I[n])
$$

In proiect, blocurile IQ sunt citite din `RtlSdrReceiver`, apoi sunt impachetate intr-un `IQBlock`, impreuna cu rata de esantionare si frecventa centrala.

### 2.2. Rata de esantionare si conditia Nyquist
Rata de esantionare, notata cu $f_s$, stabileste cate esantioane sunt citite pe secunda. Pentru ca un semnal cu latimea de banda $B$ sa poata fi reconstruit fara aliasing, este necesar ca:

$$
f_s \ge 2B
$$

In practica se foloseste o rezerva peste limita teoretica, deoarece filtrele digitale nu au tranzitie ideala. In aplicatie, rata IQ este mai mare decat rata audio finala. Dupa izolarea canalului si demodulare, semnalul este resamplat catre rata audio standard:

$$
f_{audio} = 48000 \text{ Hz}
$$

### 2.3. Translatarea in frecventa
Daca semnalul de interes nu este exact in centrul benzii receptionate, el poate fi mutat digital prin inmultirea cu o exponentiala complexa:

$$
y[n] = x[n] \cdot e^{-j2\pi f_0 n / f_s}
$$

unde $f_0$ este offset-ul fata de frecventa centrala, iar $f_s$ este rata de esantionare. Aceasta operatie este folosita pentru a aduce canalul selectat in jurul frecventei zero, inainte de resampling si demodulare.

In cod, aceasta operatie apare in pipeline prin functia interna de shift continuu, care pastreaza faza intre blocuri pentru a evita discontinuitati la marginea blocurilor.

### 2.4. Analiza in frecventa cu FFT
Pentru afisarea spectrului, semnalul IQ este transformat din domeniul timp in domeniul frecventa folosind Transformata Fourier Discreta:

$$
X[k] = \sum_{n=0}^{N-1} x[n] e^{-j2\pi kn/N}
$$

unde $N$ este dimensiunea FFT, iar $k$ este indexul binului de frecventa. Puterea spectrala este calculata ca:

$$
P[k] = |X[k]|^2
$$

Pentru afisare este mai utila scara logaritmica in decibeli:

$$
P_{dB}[k] = 10 \log_{10}(P[k] + \epsilon)
$$

Termenul $\epsilon$ evita logaritmul lui zero. In implementare, blocurile sunt impartite in frame-uri de lungime `fft_size`, se aplica o fereastra Hann pentru reducerea scurgerii spectrale, apoi se face media puterii pe frame-uri. Rezultatul este normalizat in intervalul `[0, 1]` pentru afisarea waterfall-ului.

### 2.5. Izolarea canalului si resampling
Semnalul receptionat poate contine mai multe canale in aceeasi banda IQ. Pentru procesarea unui canal ales, aplicatia poate folosi o regiune de izolare definita prin doua offset-uri fata de frecventa centrala. Latimea benzii selectate este:

$$
B = f_{high} - f_{low}
$$

iar centrul acestei regiuni este:

$$
f_c = \frac{f_{low} + f_{high}}{2}
$$

Dupa translatarea canalului in banda de baza, semnalul poate fi redus la o rata de esantionare mai mica. Resampling-ul reduce volumul de date si face demodularea mai stabila, cu conditia ca noua rata sa ramana suficient de mare pentru latimea de banda procesata.

In proiect, `StreamingResampler` foloseste `scipy.signal.resample_poly`, adica resampling rational prin interpolare si decimare polifazica. Pentru un raport:

$$
\frac{f_{target}}{f_{source}} = \frac{L}{M}
$$

semnalul este interpolat cu factorul $L$ si decimat cu factorul $M$.

Pentru FM, filtrarea de canal ramane activa si cand regiunea vizuala de izolare este dezactivata. Inainte de demodulare se aplica si un filtru DC blocker complex asupra esantioanelor IQ, pentru reducerea componentei continue introduse frecvent de receptoarele RTL-SDR.

### 2.6. Modularea si demodularea AM
Modularea transfera informatia dintr-un semnal de baza, de exemplu voce sau muzica, pe o purtatoare radio de frecventa mai mare. In modulatia de amplitudine (`AM`), amplitudinea purtatoarei variaza in functie de mesaj, iar frecventa purtatoarei ramane constanta.

Pentru un mesaj normalizat $m(t)$, o purtatoare cu frecventa $f_c$ si amplitudine $A_c$, semnalul AM poate fi scris:

$$
s_{AM}(t) = A_c \left[1 + \mu m(t)\right] \cos(2\pi f_c t)
$$

unde $\mu$ este indicele de modulatie. Pentru evitarea supramodularii este recomandat:

$$
0 \le \mu \le 1
$$

Daca $\mu > 1$, anvelopa poate traversa valoarea zero, iar un demodulator simplu de anvelopa introduce distorsiuni. Pentru un ton audio de frecventa $f_m$, spectrul contine purtatoarea la $f_c$ si doua benzi laterale la:

$$
f_c - f_m
$$

$$
f_c + f_m
$$

In reprezentarea IQ complexa, purtatoarea poate fi vazuta ca o rotatie in planul complex, iar mesajul AM modifica raza acestei rotatii. Informatia utila este deci continuta in modulul esantioanelor IQ:

$$
m_{AM}[n] = |x[n]|
$$

Componenta continua este eliminata pentru ca audio-ul rezultat sa fie centrat in jurul valorii zero:

$$
m_{AM,curat}[n] = m_{AM}[n] - \overline{m_{AM}}
$$

In implementare, `demodulate_am` calculeaza `np.abs(iq_samples)` si aplica eliminarea componentei DC. Modulul `backend/demodulare/modulation.py` include si `modulate_am`, folosit pentru generarea software a unui semnal AM si pentru experimente controlate.

### 2.7. Modularea si demodularea FM
In modulatia de frecventa (`FM`), amplitudinea purtatoarei ramane aproximativ constanta, iar mesajul modifica frecventa instantanee. Pentru un mesaj normalizat $m(t)$, semnalul poate fi exprimat:

$$
s_{FM}(t) = A_c \cos \left(2\pi f_c t + 2\pi \Delta f \int_0^t m(\tau) d\tau \right)
$$

unde:
- $f_c$ este frecventa purtatoarei;
- $\Delta f$ este deviatia maxima de frecventa;
- integrala mesajului modifica faza instantanee.

Frecventa instantanee devine:

$$
f_i(t) = f_c + \Delta f \cdot m(t)
$$

Pentru FM broadcast, deviatia maxima uzuala este aproximativ `75 kHz`. Banda ocupata poate fi estimata prin regula lui Carson:

$$
B_{FM} \approx 2(\Delta f + f_{m,max})
$$

Daca frecventa audio maxima este aproximativ `15 kHz`, rezulta:

$$
B_{FM} \approx 2(75\,000 + 15\,000) = 180\,000 \text{ Hz}
$$

Acesta este motivul pentru care pipeline-ul foloseste o banda de canal apropiata de `200 kHz` si o rata intermediara de demodulare de `240 kHz`.

In esantioanele IQ, informatia FM este continuta in variatia fazei. Frecventa instantanee este proportionala cu diferenta de faza dintre doua esantioane consecutive. Diferenta se calculeaza robust prin:

$$
m_{FM}[n] = \angle \left( x[n] \cdot x^*[n-1] \right)
$$

unde $x^*[n-1]$ este conjugatul complex al esantionului anterior. Aceasta formula evita calculul separat al fazei absolute si reduce problemele de infasurare a fazei in intervalul $[-\pi, \pi]$.

In pipeline, ultimul esantion din blocul anterior este pastrat si lipit la blocul curent pentru ca demodularea FM sa ramana continua intre citiri succesive. Inainte de discriminator se aplica un DC blocker complex, deoarece un offset IQ introdus de receptor poate modifica artificial unghiul esantioanelor si poate produce distorsiuni.

### 2.8. Conditionarea semnalului audio
Dupa demodulare, semnalul rezultat nu este inca potrivit direct pentru redare. Aplicatia aplica mai multe etape de conditionare:
- resampling catre `48_000 Hz`;
- eliminare DC cu un filtru trece-sus simplu;
- pentru FM, filtru trece-sus audio, notch la `19 kHz` pentru pilotul stereo, filtru trece-jos mono la `15 kHz` si de-emphasis;
- normalizare RMS pentru volum mai constant;
- limitare soft cu `tanh` pentru a reduce clipping-ul.

Filtrul de blocare DC poate fi exprimat prin relatia:

$$
y[n] = x[n] - x[n-1] + R \cdot y[n-1]
$$

unde $R$ este apropiat de 1. In proiect se foloseste:

$$
R = 0.995
$$

Pentru FM broadcast se aplica si de-emphasis, un filtru trece-jos de ordinul intai care compenseaza pre-emphasis-ul folosit la transmisie. In Europa, constanta de timp folosita este:

$$
\tau = 50 \mu s
$$

La final, semnalul este convertit la `float32` si trimis catre `AudioOutput`.

#### 2.8.1. Redarea audio in timp real
Inregistrarea WAV si redarea live folosesc acelasi `AudioBlock`, dar au cerinte diferite. Recorder-ul poate scrie blocurile succesiv pe disc. Placa de sunet trebuie alimentata la o cadenta continua, in acest proiect:

$$
f_{audio} = 48\,000 \text{ esantioane/s}
$$

Redarea este realizata de `AudioOutput` prin `sounddevice.OutputStream`. In modul `Automatic`, aplicatia foloseste iesirea implicita a sistemului. Daca sistemul are mai multe iesiri, un dispozitiv concret poate fi ales explicit din interfata.

Fluxul audio live este:

```text
AudioBlock float32
        |
        v
coada AudioOutput
        |
        v
callback sounddevice / WASAPI
        |
        v
placa de sunet
```

`AudioOutput` foloseste:
- o coada maxima de aproximativ `1 s`;
- un prebuffer initial de `500 ms`;
- o tinta de coada de aproximativ `400 ms`;
- reluare controlata dupa underrun, numai dupa refacerea unei rezerve suficiente;
- suport optional pentru compensarea lenta a diferentei dintre ceasul receptorului SDR si ceasul placii audio; aceasta compensare este dezactivata implicit pentru a pastra semnalul neschimbat.

Un `underrun` apare atunci cand callback-ul placii audio cere esantioane, dar coada este goala. Rezultatul perceptibil este o pauza sau o intrerupere. Un `overrun` apare cand producatorul este mai rapid decat consumatorul si coada ajunge la limita maxima.

Pentru receptia RTL-SDR, citirea IQ ruleaza separat prin `BufferedReceiver`:

```text
thread citire RTL-SDR -> coada IQ -> DSP -> coada audio -> callback WASAPI
```

Coada IQ absoarbe intarzierile scurte din DSP sau UI. In plus, FFT-ul si randarea grafica sunt executate doar pentru un frame din patru, in timp ce traseul audio continua la fiecare bloc IQ.

Fereastra `Audio diagnostics` afiseaza valorile utile pentru investigare:
- `Queued audio` - rezerva audio disponibila;
- `Underruns` si `Overruns` - incidentele cozii audio;
- `PortAudio status` - avertizarile backend-ului audio;
- `Callback frames` - dimensiunea blocului solicitat de placa audio;
- `Last SDR loop` si `Maximum SDR loop` - durata procesarii;
- `Audio production` - debitul produs, care ar trebui sa fie apropiat de `48_000 S/s`;
- `Queued IQ` - rezerva disponibila intre thread-ul RTL-SDR si DSP.

### 2.9. Ferestre de analiza si fereastra Hann
Atunci cand se calculeaza FFT pe un bloc finit de esantioane, se presupune implicit ca acel bloc se repeta periodic. Daca inceputul si finalul blocului nu se potrivesc perfect, apar discontinuitati artificiale care imprastie energia in mai multe binuri de frecventa. Acest efect se numeste scurgere spectrala.

Pentru reducerea scurgerii spectrale se aplica o functie fereastra inainte de FFT. In proiect este folosita fereastra Hann:

$$
w[n] = 0.5 - 0.5 \cos \left( \frac{2\pi n}{N - 1} \right)
$$

Semnalul analizat devine:

$$
x_w[n] = x[n] \cdot w[n]
$$

Fereastra Hann reduce amplitudinea esantioanelor de la marginile blocului si pastreaza mai mult din energia centrala. Rezultatul este un spectru mai stabil vizual, cu lobi laterali mai mici, potrivit pentru afisarea in timp real.

### 2.10. Spectrograma
O spectrograma reprezinta evolutia spectrului in timp. In loc sa se calculeze o singura FFT pentru tot semnalul, semnalul este impartit in ferestre succesive, iar pentru fiecare fereastra se calculeaza spectrul de putere:

$$
S[t, k] = 10 \log_{10} \left( |FFT(x_t)[k]|^2 + \epsilon \right)
$$

unde:
- $t$ este indexul frame-ului temporal;
- $k$ este indexul binului de frecventa;
- $x_t$ este blocul de esantioane analizat la momentul $t$.

Rezultatul este o matrice in care fiecare rand corespunde unui moment de timp, iar fiecare coloana corespunde unei frecvente. In proiect, functia `spectrogram_matrix` construieste aceasta matrice prin aplicarea repetata a functiei `power_spectrum_db`.

### 2.11. Waterfall
Waterfall-ul este o reprezentare vizuala a spectrogramei. Axa orizontala reprezinta frecventa, axa verticala reprezinta timpul, iar culoarea reprezinta puterea semnalului. Un semnal puternic apare ca o zona mai luminoasa, iar zgomotul de fond apare mai intunecat.

Pentru fiecare frame de spectru se calculeaza o linie normalizata:

$$
W[t, k] = \mathrm{clip} \left( \frac{P_{dB}[t, k] - F}{C - F}, 0, 1 \right)
$$

unde:
- $F$ este nivelul de podea al zgomotului;
- $C$ este nivelul superior folosit pentru contrast;
- `clip` limiteaza valoarea in intervalul `[0, 1]`.

In interfata, `WaterfallView` pastreaza ultimele frame-uri intr-o lista si construieste o matrice cu `np.vstack`. Aceasta matrice este trimisa catre `pyqtgraph.ImageItem`, care o afiseaza ca imagine colorata.

Pentru ca imaginea sa nu sara brusc atunci cand nivelul semnalului se schimba, podeaua si plafonul sunt estimate din percentile si netezite in timp:

$$
F_{nou} = F_{vechi} + \alpha(F_{masurat} - F_{vechi})
$$

$$
C_{nou} = C_{vechi} + \alpha(C_{masurat} - C_{vechi})
$$

In implementare, $\alpha = 0.08$, podeaua foloseste percentila 5, iar plafonul foloseste percentila 99.

### 2.12. Media mobila si netezirea semnalului
Media mobila este un filtru simplu de netezire. Fiecare esantion este inlocuit cu media unui grup local de esantioane:

$$
y[n] = \frac{1}{M} \sum_{i=0}^{M-1} x[n-i]
$$

unde $M$ este dimensiunea ferestrei. Acest filtru reduce variatiile rapide si poate fi interpretat ca un filtru trece-jos simplu. In proiect apare ca `moving_average` si `lowpass_moving_avg`.

O utilizare practica este estimarea benzii ocupate: spectrul de putere este netezit pentru a reduce varfurile izolate, apoi se cauta zona in care puterea depaseste un prag.

### 2.13. Eliminarea componentei DC
Componenta DC este media semnalului. In audio sau in demodulare, aceasta componenta poate produce offset si poate consuma inutil dinamica semnalului. Pentru eliminarea ei se scade media:

$$
y[n] = x[n] - \mu_x
$$

unde:

$$
\mu_x = \frac{1}{N} \sum_{n=0}^{N-1} x[n]
$$

In demodularea AM, eliminarea DC este importanta deoarece detectia de anvelopa produce o valoare strict pozitiva. Fara eliminarea mediei, semnalul audio ar fi deplasat fata de zero.

### 2.14. Normalizarea RMS
RMS, prescurtare de la Root Mean Square, masoara nivelul eficace al unui semnal. Pentru un bloc de esantioane, valoarea RMS este:

$$
x_{RMS} = \sqrt{\frac{1}{N} \sum_{n=0}^{N-1} |x[n]|^2}
$$

Normalizarea RMS imparte semnalul la aceasta valoare:

$$
y[n] = \frac{x[n]}{x_{RMS} + \epsilon}
$$

Termenul $\epsilon$ evita impartirea la zero. Aceasta normalizare pastreaza forma semnalului, dar aduce nivelul sau mediu la o scara comparabila intre blocuri diferite.

In pipeline-ul audio se foloseste o varianta adaptiva: se calculeaza RMS-ul blocului curent, apoi se ajusteaza treptat un castig astfel incat semnalul sa se apropie de un nivel tinta. Castigul dorit este:

$$
G_{dorit} = \min \left( \frac{RMS_{tinta}}{RMS_{curent} + \epsilon}, G_{max} \right)
$$

Iar castigul aplicat este netezit in timp:

$$
G_{nou} = G_{vechi} + \beta(G_{dorit} - G_{vechi})
$$

Aceasta abordare evita schimbari bruste de volum intre blocuri succesive.

### 2.15. Estimarea benzii ocupate
Pentru a aproxima zona din spectru in care exista semnal util, aplicatia poate estima banda ocupata. Procesul este:
- se calculeaza FFT-ul semnalului;
- se obtine spectrul de putere;
- spectrul este netezit cu o medie mobila;
- se alege un prag pe baza unei percentile;
- se cauta primul si ultimul bin care depasesc pragul.

Frecventele corespunzatoare acestor binuri definesc marginile benzii:

$$
B = f_{max} - f_{min}
$$

iar offset-ul centrului este:

$$
f_{offset} = \frac{f_{min} + f_{max}}{2}
$$

Aceasta estimare nu este o masurare perfecta a canalului, dar este utila pentru analiza vizuala si pentru alegerea unei regiuni aproximative de procesare.

### 2.16. Scanarea unei benzi de frecventa
Un receptor RTL-SDR vede la un moment dat doar banda din jurul frecventei centrale. Pentru a inspecta o zona mai larga, aplicatia poate schimba succesiv frecventa centrala intre doua limite. Aceasta operatie este numita `sweep`.

Pentru un interval $[f_{start}, f_{stop}]$ si un pas $\Delta f$, frecventele vizitate sunt:

$$
f_k = f_{start} + k \cdot \Delta f
$$

Cand urmatorul pas ar depasi limita superioara, scanarea reincepe de la $f_{start}$. In implementarea actuala, avansul se face dupa procesarea fiecarui bloc IQ. Sweep-ul este util pentru explorare vizuala, dar nu reprezinta o captura simultana a intregului interval.

In timpul scanarii, redarea si inregistrarea audio sunt oprite automat. Motivul este simplu: fiecare schimbare de frecventa muta receptorul pe alt canal, iar un flux audio continuu nu ar mai avea sens.

## 3. Structura proiectului
```text
Software-Defined-Radio/
|-- App.py
|-- requirements.txt
|-- README.md
|
|-- backend/
|   |-- audio/
|   |   |-- audio_output.py
|   |   `-- audio_recorder.py
|   |
|   |-- demodulare/
|   |   |-- am.py
|   |   |-- fm.py
|   |   `-- modulation.py
|   |
|   |-- dsp/
|   |   |-- fft.py
|   |   |-- filters.py
|   |   |-- frequency.py
|   |   |-- resampling.py
|   |   `-- windowing.py
|   |
|   |-- pipeline/
|   |   |-- events.py
|   |   `-- pipeline.py
|   |
|   |-- receiver/
|   |   |-- base.py
|   |   |-- buffered_receiver.py
|   |   |-- config.py
|   |   |-- rtl_sdr_receiver.py
|   |   `-- synthetic_receiver.py
|   |
|   `-- signal/
|       |-- buffers.py
|       `-- models.py
|
|-- config/
|   |-- current.py
|   `-- defaults.py
|
|-- frontend/
|   |-- audio_diagnostics_dialog.py
|   |-- controls_panel.py
|   |-- main_window.py
|   |-- spectrum_view.py
|   `-- waterfall_view.py
|
|-- tests/
`-- profile_pipeline_timing.py
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
- `BufferedReceiver` - wrapper cu thread dedicat si coada IQ limitata pentru receptia live;
- `SyntheticReceiver` - sursa IQ determinista pentru dezvoltare si teste automate.

### 4.5. `Backend/Audio`
Contine iesirea si inregistrarea audio.

- `AudioOutput` - gestioneaza coada audio, callback-ul `sounddevice`, selectia iesirii audio, compensarea optionala a diferentei dintre ceasuri si telemetria de playback.
- `AudioRecorder` - salveaza esantioanele audio demodulate intr-un fisier WAV mono.

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
- `Audio_diagnostics_dialog.py` - popup pentru inspectarea cozii audio, cozii IQ si a incidentelor de playback.

## 5. Fluxul aplicatiei
```text
RTL-SDR
   |
   v
RtlSdrReceiver -> BufferedReceiver -> coada IQ
   |
   v
IQBlock
   |
   v
SDRPipeline
   |-- demodulare AM/FM -> AudioBlock -> AudioOutput / AudioRecorder
   |
   `-- FFT + normalizare -> SpectrumFrame -> Spectrum/Waterfall UI
```

Pipeline-ul este singurul strat care leaga componentele intre ele. Modulele DSP raman independente si pot fi testate separat cu semnale generate artificial.

Pentru sursa RTL-SDR, `BufferedReceiver` citeste blocurile IQ intr-un thread dedicat si pastreaza o coada limitata. Astfel, intarzierile scurte din DSP sau din interfata grafica nu intrerup imediat alimentarea audio. Fereastra `Audio diagnostics` afiseaza rezerva curenta prin campul `Queued IQ`.

## 6. Threading si concurenta
Aplicatia proceseaza date in timp real. Citirea dongle-ului, DSP-ul, randarea interfetei si consumul placii audio nu trebuie sa se blocheze reciproc. Din acest motiv sunt folosite mai multe thread-uri si doua cozi intermediare.

### 6.1. Privire de ansamblu
Fluxul concurent poate fi rezumat astfel:

```text
Thread GUI Qt
   ^                                   |
   | semnale Qt                        | comenzi utilizator
   |                                   v
SDRPipelineWorker (QThread): setari -> DSP -> AudioOutput.play()
   ^                                      |
   | IQBlock                              | AudioBlock
   |                                      v
coada IQ                            coada audio
   ^                                      |
   |                                      v
thread rtl-sdr-reader              callback PortAudio / WASAPI
   ^
   |
dongle RTL-SDR
```

### 6.2. Thread-ul GUI
Thread-ul principal Qt construieste fereastra, proceseaza interactiunile utilizatorului si actualizeaza spectrul, waterfall-ul si dialogul `Audio diagnostics`. El nu citeste direct dongle-ul si nu executa pipeline-ul DSP.

Worker-ul trimite date catre GUI prin semnale Qt:
- `frame_ready` pentru actualizarea spectrului si waterfall-ului;
- `audio_telemetry_ready` pentru diagnosticarea playback-ului;
- `frequency_changed` pentru sincronizarea frecventei afisate;
- `recording_started`, `recording_stopped` si `error` pentru mesaje de stare.

Pentru reducerea costului de randare, spectrul si waterfall-ul sunt actualizate doar pentru un bloc din patru. Procesarea audio continua pentru fiecare bloc IQ.

### 6.3. Worker-ul DSP
`SDRPipelineWorker` mosteneste `QThread`. El coordoneaza fluxul principal:
- aplica setarile schimbate din interfata;
- consuma un `IQBlock`;
- executa translatarea in frecventa, filtrarea, resampling-ul si demodularea;
- trimite esantioanele catre `AudioOutput`;
- scrie optional acelasi `AudioBlock` intr-un fisier WAV;
- calculeaza periodic FFT-ul pentru interfata;
- masoara durata buclei si emite telemetrie.

Setarile partajate sunt protejate printr-un `Lock`, deoarece thread-ul GUI poate modifica valorile in timp ce worker-ul ruleaza.

### 6.4. Thread-ul de achizitie RTL-SDR
Citirea USB poate avea variatii de durata. Daca DSP-ul ar apela direct `RtlSdrReceiver.read_block()`, o citire lenta ar opri temporar producerea audio.

Pentru sursa hardware, `RtlSdrReceiver` este impachetat intr-un `BufferedReceiver`. Acesta porneste thread-ul daemon `rtl-sdr-reader`, care citeste continuu blocuri IQ si le introduce intr-un `Queue` limitat:

```text
RtlSdrReceiver.read_block() -> Queue[IQBlock] -> SDRPipelineWorker
```

Implicit, coada pastreaza maximum `8` blocuri. Pentru `block_size = 32_768` si `sample_rate = 1_024_000`, rezerva maxima este aproximativ:

$$
T_{IQ} = 8 \cdot \frac{32768}{1024000} = 0.256 \text{ s}
$$

Coada limitata previne cresterea nelimitata a memoriei. La schimbarea frecventei centrale, blocurile vechi sunt eliminate. `BufferedReceiver` foloseste si o generatie interna pentru ca un bloc citit inainte de retuning sa nu ajunga accidental in pipeline dupa schimbarea frecventei.

### 6.5. Callback-ul audio
`sounddevice.OutputStream` ruleaza callback-ul audio intr-un thread administrat de PortAudio. Callback-ul trebuie sa ramana scurt: extrage esantioane din coada `AudioOutput`, aplica doar ajustarea discreta necesara pentru clock drift si copiaza rezultatul in buffer-ul placii audio.

Accesul la coada audio este protejat printr-un `Lock`, deoarece worker-ul DSP produce esantioane in timp ce callback-ul le consuma.

### 6.6. Oprirea controlata
Oprirea aplicatiei foloseste obiecte `Event`:
- `SDRPipelineWorker.request_stop()` seteaza evenimentul worker-ului si inchide receiver-ul;
- `BufferedReceiver.close()` seteaza evenimentul reader-ului, inchide receptorul hardware si asteapta terminarea thread-ului;
- `AudioOutput.close()` opreste stream-ul PortAudio si goleste coada audio;
- recorder-ul WAV este inchis pentru finalizarea corecta a fisierului.

Aceasta ordine reduce riscul ca un thread sa continue sa foloseasca dispozitivul USB sau placa audio dupa inchiderea aplicatiei.

### 6.7. Diagnosticarea concurentei
Popup-ul `Audio diagnostics` ajuta la separarea cauzelor:
- `Queued IQ` scazut indica faptul ca reader-ul RTL-SDR nu alimenteaza suficient coada IQ;
- `Maximum SDR loop` ridicat indica un blocaj sau un cost DSP/UI prea mare;
- `Audio production` sub `48_000 S/s` indica faptul ca worker-ul produce prea putin audio;
- `Queued audio` scazut si `Underruns` in crestere indica faptul ca placa audio consuma mai repede decat este alimentata.

## 7. Dependente
Dependentele proiectului sunt definite in `requirements.txt`:

```text
numpy
scipy
pyrtlsdr[lib]
sounddevice
PySide6
pyqtgraph
pytest
```

`pytest` este folosit doar pentru testare. Celelalte pachete sunt necesare la rularea aplicatiei.

## 8. Setup Python
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

## 9. Configurare RTL-SDR
Pentru rularea aplicatiei cu un dongle RTL-SDR este necesara instalarea driverelor potrivite pentru sistemul de operare. Daca vrei doar sa explorezi interfata si pipeline-ul, poti sari peste aceasta etapa si poti folosi sursa `Synthetic`.

Pe Windows, dispozitivul trebuie configurat astfel incat sa poata fi accesat de libraria RTL-SDR. In mod obisnuit, acest lucru presupune instalarea driverului `WinUSB` pentru interfata corecta a dongle-ului, cu ajutorul utilitarului [Zadig](https://zadig.akeo.ie/). Zadig poate inlocui driverul unui dispozitiv USB, deci selectia trebuie verificata cu atentie inainte de instalare.

Aplicatia foloseste API-ul Python `pyrtlsdr`, dar acesta incarca in continuare o librarie nativa `librtlsdr`/`rtlsdr.dll`. Arhitectura trebuie sa se potriveasca: Python 64-bit are nevoie de DLL-uri 64-bit, iar Python 32-bit are nevoie de DLL-uri 32-bit. Instalarea recomandata este:

```powershell
python -m pip install --upgrade "pyrtlsdr[lib]"
```

Daca exista DLL-uri RTL-SDR vechi in `PATH` sau in folderul `dll/`, acestea pot fi incarcate inaintea celor bune si pot produce erori de import precum lipsa functiei `rtlsdr_set_dithering`.

Setarile importante sunt definite prin `ReceiverConfig`:
- `center_frequency`;
- `sample_rate`;
- `gain`;
- `block_size`;
- `ppm_correction` - corectia erorii de frecventa a oscilatorului dongle-ului, exprimata in parti per milion.

## 10. Rulare
Aplicatia se porneste din radacina proiectului, dupa activarea mediului virtual:

```powershell
python App.py
```

Entrypoint-ul porneste interfata grafica si conecteaza controalele la backend-ul SDR. Frontend-ul ramane simplu: trimite setarile alese de utilizator si afiseaza frame-urile primite, fara sa gestioneze direct receiver-ul sau pipeline-ul DSP.

### 10.1. Pornire rapida fara hardware
Cel mai simplu mod de a verifica instalarea este sa pornesti cu sursa sintetica:

1. Ruleaza `python App.py`.
2. In grupul `Radio`, alege `Synthetic`.
3. Pastreaza modul `fm` si apasa `Start`.
4. Urmareste spectrul si waterfall-ul.
5. Deschide `Audio diagnostics` pentru a vedea telemetria audio.

Sursa sintetica genereaza un semnal IQ determinist, modulat cu un ton audio de `1 kHz`. Nu inlocuieste testul cu dongle-ul real, dar ajuta mult cand vrei sa separi problemele de instalare, interfata si DSP de problemele USB sau de antena.

### 10.2. Utilizarea interfetei
Interfata permite:
- alegerea sursei IQ: dongle `RTL-SDR` sau sursa `Synthetic` pentru testare fara hardware;
- pornirea si oprirea pipeline-ului;
- selectarea frecventei centrale;
- selectarea ratei de esantionare;
- configurarea gain-ului manual;
- configurarea corectiei de frecventa `PPM`, inclusiv valoarea `0 ppm`;
- alegerea modului de demodulare AM/FM;
- modificarea dimensiunii FFT;
- activarea iesirii audio;
- alegerea iesirii audio sau folosirea selectiei automate;
- inregistrarea audio-ului demodulat in fisiere WAV in folderul `recordings/`;
- deschiderea ferestrei `Audio diagnostics`, care afiseaza nivelul cozii audio, underrun-urile, overrun-urile si avertizarile raportate de PortAudio;
- resetarea contoarelor din fereastra `Audio diagnostics`;
- revenirea la setarile implicite cu butonul `Reset defaults`;
- scanarea unui interval cu `Sweep`; in acest mod audio-ul si inregistrarea sunt oprite automat;
- vizualizarea spectrului si waterfall-ului in timp real.

Panoul de parametri este ascuns implicit pentru a lasa cat mai mult spatiu spectrului si waterfall-ului. Butonul hamburger din stanga frecventei deschide un drawer lateral cu toate controalele. Pe ecrane mai mici, drawer-ul poate fi derulat; la nevoie poate fi mutat, inchis sau desprins intr-o fereastra separata.

Spectrul este si un instrument de control:
- un click pe grafic muta frecventa centrala la offset-ul selectat;
- regiunea verticala semitransparenta poate fi deplasata si redimensionata pentru izolarea canalului;
- `Low offset` si `High offset` descriu marginile regiunii fata de frecventa centrala, nu frecvente radio absolute;
- un click pe spectru opreste sweep-ul activ inainte de retuning.

Setarile pentru sursa IQ, sample rate, gain, corectia PPM si iesirea audio sunt blocate cat timp pipeline-ul ruleaza. Frecventa, FFT-ul, regiunea de izolare, sweep-ul, audio-ul si inregistrarea pot fi ajustate in timpul rularii.

Aplicatia salveaza automat ultimele setari cu `QSettings` si le restaureaza la urmatoarea pornire. Astfel, frecventa, sursa, PPM-ul, iesirea audio si preferintele de afisare nu trebuie reintroduse la fiecare sesiune. Daca setarile ajung intr-o stare nepotrivita, `Reset defaults` sterge valorile salvate si readuce panoul la configuratia initiala.

## 11. Depanare
Cand ceva nu functioneaza, incepe cu sursa `Synthetic`. Daca aceasta produce spectru si audio, partea software de baza este in regula, iar investigatia se poate muta spre dongle, driver, USB sau antena.

| Simptom | Ce merita verificat prima data |
| --- | --- |
| Aplicatia nu porneste | Activeaza mediul virtual si ruleaza `python -m pip install -r requirements.txt`. |
| Sursa `Synthetic` functioneaza, dar `RTL-SDR` nu porneste | Verifica driverul `WinUSB`, DLL-urile `librtlsdr` si faptul ca dongle-ul nu este folosit de alta aplicatie. |
| Apare o eroare despre `rtlsdr_set_dithering` | Este probabil incarcata o versiune veche sau incompatibila de `rtlsdr.dll`. Verifica DLL-urile locale si cele din `PATH`. |
| Apare `invalid param` cand PPM este `0` | In versiunea curenta, `0 ppm` este tratat ca valoare implicita si nu mai este trimis explicit catre driver. Daca eroarea persista, reporneste aplicatia dupa `Reset defaults` si verifica DLL-ul RTL-SDR folosit. |
| Spectrul apare, dar sunetul se intrerupe | Deschide `Audio diagnostics` si urmareste `Queued audio`, `Underruns`, `Audio production`, `Queued IQ` si `Maximum SDR loop`. |
| Nu se aude nimic | Verifica daca `Enable audio` este activ, daca sweep-ul este oprit si alege explicit iesirea dorita din lista `Audio output`. |
| O statie apare deplasata fata de frecventa asteptata | Ajusteaza gradual valoarea `PPM correction` pana cand semnalul este centrat corect. |
| Inregistrarea nu porneste | Opreste sweep-ul; inregistrarea WAV este dezactivata automat in timpul scanarii. |
| Receptia este slaba sau zgomotoasa | Verifica frecventa, gain-ul, antena si latimea regiunii de izolare. |

### 11.1. Problema cu driverul / libraria RTL-SDR
In timpul integrarii cu dongle-ul RTL-SDR au aparut probleme legate de accesul la dispozitiv si de librariile native folosite de `pyrtlsdr`. Aceste probleme sunt normale pe Windows cand driverul USB, DLL-urile si pachetul Python nu sunt perfect aliniate.

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
- reducerea riscului de stare instabila prin inchiderea receiver-ului daca initializarea esueaza;
- tratarea valorii `0 ppm` ca valoare implicita, fara apel explicit la setter-ul `freq_correction`, deoarece unele combinatii de librarii RTL-SDR pot raporta `invalid param` pentru aceasta scriere.

Pasi ramasi de verificat:
- testarea dongle-ului cu un utilitar extern, de exemplu `rtl_test`, pentru a confirma ca driverul si dispozitivul functioneaza independent de aplicatie;
- verificarea portului USB si evitarea hub-urilor USB daca apar erori intermitente de tip `LIBUSB_ERROR_IO`;
- incercarea unei dimensiuni mai mici pentru `block_size`, daca eroarea apare la citiri mari.

### 11.2. Problema cu sunetul / iesirea audio
Zona de redare audio are propriile capcane, deoarece semnalul demodulat trebuie livrat placii de sunet intr-un ritm constant prin `sounddevice`.

Simptome posibile:
- aplicatia ruleaza si proceseaza semnalul, dar nu se aude nimic;
- audio-ul poate fi intrerupt sau instabil daca pipeline-ul produce esantioane intr-un ritm diferit fata de consumul placii de sunet;
- pot aparea erori daca `sounddevice` nu este instalat corect sau daca backend-ul audio al sistemului nu este disponibil.

Ce s-a incercat pana acum:
- folosirea `sounddevice.OutputStream` cu un callback audio dedicat;
- conversia esantioanelor la `float32`, format potrivit pentru iesirea audio;
- limitarea semnalului audio in intervalul `[-1.0, 1.0]` pentru a evita clipping-ul excesiv;
- introducerea unui buffer intern bazat pe coada, astfel incat callback-ul audio sa poata consuma esantioane fara sa depinda direct de viteza pipeline-ului;
- eliminarea asteptarilor artificiale din thread-ul de achizitie IQ si refacerea prebuffer-ului audio dupa un underrun, inainte ca redarea sa fie reluata;
- adaptarea pragului de reluare dupa un underrun la cel putin doua callback-uri audio reale, pentru evitarea ciclurilor repetate de rebuffering;
- limitarea actualizarilor grafice la un frame din patru, fara reducerea cadentei audio, pentru a lasa mai mult timp thread-ului de achizitie SDR;
- folosirea unui prebuffer audio initial de `500 ms` si a unei tinte de coada de `400 ms`, pentru absorbtia variatiilor scurte de debit;
- compensarea lenta a diferentei dintre ceasul RTL-SDR si ceasul placii audio, prin ajustarea discreta a numarului de esantioane consumate de callback;
- folosirea iesirii audio implicite a sistemului in modul `Automatic` si posibilitatea selectarii explicite a unui device;
- folosirea unui bloc audio fix de `1024` esantioane si a profilului de latenta `high` pentru stabilitate;
- pastrarea iesirii audio pe un singur canal (`channels=1`) si sample rate audio standard de `48_000` Hz;
- separarea citirii RTL-SDR intr-un thread dedicat prin `BufferedReceiver`, cu o coada IQ limitata care absoarbe intarzierile scurte ale DSP-ului sau ale interfetei grafice;
- adaugarea ferestrei `Audio diagnostics` pentru inspectarea in timp real a debitului audio, cozii IQ, cozii audio si incidentelor de playback.

Pasi ramasi de verificat:
- listarea dispozitivelor audio disponibile in `sounddevice` si alegerea explicita a dispozitivului corect, daca sistemul are mai multe iesiri;
- verificarea ratei audio finale dupa demodulare si resampling, ca sa ramana compatibila cu `48_000` Hz;
- testarea pipeline-ului audio cu un semnal generat software, separat de receptorul RTL-SDR, pentru a izola problema de partea radio.

Pentru listarea dispozitivelor si backend-urilor audio disponibile:

```powershell
python -m sounddevice
```

## 12. Functionalitati implementate
- Modele de date pentru blocuri IQ, audio si spectru.
- Functii pure pentru FFT, putere, normalizare spectru si spectrograma.
- Functii pure pentru eliminare DC, moving average si normalizare RMS.
- Estimare de banda ocupata si shift de frecventa.
- Demodulare AM.
- Demodulare FM.
- Modulare AM.
- Contract abstract pentru receptoare.
- Implementare RTL-SDR.
- Wrapper `BufferedReceiver` cu thread dedicat pentru achizitia IQ live.
- Sursa IQ sintetica pentru teste si dezvoltare fara hardware.
- Iesire audio prin `sounddevice`.
- Playback audio cu coada, prebuffer, selectie de device, compensare optionala de clock drift si telemetrie.
- Pipeline SDR pentru procesarea unui frame complet.
- Interfata grafica desktop cu panou de control, spectrum view si waterfall view.
- Popup `Audio diagnostics`.
- Buton pentru resetarea contoarelor de diagnostic audio.
- Selector pentru iesirea audio, cu mod automat si selectare explicita.
- Corectie PPM configurabila pentru dongle-ul RTL-SDR.
- Tratament special pentru `0 ppm`, care pastreaza valoarea implicita a driverului si evita erorile native de tip `invalid param`.
- Persistenta setarilor intre sesiuni prin `QSettings`.
- Resetarea setarilor salvate la configuratia implicita.
- Inregistrare WAV pentru semnalul demodulat, inclusiv cand este activa regiunea de izolare.

## 13. Testare
Proiectul include `31` de teste automate `pytest`. Rulare:

```powershell
python -m pytest -q
```

### 13.1. Teste DSP
Fisier: `tests/test_dsp.py`

- verifica dimensiunea FFT-ului si normalizarea spectrului in intervalul `[0, 1]`;
- verifica raportul dintre numarul de esantioane de intrare si iesire dupa resampling;
- verifica faptul ca `StreamingResampler` nu modifica semnalul cand rata sursa este egala cu rata tinta.

### 13.2. Teste de demodulare
Fisier: `tests/test_demodulation.py`

- verifica recuperarea anvelopei unui semnal AM;
- verifica recuperarea diferentei constante de faza pentru un ton FM.

### 13.3. Teste pentru pipeline
Fisier: `tests/test_pipeline.py`

- proceseaza un frame complet folosind `SyntheticReceiver`;
- verifica actualizarea frecventei centrale pentru sursa sintetica;
- verifica omiterea FFT-ului fara intreruperea producerii audio;
- verifica filtrul audio FM mono la `15 kHz`;
- verifica filtrarea canalului FM chiar si cand regiunea vizuala de izolare este dezactivata;
- verifica reducerea distorsiunii discriminatorului FM prin DC blocker-ul IQ.

### 13.4. Teste pentru playback si recorder
Fisier: `tests/test_audio_output.py`

- verifica scrierea fisierelor WAV mono;
- verifica ordinea esantioanelor consumate din coada audio;
- verifica recuperarea dupa underrun;
- verifica asteptarea unei rezerve suficiente inainte de reluarea playback-ului;
- verifica compensarea optionala a diferentei mici dintre ceasul SDR si ceasul placii audio;
- verifica faptul ca playback-ul implicit nu resampleaza callback-ul cand coada este plina;
- verifica folosirea iesirii audio implicite in modul `Automatic`;
- verifica utilizarea blocului fix de `1024` esantioane si a profilului stabil de latenta;
- verifica telemetria afisata in popup-ul `Audio diagnostics`.

### 13.5. Teste pentru receiver-ul bufferizat
Fisier: `tests/test_buffered_receiver.py`

- verifica ordinea blocurilor IQ citite prin `BufferedReceiver`;
- verifica limita cozii IQ si durata raportata;
- verifica eliminarea blocurilor vechi dupa schimbarea frecventei centrale.

### 13.6. Teste pentru configurare si interfata
Fisiere: `tests/test_rtl_sdr_receiver.py` si `tests/test_controls_panel.py`

- verifica aplicarea corectiei PPM catre driverul RTL-SDR;
- verifica faptul ca `0 ppm` nu este trimis explicit catre driver, pentru a evita eroarea nativa `invalid param`;
- verifica restaurarea setarilor salvate cu `QSettings`;
- verifica restaurarea iesirii audio selectate;
- verifica resetarea setarilor salvate la valorile implicite;
- verifica eticheta sursei afisate in status bar.

### 13.7. Verificari manuale cu hardware
Testele automate nu pot valida complet dongle-ul fizic, driverul USB sau calitatea perceputa a sunetului. Verificarea manuala recomandata:

- conectarea dongle-ului RTL-SDR si rularea `python App.py`;
- reglarea frecventei, gain-ului si regiunii de izolare;
- compararea playback-ului live cu fisierul WAV inregistrat;
- inspectarea ferestrei `Audio diagnostics`;
- verificarea valorilor `Queued audio`, `Underruns`, `Overruns`, `Audio production`, `Queued IQ` si `Maximum SDR loop`;
- rularea unui utilitar extern precum `rtl_test` daca apar erori USB.

## 14. Profilarea pipeline-ului
Fisierul `profile_pipeline_timing.py` masoara timpul consumat de fiecare etapa: citire IQ, pregatirea intrarii pentru demodulare, resampling, filtre audio, conditionare si FFT.

Pentru o masurare repetabila fara dongle:

```powershell
python profile_pipeline_timing.py --source synthetic --frames 100
```

Pentru o masurare cu receptorul fizic:

```powershell
python profile_pipeline_timing.py --source rtl --frequency 100600000 --frames 100
```

Raportul compara timpul mediu al buclei cu durata radio a unui bloc IQ. Daca utilizarea ajunge aproape de `100%`, pipeline-ul nu mai are suficienta rezerva pentru variatii de timp si pot aparea intreruperi audio.

## 15. Limite actuale si directii de extindere
Aplicatia este un receptor SDR educational functional, nu un inlocuitor complet pentru aplicatii mature precum SDRSharp. In forma actuala:

- FM-ul este redat mono; decoder-ul stereo si RDS nu sunt implementate;
- AM foloseste detectie simpla de anvelopa;
- sweep-ul inspecteaza frecventele secvential si nu construieste inca o panorama persistenta;
- sample rate-ul si gain-ul nu se schimba in timpul rularii;
- testele automate nu pot valida driverul USB, antena sau calitatea audio perceputa.

Extinderile naturale sunt memorii de frecventa, export de capturi IQ, o panorama pentru sweep si demodulatoare suplimentare.

## 16. Referinte si documentatie externa
Referintele de mai jos sunt utile pentru instalare, depanare si intelegerea bibliotecilor folosite in proiect. Legaturile online au fost verificate la `4 iunie 2026`.

- [pyrtlsdr - repository oficial](https://github.com/pyrtlsdr/pyrtlsdr) - instalare, utilizarea `pyrtlsdr[lib]`, dependenta de `librtlsdr` si compatibilitatea DLL-urilor pe Windows;
- [librtlsdr - proiect upstream](https://github.com/steve-m/librtlsdr) - implementarea de baza pentru dongle-uri RTL2832U;
- [Zadig - pagina oficiala](https://zadig.akeo.ie/) - instalarea driverelor USB generice pe Windows, inclusiv `WinUSB`;
- [NumPy FFT](https://numpy.org/doc/stable/reference/routines.fft.html) - transformata Fourier discreta si utilitarele folosite pentru axa de frecventa;
- [SciPy Signal](https://docs.scipy.org/doc/scipy/reference/signal.html) - filtre Butterworth, filtre IIR si procesarea digitala a semnalului;
- [SciPy `resample_poly`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html) - resampling rational polifazic folosit de pipeline;
- [python-sounddevice](https://python-sounddevice.readthedocs.io/) - `OutputStream`, callback-uri, dispozitive audio si host API-uri;
- [Qt for Python - `QThread`](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html) - executia worker-ului DSP intr-un thread separat si comunicarea prin semnale Qt;
- [pyqtgraph - `LinearRegionItem`](https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/linearregionitem.html) - regiunea interactiva folosita pentru izolarea unui canal;
- [pytest](https://docs.pytest.org/) - rularea testelor automate.

## 17. Ce am invatat din proiect
Proiectul a pornit de la o idee simpla: sa receptioneze un semnal radio si sa il redea ca audio. In practica, a devenit clar ca un receptor SDR este un lant de etape care trebuie sa tina pasul una cu alta, in timp real. O problema mica intr-un singur loc poate ajunge rapid sa se vada in spectru sau sa se auda in difuzoare.

### 17.1. Legatura dintre teoria DSP si un semnal real
Reprezentarea IQ nu ramane doar o formula din teorie. In aplicatie, ea permite pastrarea amplitudinii si fazei, mutarea digitala a unui canal si demodularea FM prin diferenta de faza dintre esantioane. FFT-ul, fereastra Hann si waterfall-ul transforma aceleasi esantioane intr-o imagine pe care o poti interpreta dintr-o privire.

### 17.2. Filtrarea trebuie gandita ca un lant
Un singur filtru nu rezolva tot. Pentru FM au fost necesare izolarea canalului, reducerea componentei DC din IQ, filtrarea audio, eliminarea pilotului stereo de `19 kHz`, limitarea benzii mono la `15 kHz` si de-emphasis. Ordinea acestor operatii conteaza, iar efectul ei se simte direct in calitatea audio.

### 17.3. Procesarea in timp real inseamna gestionarea ritmurilor diferite
Dongle-ul RTL-SDR, worker-ul DSP, interfata grafica si placa de sunet nu lucreaza dupa acelasi ceas. Coada IQ si coada audio absorb intarzierile scurte fara sa blocheze intreaga aplicatie. Telemetria a devenit aproape la fel de importanta ca sunetul, pentru ca arata unde se pierde ritmul.

### 17.4. Separarea componentelor simplifica investigarea
Sursa `Synthetic` a permis verificarea pipeline-ului fara dongle. Testele DSP folosesc semnale controlate, iar profiler-ul masoara fiecare etapa separat. Asta face diferenta dintre "cred ca problema e aici" si un diagnostic care poate fi verificat.

### 17.5. Interfata trebuie sa ajute utilizatorul sa inteleaga semnalul
Spectrul nu este doar un grafic decorativ. Click-ul pentru retuning, regiunea de izolare, resetarea setarilor si fereastra `Audio diagnostics` transforma interfata intr-un instrument de explorare. Un proiect tehnic devine mai usor de folosit cand arata informatiile importante direct in UI, nu doar in log-uri.

## 18. Dificultati intampinate
Cele mai importante dificultati nu au aparut izolat. Ele s-au influentat reciproc: o citire USB lenta poate goli coada audio, iar o actualizare grafica prea frecventa poate lasa mai putin timp pentru DSP.

### 18.1. Integrarea dongle-ului RTL-SDR pe Windows
Prima dificultate a fost accesul stabil la dispozitiv. `pyrtlsdr` este o interfata Python, dar sub ea exista librarii native si driver USB. O versiune nepotrivita de `rtlsdr.dll`, o arhitectura diferita fata de Python sau un driver USB incorect pot opri aplicatia inainte ca procesarea DSP sa inceapa.

Solutia a inclus mesaje de eroare mai clare, suport pentru un folder local `dll/`, recomandarea instalarii `pyrtlsdr[lib]`, verificarea driverului `WinUSB` si evitarea scrierii explicite a valorii `0 ppm` cand driverul nu are nevoie de ea. Detaliile de depanare sunt descrise in [sectiunea 11.1](#111-problema-cu-driverul--libraria-rtl-sdr).

### 18.2. Continuitatea audio
Redarea live a fost mai dificila decat salvarea unui fisier WAV. Recorder-ul poate scrie blocuri atunci cand acestea sosesc, dar placa de sunet cere periodic un numar exact de esantioane. Daca pipeline-ul intarzie, apare un `underrun`.

Pentru stabilizare au fost introduse prebuffer-ul, reluarea controlata dupa underrun si o coada audio limitata. Valorile pot fi urmarite si resetate in fereastra `Audio diagnostics`, iar iesirea audio poate fi aleasa explicit din interfata. Modul `Automatic` foloseste iesirea implicita a sistemului pentru a evita schimbarea neasteptata a backend-ului audio.

### 18.3. Continuitatea semnalului intre blocuri
Procesarea pe blocuri este eficienta, dar poate crea discontinuitati artificiale. Pentru FM, ultimul esantion din blocul anterior trebuie pastrat pentru discriminator. Pentru translatarea in frecventa trebuie pastrata faza oscilatorului numeric, iar resampling-ul are nevoie de stare intre apeluri.

Aceasta dificultate a aratat de ce un algoritm care merge perfect pe un vector izolat nu este automat corect intr-un flux continuu.

### 18.4. Echilibrul dintre afisare si procesare
FFT-ul si actualizarea waterfall-ului sunt utile, dar au un cost. Pentru a proteja traseul audio, interfata este actualizata doar pentru un bloc IQ din patru. Pipeline-ul continua sa demoduleze fiecare bloc.

### 18.5. Testarea fara dependenta permanenta de hardware
Dongle-ul fizic, driverul, antena si mediul radio nu sunt reproductibile intr-un test automat. Din acest motiv a fost adaugat `SyntheticReceiver`, iar testele valideaza separat demodularea, filtrele, pipeline-ul, callback-ul audio si receiver-ul bufferizat. Testarea manuala cu hardware ramane necesara pentru validarea finala.
