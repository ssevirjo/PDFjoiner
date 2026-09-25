# PDF Dokumentu Apvienotājs (PDF, DOCX, JPG / PNG)

Lietotne vairāk nekā 20 dažādu formātu dokumentu ātrai un kvalitatīvai apvienošanai vienā kopīgā PDF dokumentā ar ērtu secības pārvaldību un **100% latviešu valodas diakritikas un teksta saglabāšanu** (*ā, č, ē, ģ, ī, ķ, ļ, ņ, š, ū, ž*).

---

## 🌟 Galvenās iespējas un priekšrocības

1. **Visu populāro formātu atbalsts:**
   - **PDF:** tieša vektoru un lapu straumju kopēšana bez atkārtotas saspiešanas un bez teksta rasterizācijas (`PyMuPDF`). Visi oriģinālie fonti un latviešu valodas burti saglabājas pilnībā, un teksts gala PDF dokumentā ir iezīmējams un meklējams.
   - **DOCX / DOC:** tieša konvertēšana, izmantojot Microsoft Word dzinēju (COM API) — nodrošina precīzu oriģinālo izkārtojumu, tabulas, kolonnas un fontus.
   - **Attēli (JPG, JPEG, PNG, WEBP):** automātiska pielāgošana standarta A4 lapas formātam (automātisks portrets vai ainava atkarībā no attēla) vai sākotnējās izšķirtspējas saglabāšana.

2. **Pārdomāta secības pārvaldība:**
   - **Vilkšana un nomešana (Drag & Drop):** vienkārši velciet kartītes ar peli, turot aiz roktura `⠿`, lai brīvi mainītu dokumentu secību.
   - **Bultiņu pogas:** pogas `▲ Pārvietot uz augšu` un `▼ Pārvietot uz leju` katrai kartītei.
   - **Ātrā kārtošana:** pogas «Nosaukums A-Z», «Nosaukums Z-A», «Apgriezt secību».
   - **Priekšskatījums:** katram dokumentam redzama pirmās lapas miniatūra un pieejams pilna izmēra lappušu priekšskatījuma logs.
   - **Lappušu atlase:** iespēja apvienot visu dokumentu vai norādīt konkrētas lapas (piemēram, `1-3, 5`).

3. **Pārnēsājams (Portable) EXE fails bez instalācijas:**
   - Izveidots patstāvīgs fails **`PDF_Dokumentu_Apvienotajs.exe`**, kuram **nav nepieciešams instalēt Python vai papildu bibliotēkas**.
   - Darbojas uz jebkura Windows 10 un Windows 11 datora.

---

## 🚀 Kā palaist programmu

### 1. variants (Visērtākais — jebkurā datorā):
Vienkārši veiciet dubultklikšķi uz faila:
👉 **`PDF_Dokumentu_Apvienotajs.exe`**

Programma atvērsies kā ērts darbvirsmas logs vai jūsu noklusējuma pārlūkprogrammā.

### 2. variants:
Veiciet dubultklikšķi uz **`Palaist_PDF_Apvienotaju.bat`** vai **`start.cmd`**.

---

## 📁 Failu struktūra

- **`PDF_Dokumentu_Apvienotajs.exe`** — autonoms pārnēsājams programmas izpildāmais fails (nav vajadzīgs Python).
- **`Palaist_PDF_Apvienotaju.bat`** / **`start.cmd`** — palaišanas komandfaili.
- **`app.py`** un **`converter.py`** — servera un dokumentu apstrādes pirmkods.
- **`static/`** — lietotāja saskarnes faili (HTML, CSS, JS) ar tumšo un gaišo motīvu.
- **`output/`** — mape, kurā tiek saglabāti izveidotie apvienotie PDF dokumenti.
