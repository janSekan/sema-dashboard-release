# Watchdog dashboardu a Tailscale na SEMA jednotke

Stav 21. 11. 2026: implementované a izolovane otestované; **observe na sema-001**
od 19:59:59 CET. Služba a živé sondy zdravé, persistent journal potvrdený.
Od 20:02:33 CET na výslovný pokyn aktívny recover, sondy zdravé; bez pushu,
release. Distribučná a bootstrap integrácia sú následne pripravené iba lokálne.
Toto nie je RAM watchdog portálového servera a nevlastní /dev/watchdog.

## Čo kontroluje

Samostatný Python 3 proces bez nových Python závislostí, cyklus 30 s:

- Backend: localhost:8000/device-api/health musí vrátiť HTTP 200 a `ok=true`.
- Frontend/nginx: localhost:80/ musí vrátiť HTML s lokálnym JS assetom;
  kontroluje sa aj úspešné načítanie assetu (HTML fallback sa odmietne).
- Tailscale: stav služby cez CLI/JSON, Running a Self.Online. Navyše ping
  najviac dvoch online peerov; bez vhodných peerov je výsledok neznámy.
  Nedostupný portál nie je samostatný dôvod na reštartovanie jednotky.
- Sieť: default route mimo eth0/tailscale0/lo, aktívny AP režim,
  TCP spojenie na 1.1.1.1:443 alebo 8.8.8.8:443. DNS pre Tailscale controlplane
  sa zaznamenáva osobitne. Nepriechodné sondy nie sú dôkaz príčiny poruchy.
  Internet s default route, ktorý neodpovedá, sa označí upstream: bez rebootu.

Sondy bežia súbežne s limitmi HTTP 3 s, príkazov spravidla 5 s,
Tailscale peer ping 4 s, WAN TCP 2 s na cieľ, DNS 3 s.
Žiadna sonda nevolá čerpadlo ani nevyužíva tokeny či účty používateľov.

## Obnova a poistky

Po boote tolerancia 300 s, následne súvislá porucha:

| Podmienka | Zásah |
| --- | --- |
| Backend neodpovedá 90 s | Požiadať systemd o restart sema.service |
| Frontend chybný, backend zdravý, 90 s | Restart nginx.service |
| Lokálny Tailscale chybný a WAN dostupná, 90 s | Restart tailscaled.service |
| Peer ping zlyháva, inak zdravý Tailscale a WAN, 90 s | Jeden restart Tailscale za epizódu; nikdy reboot len kvôli peerom |
| Chýba uplink route aj WAN, 90 s | Pokus nmcli device connect wlan0 cez uložené profily |
| Pretrváva lokálna chyba dashboardu/Tailscale/siete 300 s | Reboot RPi, ak to povoľuje rozpočet a synchronizovaný čas |

Odstup medzi opravami rovnakého typu 600 s. Peer odmietnutie môže byť ACL
alebo vzdialená porucha, preto nemá opakované opravy počas tej istej epizódy.
Tailscale NeedsLogin/NeedsMachineAuth/Stopped vyžaduje operátora; žiadne
odhlasovanie, nová autorizácia alebo opakovaný reštart.

Reboot najviac raz za **3 h**, s atómovou fsync rezerváciou mimo aplikácie
v `/var/lib/sema-device-watchdog/recovery.json`. Poškodený stav alebo
nesynchronizovaný čas reboot blokuje. Rezervácia sa vytvorí pred požiadavkou
na reboot a zostáva platná aj pri zlyhaní príkazu. Budget sa pri reinštalácii
nemaže. Súčasná implementácia neskracuje interval podľa používateľskej konfigurácie.

Pri aktívnom update alebo neznámom stave jeho služby, obsadenom/chýbajúcom
`.git/sema-update.lock`, aktívnom Wi-Fi setup locku alebo AP režime sa zásahy
pozastavia a časovače porúch vynulujú. Update lock drží proces počas rozhodnutia
a zásahov. Wi-Fi používa navyše rovnaký lock ako wifi-watch.sh; tým sa
zabráni súbežným opravám. Nevykonáva sa restart NetworkManagera ani zásah do
eth0, pumpovej statickej IP, DHCP alebo Wi-Fi profilov.

`requested` v logu znamená prijatie požiadavky systemd/nmcli; až neskoršia
zdravá sonda potvrdzuje obnovu. `observe` iba zaznamenáva zamýšľané zásahy.
Vlastný daemon lock bráni súbežným inštanciám. Služba má limit pamäte 80 MB,
obmedzené automatické reštarty procesu a rootom vlastnený kód mimo checkoutu.

## Záznamy

Journal override `90-sema-device-watchdog.conf` prekonáva Raspberry Pi vendor
`40-rpi-volatile-storage.conf`. Ukladá **celý systémový journal** trvalo,
s limitom 32 MB, max. súborom 4 MB, retenčným časom 14 dní a rezervou 256 MB.
Ide o horné limity; história môže byť pri plnom logu kratšia.
Synchronizácia bežne 5 min; pred plánovaným rebootom navyše bounded journal sync.
Tvrdý reset alebo nefunkčné úložisko stále môže stratiť posledné záznamy.

Watchdog zapisuje UTC pri zmene stavu, kontrolný záznam každých 10 minút,
a pred opravou služby/MemAvailable/SwapFree, sondy, akciu a jej výsledok.
Nevypisuje env, heslá, profily Wi-Fi ani úplné Tailscale JSON.
HTTP sondy však vytvárajú aj bežné access logy nginx a uvicorn: za 30 s
2 nginx requesty (HTML + asset) a 3 backend requesty (vrátane priameho health).
Limit 32 MB je limit uchovanej histórie, nie denných zápisov alebo fyzickej
write amplification. Skutočnú výdrž SD nemožno z týchto limitov vypočítať.

```bash
sudo journalctl -u sema-device-watchdog -o short-iso
sudo journalctl -b -1 -u sema-device-watchdog -u NetworkManager -u tailscaled -u sema -u nginx
sudo journalctl -b -1 -k
```

## Budúce nasadenie – iba na výslovný pokyn

Najprv preniesť tento adresár do samostatného stagingu na autorizovanej jednotke.
Bežný update.sh nové systémové služby neinštaluje. Nepridávať root spúšťanie
kódu priamo z používateľsky zapisovateľného runtime checkoutu.

1. Overiť zálohu konfigurácie, voľné miesto a aktuálne služby.
2. V stagingu jednorazovo `sudo python3 watchdog.py --check`: iba sondy, bez zápisu
   stavu alebo obnovovacích zásahov. Výsledok obsahuje aj stav update služby.
3. `sudo bash install.sh --observe`: inštalátor zálohuje dotknuté súbory do
   /var/backups/sema-device-watchdog-*, inštaluje root-owned kód, zapne trvalý
   journal a pozorovaciu službu. Overí journal a active stav; pri chybe obnoví
   konfiguráciu a predchádzajúcu službu. Restartuje journald a watchdog,
   nie dashboard/nginx/Tailscale ani celé RPi.
4. Skontrolovať zdravé sondy na reálnej doske, limity pamäte a journal po boote.
   Bezpečne overiť update zámok; nezhadzovať jedinú SSH cestu bez obnovy.
5. Až po ďalšom súhlase aktivovať `sudo bash install.sh --recover`.
   Inštalátor volá každý režim explicitne; bez argumentu je observe.
6. Skúšobné výpadky robiť s dostupnou záložnou cestou. Najprv dashboard/nginx,
   Tailscale/Wi-Fi iba kontrolovane. Fyzická skúška Zero 2 W a 3B zostáva.

Návrat bez opráv: inštalátor `--observe`. Úplné zastavenie:
`sudo systemctl disable --now sema-device-watchdog.service`.
Trvalý journal tým zostáva zapnutý; jeho override možno samostatne obnoviť
zo zálohy alebo odstrániť a reštartovať systemd-journald. Na tom istom zariadení
nerušiť iné existujúce journal konfigurácie a nemať paralelný reboot watchdog.

Pre nové zariadenia je v lokálnom sema-bootstrap pripravené volanie toho istého
rollout kroku. Na zariadenia sa nový bootstrap ani distribučný hook nenasadili.

## Overenie lokálne

`python3 -m unittest discover -s tests -p test_device_watchdog.py -v`

36 izolovaných testov: krátke/dlhé poruchy, pozorovanie a obnova v simulovanom
cykle, update zámok, nezávislé časovače, frontend asset, upstream výpadok,
peer/ACL obmedzenie, Wi-Fi lock, autorizácia Tailscale, NTP/poškodený budget,
pretrvanie 3 h budgetu a jediná inštancia. Navyše Bash syntax, systemd unit
verify a diff check. Testy nevolajú reálne systemd/nmcli/Tailscale ani pumpu.
Observe inštalácia na sema-001 prešla; skutočná obnova/reboot a zachovanie
journalu po ďalšom boote sa ešte netestovali.


## Automatická distribúcia cez release – lokálny kandidát 21. 11. 2026

`scripts/update.sh` po úspešnom update a reštarte dashboardu volá voliteľný
`device-watchdog/rollout.py`. Nový bootstrap používa ten istý krok pod update
zámkom. Chýbajúci bundle v starom release je kompatibilný stav, nie blokér
inštalácie/aktualizácie aplikácie.

### Oprávnenia a dôveryhodný zdroj

Existujúci bootstrap povoľuje janovi sudo bez hesla pre **systemctl**, nie
všeobecný sudo bash/cp. Rollout využije výhradne túto existujúcu cestu:

1. Overí celý 40-znakový release SHA a zhodu HEAD.
2. Do jedinečného stagingu /var/tmp/sema-watchdog-* vyberie päť konkrétnych
   súborov cez git show zo zadaného commitu. Nepoužíva necommitnutý alebo
   podvrhnutý worktree inštalačný bundle; Git nikdy nebeží ako root.
3. Vytvorí jednorazovú oneshot unit sema-device-watchdog-install.service
   s root používateľom a timeoutom 120 s. Cez sudo -n systemctl link --runtime
   a start spustí install.sh --auto-observe. Cudzia už existujúca unit sa
   nenahrádza. Nie sú potrebné nové sudoers pravidlá.
4. Inštalátor skopíruje trvalý daemon do root-owned /usr/local/lib; trvalá
   služba nikdy nespúšťa súbor z janovho aplikačného checkoutu.
5. Po skončení odstráni runtime link a staging. Pri timeoute klienta zostáva
   staging zachovaný, aby sa neodstránil pod stále bežiacim root jobom.

Dôveryhodnosť GitHub release/účtu zostáva podmienkou: ide o autorizované
spustenie release inštalátora ako root, nie o kryptografický podpis či novú
izoláciu používateľa jan. Jan už má široké systémové oprávnenie systemctl.
Na zariadení s inými/užšími sudo pravidlami sa krok môže bezpečne preskočiť.

### Režim a opakovanie

- Nová jednotka začne výhradne observe, nie recover.
- Existujúca konfigurácia observe/recover sa zachová (vrátane sema-001).
- Nezmenené súbory + enabled/active služba = skip_current: žiadny nový backup,
  reload/restart journald ani watchdogu pri každej nočnej aktualizácii.
- Ručne disabled/masked služba sa automaticky nezapne.
- Rootom vytvorený /etc/sema/device-watchdog-auto-disabled blokuje automatickú
  inštaláciu/obnovu. Explicitné manuálne --observe/--recover tým nie sú blokované.
- Neplatná existujúca konfigurácia sa neprepíše a reboot budget sa nemaže.
- Pri chybe inštalátor obnoví súbory/predchádzajúcu službu. Rollout hlási
  warning, ale už úspešný aplikačný update zostáva úspešný. Dôvod je v journale
  sema-device-watchdog-install.service a sema-update.service.

Pri zlyhaní oprávnení alebo cudzom/zostávajúcom install unit sa neinštaluje
nasilu. Po timeoute skontrolovať stav jobu a jeho FragmentPath; staging/root
unit nemaž počas aktívneho jobu. Pri nereštartovanom systéme môže zvyšný unit
vyžadovať ručné preverenie pred ďalším pokusom. Reboot runtime link odstráni.

### Prvý prenos na staršie/offline zariadenia

Starý updater nemá nový hook. Prvá aktualizácia stiahne release s novým
updaterom; až ďalšie spustenie updatera spoľahlivo vykoná inštaláciu. Nespoliehať
sa na priebežné prečítanie prepisovaného Bash skriptu pri git reset --hard.
Pri bežnom režime teda plánovať až **dve nočné aktualizácie**. Offline jednotka
prejde rovnakým postupom po zapnutí. Root-owned poškodený checkout či iný
existujúci problém updatera táto migrácia automaticky neopravuje.

Po prvom prenose možno na autorizovanej skúšobnej jednotke druhý update
spustiť kontrolovane a overiť skip_current. Pred produkciou treba odskúšať
skutočný runtime-systemd most a nočný update na sema-001; lokálne testy
používajú falošný systemctl a nedokazujú nasadenie cez obmedzené sudo na RPi.

### Testy distribučnej časti

- 17 testov politiky/bundlu/mosta: committed SHA, ignorovanie worktree zmien,
  chýbajúce oprávnenia, cudzia unit, zlyhanie a timeout.
- 5 testov skutočného Bash inštalátora v prepísanom dočasnom filesystéme:
  idempotencia, zachovanie recover/budgetu, rollback, opt-out a disabled stav.
- 11 release/updater testov s lokálnym Git remote, vrátane neblokujúcej chyby
  hooku a vylúčenia Python bytecode z balíka scripts/.
- 4 bootstrap testy: starý release, nový hook, chyba a obsadený update lock;
  navyše 4 existujúce bootstrap update preflight testy.
- 36 pôvodných testov samotného watchdogu zostáva úspešných.

Zatiaľ žiadny source push, release ani nasadenie tejto distribučnej zmeny.
