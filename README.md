# Ellátásbiztonsági figyelő v3 · magyar / európai monitoring

Nyilvános GitHub Pages oldal, **3 óránként futó** adatgyűjtéssel és **feltételes Gmail e-mail-riasztással**. Az alkalmazás valós adatokat használ, de **nem ad hiteles százalékos eseményvalószínűségeket**. A 0–100 index *nem %*. A 50 pontos riasztási határ nem jelent 50% esélyt.

## Frissítés meglévő GitHub repositoryban

1. A ZIP **fájljait és mappáit közvetlenül** a `gyoriddani/aramellatas-figyelo` repo **gyökerébe** töltsd fel; ne hozz létre új `aramellatas-figyelo` almappát. A `.github/workflows/daily.yml` rejtett mappát is frissítsd. (A régi workflow-t ugyanazzal az útvonallal cserélje az új.)
2. Az `index.html`, `app.js`, `style.css` a repo tetején legyen; `scripts/*.py`, `data/*.json` és `.github/workflows/daily.yml` maradjon a megadott mappákban.
3. GitHub → **Settings → Actions → General** → **Workflow permissions** → **Read and write permissions** (ha az Actions nem tudja a `data/latest.json`-t visszaírni). Mentsd el. A repó **Settings → Pages** továbbra is `main` / `/(root)`.
4. **Actions → Automatikus ellátásbiztonsági figyelés és e-mail → Run workflow**. Ellenőrizd a zöld pipát; nézd meg a `data/latest.json` és az `assessment` mező megjelenését. A GitHub `schedule` késhet, nem 24/7 valós idejű szolgáltatás.
5. A weboldal 3 publikus API-t kérdezhet le külön, a böngészőből a **Frissítés most** gombbal. A **teljes 13 kategóriás számítás és e-mail** csak a GitHub Actions munkafolyamat után frissül; a honlapon erre közvetlen Actions-link van.

## E-mail beállítás (nem küld levelet beállítás nélkül!)

A GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**.

Három secretet adj hozzá (a név pontos legyen):

| Secret neve | Érték |
|---|---|
| `SMTP_USER` | A küldő Gmail-cím, pl. `gyoriddani@gmail.com` |
| `SMTP_APP_PASSWORD` | A küldő Google-fiókjában létrehozott **alkalmazásjelszó**, NEM a Gmail-belépési jelszó. Általában kétlépcsős azonosítás kell; egyes fiókoknál nem elérhető. |
| `ALERT_TO` | `gyoriddani@gmail.com` |

Az alkalmazásjelszót **soha ne írd kódba, README-be, chatüzenetbe vagy nyilvános repo-fájlba**. Gmail SMTP: `smtp.gmail.com:465`, TLS. A heti/havi GitHub Actions-korlátok, ütemezési késések és levélküldési korlátok érvényesek. Ha a három secret hiányzik, a rendszer **nem küld e-mailt**, ezt a futási napló jelzi.

Küszöb: **legalább 50/100 figyelőindex** a következő 24 órán belül; egy kategóriáról legfeljebb 24 óránként ismétel, kivéve ha a pontszám emelkedik. A küldött riasztások időbélyegét a `data/alert_state.json` tárolja. Hibás SMTP-küldés esetén nem jelöl kiküldöttnek semmit.

### Opcionális energia API-kulcsok

- `GIE_API_KEY`: GIE AGSI+ ingyenes fiókból saját API-kulcs. **HU gáztároló-töltöttség**, önmagában nem rövid távú gázellátási kockázat.
- `ENTSOE_API_TOKEN`: ENTSO-E Transparency API hozzáféréshez igényelt token. **Magyar villamosenergia-fogyasztás day-ahead előrejelzés**, nem ellátási megfelelőség. Ezek hiánya esetén `Nincs adat` látszik, nem 0%.

## 13 kategória és a módszertan

Helyi áramszünet, országos blackout, európai áramellátási zavar, kibertámadás, internet/kommunikáció, élelmiszerellátás, üzemanyag, gázellátás, terror, háború, államcsőd/pénzügyi válság, extrém időjárás és geomágneses vihar.

- Open-Meteo **24 órás időjárási kitettség**: legmagasabb óránkénti széllökés/hó/intenzív csapadék/fagy szabályalapú pontszáma, plusz kombinált hatás; helyi hálózati **kitettség** indikátora, nem áramszünet-esély. Forrás: `scripts/assess.py` → `weather_score`.
- NOAA SWPC: előrejelzett **Kp** alapján 0/40/55/70/90/100 index, kizárólag a **geomágneses vihar** kategóriában; nem blackout-valószínűség.
- Hivatalos, **kézzel ellenőrzött** közlemények: `data/official_alerts.json` fájlba felvihető aktív, forráshivatkozással rendelkező figyelmeztetés. A közlemény súlyossági szintje (information/warning/severe/emergency) 20/55/75/95 pont. Ez **figyelmeztetés súlyossága**, NEM esemény bekövetkezési valószínűsége. Alapesetben üres lista, nem állítjuk, hogy automatikusan igazoltuk a közleményeket.
- A többi kategória ellenőrzött hivatalos közlemény hiányában **N/A / Nem becsülhető**. **Nem tekintjük nulla kockázatnak**.
- Az overall index a rendelkezésre álló 24 órás kategóriák **maximuma**, mellette a lefedettség (pl. 3/13). Nem átlagolt „katasztrófavalószínűség”.
- Nem adunk pontot a nem bizonyított ok-okozati összefüggéseknek: Apocalypse EWS, GDELT, áramár, GDACS hírek, repülőforgalom nem lesz terror-/háború-/blackout-jóslat.

Példa kézi, valóban ellenőrzött hivatalos értesítésre (`data/official_alerts.json`):

```json
{
 "alerts": [{
   "category":"fuel",
   "severity":"warning",
   "title":"Hivatalosan bejelentett ellátási figyelmeztetés",
   "url":"https://example.gov.hu/hivatalos-kozlemeny",
   "scope":"Magyarország",
   "start_at":"2026-11-17T12:00:00+01:00",
   "expires_at":"2026-11-18T12:00:00+01:00",
   "verified":true
 }]
}
```

**Példa – ne másold be valós eseményként.** A `url` kizárólag illusztráció. Ellenőrizd a dátumokat, hivatalos forrást, földrajzi vonatkozást és azt, hogy tényleg aktív figyelmeztetésről van szó. Ne állítsd `verified:true`-ra automatikus híralapú találat alapján.

## Adatforrások (élő és hivatkozásos)

**Automatikusan gyűjtött, ha elérhető:** Open-Meteo, Energy-Charts (HU + európai országok), NOAA SWPC, Meteoalarm országos Atom-hírfolyamok, Európai Bizottság RSS, GDACS RSS, EWS publikus JSON. **Opcionális kulccsal:** GIE AGSI+ / ENTSO-E Transparency. A gyűjtő Pythonból GitHub Actions alatt dolgozik, mert böngészőből egyes API-k CORS miatt nem olvashatók.

**Egyelőre csak ellenőrzőlink:** OPUS TITÁSZ, VÉSZ, MAVIR/ENTSO-E STA, ENTSOG, IODA, Cloudflare Radar, ENISA, Europol, EU ERCC, ECB, EU agrárpiaci oldal, Flightradar24, GDELT. Az oldalak megjelenítése **nem jelent valós idejű adatkapcsolatot**. A hivatalos TSO/STA hatáselemzésre nincs igazolt, kulcs nélkül elérhető, megbízható automatikus feedünk.

**Hiteles, minden kategóriára kiterjedő 24 órás eseményesély (%) nem állítható elő ezekből a forrásokból.** Ahhoz címkézett történeti események, validált előrejelző modell, megbízhatósági és kalibrációs vizsgálat kell.

## Helyi tesztek

```bash
python -m unittest discover -s tests -v
python scripts/collect.py      # internet szükséges
python scripts/assess.py
python scripts/notify.py       # csak beállított Secrets + küszöb esetén küld levelet
python -m http.server 8000
```

A `data/latest.json` alapból üres, tehát az első sikeres Actions-futtatásig **N/A** látható; nem adunk kitalált élő adatot.
