# Ellátásbiztonsági figyelő V4.1 – Nyíregyháza és Európa

**Állapot:** használható, de korlátozott kockázatfigyelő. Nem hiteles, kalibrált katasztrófa- vagy áramszünet-valószínűségi modell. A 0–100 index **nem százalék**. Hiányzó adat = **nem becsülhető**, nem nulla kockázat.

## Frissítés a már működő GitHub Pages weboldaladon

1. Töltsd le a V4 ZIP-et, majd **bontsd ki**.
2. A kicsomagolt fájlokat és mappákat **közvetlenül** a meglévő `gyoriddani/aramellatas-figyelo` repository **gyökerébe** töltsd fel. **Ne csinálj új `aramellatas-figyelo-v4` almappát.** Az `index.html` közvetlenül a gyökérben legyen.
3. GitHub **Code → Add file → Upload files**. Az azonos nevű fájlokat felül kell írni. Ellenőrizd külön, hogy a rejtett `.github/workflows/daily.yml` is frissült. Ha a GitHub webes feltöltés nem tartja meg a rejtett mappát, nyisd meg az adott fájlt az editorban, és másold bele a V4-beli `daily.yml` tartalmát.
4. **Settings → Actions → General → Workflow permissions → Read and write permissions**. Erre azért lehet szükség, hogy az ütemezett futás frissítse a `data/latest.json`-t.
5. **Actions → Ellátásbiztonsági V4.1 – automatikus figyelés és e-mail → Run workflow**. Az első futás után a `data/latest.json` fájlban `assessment.windows` és `assessment.health` mezők lesznek. A weboldal ezekből rajzolja a V4-es paneleket.
6. **Settings → Pages → main / (root)** marad, mint korábban. A weboldal címe: `https://gyoriddani.github.io/aramellatas-figyelo/`.
7. **Fontos:** ha a régi, korábbi elnevezésű workflow is megmaradt a `.github/workflows` mappában, **kapcsold ki vagy töröld**, mert kettős futásokat és e-maileket eredményezhet.

### E-mail – ugyanaz a 3 GitHub Actions secret

`Settings → Secrets and variables → Actions → New repository secret`

| Name | Secret értéke |
|---|---|
| `SMTP_USER` | `gyoriddani@gmail.com` |
| `SMTP_APP_PASSWORD` | Google által generált 16 karakteres **alkalmazásjelszó** (nem a normál jelszó) |
| `ALERT_TO` | `gyoriddani@gmail.com` |

**Nem szükséges új Gmail-alkalmazásjelszót létrehoznod**, ha a V3-ban már működött. A secret értékeit semmilyen fájlba ne írd. Az API-kulcsok opcionálisak: `ENTSOE_API_TOKEN`, `GIE_API_KEY`.

A rendszer 3 óránként próbál futni UTC szerint, de a GitHub ütemezés késhet vagy kimaradhat. A **50/100 index feletti, következő 24 órás** jelzésekről az e-mail-küldés akkor történik, ha van megfelelő Gmail-beállítás és új/escalálódó jelzés; ismétlés jellemzően legfeljebb 24 óránként. **Külön e-mailt küld akkor is, ha legalább 2 fontos adatforrás kiesik**, valamint sikertelen workflow-futás esetén (ha az SMTP működik).

### Független futásfelügyelet (opcionális, ajánlott)

A GitHub Actions nem tud értesíteni saját kimaradt futásáról, ha a workflow meg sem indul. A [Healthchecks.io](https://healthchecks.io/) oldalon létrehozhatsz egy **3 órás** időközű ellenőrzést, megfelelő (~2–3 órás) türelmi idővel. A szolgáltatás által adott HTTPS **ping URL**-t GitHub Actions secretbe teheted:

`HEALTHCHECKS_PING_URL` → az általad létrehozott check ping URL-je.

A workflow csak **sikeres futás után** jelez oda. Ha elmarad, a külső szolgáltatás külön értesíthet. Ez **nem kötelező**, és az URL-t ne tedd nyilvános fájlba.

## Új V4 funkciók

- **24/48/72 órás külön előrejelzési ablak:** nyíregyházi időjárási kitettség, NOAA Kp, valamint szigorúan ellenőrzött, érvényes hivatalos időjárási CAP-riasztások; ahol nincs igazolt modell/forrás, továbbra is `N/A`.
- **Meteoalarm CAP:** HU/SK/RO/AT Atom hírfolyamok alapján a program megpróbálja letölteni az eredeti CAP-üzeneteket. Csak `Actual`, nem visszavont és időben érvényes riasztásokat fogad el. Magyar *Severe/Extreme* figyelmeztetés emelheti az `extrém időjárás` kategóriaindexet, **nem** az `országos blackout` értékét. A megjelölt régió nem feltétlenül Nyíregyháza.
- **Energiapiaci és hálózati kontextus:** Energy-Charts v2 HU napi terhelési előrejelzés, HU fizikai határkeresztező áramlások és EU megújulóenergia-részarány, **ha az adott API visszaadja az adatot**. `N/A`, ha az API nem szolgáltat ilyen sorozatot. Ezek **nem** azonosak az ENTSO-E STA ellátásmegfelelőségi eredményeivel.
- **Forrásminőség:** a 6 fontos adatforrás közül hány friss; 2 vagy több kiesésnél e-mail. Az API-k hibáit a felület külön mutatja.
- **E-mail a sikertelen GitHub Actions futásról** és opcionális független heartbeat a ki nem induló időzített futások észlelésére.
- **Történeti visszamérés eszköz:** `scripts/backtest.py` valós eseményekre; az `data/outcomes.csv` szándékosan **üres**, tehát egyelőre **nincs mért pontosság**. A program a következő futásoktól `data/predictions.csv` fájlban gyűjti az előzetesen rögzített jelzéseket. A `scripts/backtest.py` precision, recall és téves riasztási arány mutatókat számít, ha később valóban dátumozott, előre rögzített indexekkel és kimenetekkel töltöd fel.
- **Alternatív indikátorok** (EWS, GDACS/GDELT, hálózati zavar oldalak) változatlanul kiegészítő tájékoztatók; nem bizonyított ok-okozati kapcsolat, **nem** kapnak automatikusan terror/háború/blackout-esélyt.

## Szándékos korlátok

- Az **ENTSO-E Short-Term Adequacy (STA)** modellezési szolgáltatása valós, de a géppel automatikusan felhasználható, általános nyilvános eredmény-API-t jelenleg nem igazoltuk. Ez **nincs bekötve**. Hivatalos információ: <https://www.entsoe.eu/data/opcsta/>.
- A **TITÁSZ** valós idejű térképe és a magyar **VÉSZ** riasztások hivatalos oldalak, de nincs itt igazolt, engedély nélküli, stabilan használható gépi végpont; **csak hivatkozás** a weboldalon.
- Háború, kibertámadás, terrortámadás, államcsőd, országos blackout: **nem számítunk százalékos esélyt** történeti eseményadatokon kalibrált modell nélkül; a hivatalos, manuálisan ellenőrzött közlemények továbbra is bevihetők `data/official_alerts.json` fájlban.
- A manuális „3 élő forrás frissítése” gomb a böngészőből csak 3 forrást aktualizál. A teljes kategóriaelemzést, CAP-feldolgozást és e-mailt a **GitHub Actions** futtatja. Ezt az **Actions → Run workflow** gomb indítja kézzel.
- Az adatok és a számítások szerveroldali külső API-hívásait ebben a készítési környezetben **nem lehetett éles hálózaton tesztelni**. A weboldal első GitHub Actions futásakor a `data/latest.json`, az `errors` mező és a futásnapló alapján ellenőrizni kell, hogy melyik API működik.
- A GitHub Pages és a GitHub Actions **nem életvédelmi riasztórendszer**. A szolgáltató, a VÉSZ és más hivatalos csatornák elsődlegesek.

## Fejlesztői teszt

```bash
python -m unittest discover -s tests -v
python scripts/collect.py  # Internetet igényel
python scripts/assess.py
python scripts/notify.py   # Csak küszöb felett és beállított SMTP-vel küld
python scripts/backtest.py # Nem lesz mérés, amíg outcomes.csv üres
python -m http.server 8000
```

2026. november 17., V4.1.

## V4.1 – adatforrás-hibák javítása (2026.11.17.)

- A NOAA SWPC 2026-ban megváltozott JSON-formátuma (objektumlista) és a régebbi listaformátum is támogatott a `collect.py` és a böngésző `app.js` részében.
- A források állapota ezentúl **failed / partial / fresh / not_configured / unavailable**. Egy frissen sikertelen lekérés nem látszik sikeresnek pusztán azért, mert korábban megmaradt egy gyorsítótárazott rekord.
- A **Forráshibák részletes összegzése** lépés a GitHub Actions **Summary** felületére írja az összes forrás státuszát és hibaüzenetét. Ezzel a következő futás után egyértelműen megállapítható, melyik API nem működik.
- Az opcionális `GIE_API_KEY` és `ENTSOE_API_TOKEN` hiánya **nem** alapkiesés; szükség van a szolgáltatóknál regisztrációra, ha tényleg használni akarod azokat.
- Nincs megváltoztatva a kockázati modellezés: a 0–100 **nem 0–100%**.

**Ellenőrzés:** GitHub Actions → V4.1 → Run workflow → Summary → *Adatforrások – részletes állapot*. Ha forráshiba van, az adott API-üzenetet (és a `data/latest.json` `errors` mezőjét) kell megvizsgálni. A zöld pipa önmagában nem bizonyít minden forrásnál sikeres lekérdezést.
