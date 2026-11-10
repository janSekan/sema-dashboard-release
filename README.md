# SEMA Dashboard – rýchly návrat k vývoju

**Spoločný vývoj:** [pokyny pre Codex](AGENTS.md), [synchronizácia VS Code ↔ Cloud](docs/DEVELOPMENT_WORKFLOW.md), [aktuálny stav a ďalšie kroky](docs/PROJECT_STATUS.md). Vývojová vetva: `development`.

Toto je hlavný rozcestník pre vývoj dashboardu a aktualizácie zariadení. Príkazy nižšie sú určené pre lokálny vývojový počítač, ak nie je uvedené Raspberry Pi.

## Ktorý projekt je ktorý

| Projekt | Úloha |
| --- | --- |
| `sema` – tento repozitár | Zdrojový React/Vite frontend, FastAPI backend a release skripty |
| `../sema-release` | Distribučný repozitár: backend a hotový frontend; z jeho GitHub vetiev aktualizujú Raspberry Pi |
| `../sema-bootstrap` | Príprava OS, služieb, siete a provisioning nových Raspberry Pi |
| `/home/jan/Projects/sema-portal` | Samostatný centrálny portál, účty, evidencia zariadení a vzdialená proxy |

Na Raspberry Pi je release nainštalovaný v `/home/jan/sema`. Nie je to vývojový checkout s Vite serverom. Portál má vlastné nasadenie; vydanie dashboardu ho neaktualizuje.

## Každodenné spustenie dashboardu

Spusti dva terminály. Backend aj frontend zastavíš cez `Ctrl+C`.

**Terminál 1 – FastAPI:**

```bash
cd /home/jan/Projects/sema_dashboard/sema/backend
source .venv/bin/activate
LAN_ACCESS=true APP_ENV=development python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminál 2 – React/Vite:**

```bash
cd /home/jan/Projects/sema_dashboard/sema/frontend
npm run dev
```

Otvor `http://localhost:5173/` alebo adresu vypísanú Vite. API dokumentácia je na `http://127.0.0.1:8000/docs`. Vite posiela `/device-api/*` na `127.0.0.1:8000`, preto sa frontendové API URL nemenia.

`LAN_ACCESS=true` tu povoľuje lokálne dashboardové API; bez neho môže predvolené nastavenie odmietať localhost cez 403. Backend je v tomto príkaze viazaný iba na loopback. Toto nastavenie neprenášať automaticky do zákazníckych jednotiek.

## Prvé nastavenie vývojového počítača

Potrebný je Python s modulom `venv`, Node.js/npm, Git a pre release skripty `rsync`. Lokálny build bol overený s Node 22 a Python 3.12.

Ak ešte neexistuje virtuálne prostredie:

```bash
cd /home/jan/Projects/sema_dashboard/sema
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r requirements.txt
```

Frontendové závislosti:

```bash
cd /home/jan/Projects/sema_dashboard/sema/frontend
npm ci
```

Ak chýba `backend/.env`, vytvor ho z `backend/.env.example`; existujúci súbor neprepisuj. Vyplň vlastné lokálne hodnoty:

| Premenná | Význam |
| --- | --- |
| `APP_ENV=development` | Vývojový režim; frontend beží samostatne cez Vite |
| `DEVICE_IP_DEV` | Adresa testovacieho čerpadla alebo jednotky s portom 8081, bez `http://` a bez cesty |
| `DEVICE_USER`, `DEVICE_PASSWORD` | Basic Auth prihlasovanie čerpadla, iba v lokálnom `.env` |
| `DEVICE_ID` | Identita lokálnej inštancie; zákaznícke ID nekopírovať medzi jednotkami |
| `LAN_ACCESS` | Povolenie priameho lokálneho API prístupu; pri vývoji sa vyššie prepisuje na `true` |
| `PROXY_TOKEN` | Samostatný token dôveryhodnej komunikácie s portálom |
| `JWT_SECRET_KEY` | Tajomstvo lokálneho JWT prihlasovania; použiť vlastnú hodnotu |

`development` nie je simulátor. Backend číta cieľ z `DEVICE_IP_DEV`, na pozadí zbiera merania a ovládanie/formuláre môžu zapisovať do skutočného čerpadla. Bez čerpadla alebo mock servera môže UI zobrazovať nedostupnosť či chyby. V produkcii sa cieľ čerpadla berie z databázovej konfigurácie, s predvolenou adresou `192.168.69.2`.

Backend spúšťaj z adresára `backend`: SQLite používa relatívnu cestu `data.db`, teda pri tomto postupe `backend/data.db`. Spustenie z iného adresára môže vytvoriť inú databázu. Prihlasovacie účty dashboardu sú uložené v SQLite; `DEVICE_USER` a `DEVICE_PASSWORD` slúžia na prihlásenie k čerpadlu, nie do dashboardu.

## Overenie pred vydaním

Z koreňa tohto projektu:

```bash
python3 -m unittest discover -s tests -v
bash -n make_release.sh deploy_release.sh promote_release.sh scripts/update.sh scripts/instal-autoupdate.sh
```

Testy release workflow používajú iba dočasné lokálne Git repozitáre, bez GitHubu a živých zariadení. Testovací npm a systemd sú nahradené; skutočný frontend over samostatne:

```bash
cd /home/jan/Projects/sema_dashboard/sema/frontend
npm run build
```

Build vytvorí `frontend/dist`; sám nič nepublikuje. Zostavený frontend backend podáva pri `APP_ENV=production`. Tento režim mení aj výber cieľa čerpadla, preto ho nenastavovať len kvôli lokálnemu náhľadu bez kontroly konfigurácie.

## Testovací a produkčný update

**Kompletný postup vrátane jednorazového prepnutia sema-001:** [docs/RELEASE_WORKFLOW.md](docs/RELEASE_WORKFLOW.md).

| Kanál | Release vetva | Jednotky |
| --- | --- | --- |
| Produkcia | `main` | Zákaznícke jednotky, aj dnes vypnuté |
| Testovanie | `testing` | Iba sema-001 po jednorazovom nastavení |

Z koreňa zdrojového projektu:

```bash
# PUBLIKUJE testovaciu verziu na GitHub; nemení main.
./deploy_release.sh --testing "Popis testovacej verzie"

# Až po overení daného release SHA na sema-001:
# PUBLIKUJE presne tento commit do produkčného main.
./promote_release.sh --production UPLNY_40_ZNAKOVY_OTESTOVANY_RELEASE_SHA
```

Skripty zostavujú aktuálny obsah zdrojov vrátane necommitnutých zmien. Pred publikovaním skontroluj `git status` a `git diff`. Push zdrojového repozitára a push release sú odlišné operácie; jednotky aktualizujú z release repozitára.

Lokálne nastavenie kanála je `/etc/sema/update-channel`, prípadne `/home/jan/.config/sema/update-channel`, ak systémový súbor neexistuje. Oba sú mimo Gitu. Bez neho nový updater používa `main`. Staré jednotky netreba ihneď upravovať. Sema-001 bola 30. 10. 2026 prepnutá na `testing`; podrobnosti, release SHA a záloha sú v [zázname aktivácie](docs/SEMA_001_TESTING.md).

## Rýchla diagnostika Raspberry Pi

**Pri montáži ďalšieho zariadenia:** [kontrola a oprava vlastníctva cez SSH](docs/UPDATE_OWNERSHIP.md#rýchla-kontrola-cez-ssh-pri-ďalšej-montáži). Obsahuje príkaz na kontrolu aj jednorazové `sudo chown`.

Nasledujúce kontroly sú určené pre SSH na konkrétnu jednotku:

```bash
hostname
git -C /home/jan/sema rev-parse HEAD
sudo systemctl status sema --no-pager
sudo journalctl -u sema -n 100 --no-pager
sudo journalctl -u sema-update.service -n 50 --no-pager
systemctl cat sema-update.service sema-update.timer
systemctl list-timers --all
```

Kanál skontroluj cez `cat /etc/sema/update-channel`, ak súbor existuje; inak cez `cat /home/jan/.config/sema/update-channel`. Jeho neprítomnosť pri novom updateri znamená `main`; pri starej jednotke treba pozrieť jej updater.

Príkaz `sudo systemctl start sema-update.service` už aktualizuje kód a reštartuje aplikáciu podľa kanála jednotky. Nie je to iba kontrola. Updater automaticky neinštaluje nové Python závislosti, neaplikuje nginx konfigurácie a nerobí migrácie DB.

Repozitárový timer spúšťa update tri minúty po boote. Starší prevádzkový návod opisuje aj voliteľný nočný reboot, po ktorom sa tento timer spustí. Skutočný stav over na jednotke vrátane `crontab -l` a `sudo crontab -l`.

Na Raspberry Pi systemd používa virtuálne prostredie `/home/jan/sema/.venv`, kým vývojový postup vyššie používa `backend/.venv`. Ide o dve odlišné inštalácie.

## Ďalšia dokumentácia

- [Stav sema-001](docs/SEMA_001_TESTING.md) – aktivovaný testing kanál, nainštalovaný commit a záloha.
- [Koeficient posunu krivky](docs/HEATING_COEFFICIENT.md) – nastavenie pre admina, výpočet a presnosť čerpadla.
- [Release workflow](docs/RELEASE_WORKFLOW.md) – aktuálny postup testing → overenie → produkcia, zapnutie kanála a návrat na main.
- [Deployment](docs/DEPLOYMENT.md) a [staršie poznámky DEPLO](docs/DEPLO.md) – historické prevádzkové a inštalačné postupy; release/update rieši aktuálny návod vyššie.
- [Troubleshooting](docs/TROUBLESHOOTING.md), [first boot](docs/FIRST_BOOT.md), [tvorba image](docs/MAKE_IMAGE.md) a [persistent mode](docs/persistent%20mode.md).
- Portál: `/home/jan/Projects/sema-portal/README.md`; technický kontext v jeho `codex/SEMA_CODEX_CONTEXT.md`, pumpová proxy v `codex/PUMP_PROXY_LOCAL.md`.

`.env`, databázy, tokeny, heslá a virtuálne prostredia nepatria do Gitu. Pred zmenami na živom zariadení over jeho identitu a pred zásahom do dát urob zálohu. Testovací kanál oddeľuje distribúciu kódu; na sema-001 stále ovládaš svoje reálne čerpadlo.

- [Zber histórie, microSD a synchronizácia do portálu](docs/TELEMETRY.md).

Používanie a oprávnenia: [používateľský manuál](docs/USER_MANUAL.md), [kontrakt rolí](docs/ROLES.md).

- [Upraviteľné texty tooltipov Nastavení](docs/SETTINGS_TOOLTIPS.sk.md) – zmeniť text pod identifikátorom, zostaviť frontend a vydať update.

- [Verzie, zostavenia a dostupné aktualizácie](docs/VERSIONING.md).
