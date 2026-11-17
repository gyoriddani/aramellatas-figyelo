# Ellátásbiztonsági figyelő – Nyíregyháza

Egy statikus, magyar nyelvű webes jelzőtábla **valódi adatforrásokkal**. Nem jósolja meg a blackout pontos idejét, és **nem** közöl hamis áramszünet-százalékot.

## Gyors indítás

1. Csomagold ki a ZIP-et.
2. Helyben: a mappában futtasd `python -m http.server 8000`, és nyisd meg `http://localhost:8000`.
3. A **Frissítés most** gomb közvetlenül kéri le a nyilvános Open-Meteo, Energy-Charts és NOAA adatokat a böngészőben. A hálózati beállítások vagy CORS-korlátozás miatt előfordulhat, hogy egy részük nem elérhető; ilyenkor az adatot **nem** jelzi zöldnek vagy nullának.

## Nyilvános weboldal GitHub Pages-en (ingyenes)

1. Hozz létre egy nyilvános GitHub repót; töltsd fel a kicsomagolt fájlokat a repó gyökerébe (a rejtett `.github` és `.nojekyll` fájlokkal együtt).
2. GitHub / Settings / Pages / Build and deployment: **Deploy from a branch**, branch **main**, folder **/(root)**.
3. A GitHub Actions / `Napi adatfrissítés` workflow-t engedélyezd, és egyszer futtasd a **Run workflow** gombbal.
4. Innentől a workflow naponta egyszer (UTC 05:12 körül) betölti a friss adatok `data/latest.json` fájlját. A GitHub ütemezése csúszhat, és a módosuló adatok több perc késéssel jelenhetnek meg.
5. GitHub Pages címed általában: `https://FELHASZNALO.github.io/REPO/`.

A statikus oldalon nincs titkos API kulcs. Nem támogatja a TITÁSZ automatikus üzemzavar-lekérését, mert ehhez nem igazoltan rendelkezésre álló nyilvános interfész; a szolgáltató térképe közvetlen hivatalos hivatkozás.

## Adatok és értelmezés

- Open-Meteo (Nyíregyháza, óránkénti 7 napos előrejelzés): széllökés, hó, hőmérséklet, csapadék. Időjárási **kitettségi index** 0–100; csak tájékozódási pontszám, nem áramszünet-valószínűség.
- Energy-Charts (Fraunhofer ISE, HU day-ahead ár): villamosenergia-piaci **kontextus**. Az árcsúcs nem bizonyít áramhiányt vagy áramszünetet. Forrás feltüntetve; adathasználat: CC BY 4.0, a feed feltételei szerint.
- NOAA SWPC: előrejelzett Kp-index. Geomágneses figyelmeztető kontextus, Kp önmagában nem blackout-előrejelzés.
- Hivatalos oldalak: OPUS TITÁSZ, VÉSZ, ENTSO-E, GIE AGSI+, ENTSOG, NOAA, IODA.

A rendszer minden adatforráshoz külön frissítési időt mutat. Egy feed hibája esetén a régi adat **elavultként** látszik; nincs kipótolt érték.

## Korlátok

Valós, kalibrált blackout-valószínűség (%) kizárólag megfelelő minőségű, földrajzilag összevethető történelmi áramszünet-adatokkal és utólag visszamért modellel számítható. A nyilvános adatok nem tartalmaznak ehhez elegendő címkézett, helyi eseményt. A felületen ezért a blackout-esély és annak pontos időpontja **nem becsülhető**. A jelzett dátumok csak időjárási terhelési csúcsok lehetséges időablakai.

Tilos automatikus döntést hozni kizárólag ez alapján; hatósági utasítás és szolgáltatói közlemény az elsődleges.
