# Testovací a produkčný kanál SEMA

Aktivácia sema-001 bola dokončená 30. 10. 2026: [overený stav a záloha](SEMA_001_TESTING.md). Nižšie je všeobecný postup pre prípravu a ďalšie vydania.

## Princíp

- `main` v release repozitári je produkcia pre všetky zákaznícke zariadenia.
- `testing` je testovací release pre sema-001.
- `/etc/sema/update-channel` obsahuje jediný riadok `main` alebo `testing`. Ak neexistuje, číta sa `/home/jan/.config/sema/update-channel`; systémový súbor má prednosť.
- Bez tohto súboru nový updater používa `main`. Staré jednotky môžu ďalej používať svoj pôvodný updater bez zmeny.
- Súbor kanála je mimo aktualizovaného repozitára. Nastavenie prežije `git reset --hard`.
- Kanál sa neposudzuje podľa hostname ani automaticky podľa ID; musí sa nastaviť iba na sema-001.

Vypnuté jednotky nevyžadujú okamžitý zásah. Po zapnutí ich pôvodný updater stiahne produkčný `main`, nie `testing`. Nový kompatibilný updater dostanú až s budúcim schváleným produkčným release. Aj po tejto aktualizácii zostanú bez lokálneho súboru na `main`.

## Publikovanie testu z vývojového počítača

Z koreňa zdrojového projektu `sema`:

```bash
./deploy_release.sh --testing "Opis testovacej verzie"
```

Tento príkaz UŽ PUBLIKUJE na GitHub. Prvý testing release už bol publikovaný; aktuálny stav je v zázname aktivácie vyššie.

Skript načíta adresu `origin` zo susedného `sema-release`, pripraví izolovaný dočasný klon, vytvorí alebo nadviaže na `testing`, zostaví frontend a commitne/pushne iba `testing`. Existujúci checkout `sema-release` nemení. Vytlačí úplný release commit SHA, ktorý si treba zaznamenať. Ak sa obsah nezmenil, nový release nevytvorí.

Release obsahuje aktuálne súbory zdrojového projektu vrátane necommitnutých zmien. Pred publikovaním skontrolovať diff a podľa potreby commitnúť zdrojový projekt zvlášť; tento skript ho automaticky necommituje ani nepushuje. Pri prvej príprave sú tu aj rozpracované zmeny pumpovej proxy. Portál má samostatné nasadenie.

Pôvodné `./deploy_release.sh` bez parametrov už nič nepublikuje. `make_release.sh` vyžaduje explicitný samostatný čistý checkout na vetve `testing`; nevymazáva susedný release checkout.

## Jednorazové prepnutie IBA sema-001

Najprv publikovať prvú vetvu `testing`, ktorá už obsahuje nový `scripts/update.sh`. Pred zmenou overiť identitu jednotky sema-001 a dostupnosť SSH. Na sema-001 už boli vykonané podľa záznamu aktivácie; ide o všeobecný návod, nie príkazy na opätovné spustenie bez kontroly stavu.

Na jednotke najprv overiť skutočné spúšťanie aktualizácií:

```bash
hostname
systemctl cat sema-update.service sema-update.timer
systemctl list-timers --all
crontab -l
sudo crontab -l
```

Repozitárový timer má iba `OnBootSec=3min`. Nočný spúšťač môže byť lokálny; treba skontrolovať, či volá `scripts/update.sh`, alebo má vlastné natvrdo uvedené `origin/main`. Druhý prípad treba upraviť osobitne na sema-001 pred zapnutím testovacieho kanála.

Na jednotke dočasne zastaviť timer, ak existuje, a overiť, že práve nebeží update:

```bash
sudo systemctl stop sema-update.timer
systemctl is-active sema-update.service
```

Ak je služba aktívna, počkať na jej dokončenie pred výmenou updatera. Aj prípadný nočný spúšťač musí byť počas prepínania neaktívny. Starý updater ešte nemá zámok proti súbehu.

Zo zdrojového počítača preniesť nový updater na SSH adresu overenej sema-001 (dosadiť skutočnú adresu namiesto `ADRESA_SEMA_001`):

```bash
scp scripts/update.sh jan@ADRESA_SEMA_001:/tmp/sema-update-channel.sh
```

Na sema-001 nainštalovať nový updater a nastaviť lokálny kanál:

```bash
sudo install -m 755 /tmp/sema-update-channel.sh /home/jan/sema/scripts/update.sh
sudo install -d -m 755 /etc/sema
printf '%s\n' testing | sudo tee /etc/sema/update-channel
sudo chmod 644 /etc/sema/update-channel
sudo systemctl start sema-update.service
```

Ak nie je k dispozícii všeobecné sudo a systémový súbor ešte neexistuje, možno namiesto vyššie uvedenej inštalácie použiť ako `jan`:

```bash
install -m 755 /tmp/sema-update-channel.sh /home/jan/sema/scripts/update.sh
mkdir -p /home/jan/.config/sema
printf '%s\n' testing > /home/jan/.config/sema/update-channel
chmod 644 /home/jan/.config/sema/update-channel
sudo systemctl start sema-update.service
```

Pri tomto variante overovať a neskôr meniť kanál v `/home/jan/.config/sema/update-channel`, nie v `/etc/sema/update-channel`. Existujúci systémový súbor má vždy prednosť. Užívateľský súbor sa do release nekopíruje.

Po dokončení overiť:

```bash
cat /etc/sema/update-channel
git -C /home/jan/sema rev-parse HEAD
sudo systemctl status sema --no-pager
sudo journalctl -u sema-update.service -n 50 --no-pager
```

SHA musí zodpovedať zamýšľanému release. Potom znovu spustiť pôvodný timer:

```bash
sudo systemctl start sema-update.timer
```

Ak staršia systemd služba beží ako root, nový updater sa najprv prepne cez `runuser` na `jan`, aby Git použil jeho identitu a oprávnenia. Reštart aplikácie používa povolené `sudo systemctl`.

Nový updater explicitne fetchuje vybranú vetvu aj z klonu pôvodne obmedzeného na `main`. Pri neplatnom kanáli alebo chýbajúcej vzdialenej vetve skončí chybou, bez návratu na inú vetvu a bez reštartu služby. Súbežné spustenia blokuje `flock`.

## Bežné testovanie

1. Publikovať nový release cez `deploy_release.sh --testing ...`.
2. Na sema-001 spustiť `sudo systemctl start sema-update.service`.
3. Overiť skutočný `git rev-parse HEAD` a funkcie aplikácie. Ak sa do testing medzitým publikovala novšia verzia, otestovať skutočne nainštalovaný commit.
4. Zákaznícke zariadenia zostávajú na nezmenenom `main`.

Updater naďalej sťahuje kód a reštartuje službu. Automaticky neinštaluje Python závislosti, nemení nginx ani databázovú schému. Takéto zmeny majú samostatný postup nasadenia; pred nimi zálohovať lokálne dáta. Živý test môže reálne ovládať domáce čerpadlo.

## Vydanie overeného release do produkcie

Až po testovaní z vývojového počítača:

```bash
./promote_release.sh --production UPLNY_40_ZNAKOVY_OTESTOVANY_RELEASE_SHA
```

Tento príkaz UŽ MENÍ produkčný `main` na GitHube. Nevytvára nový build ani nový commit. Publikuje presne otestovaný release SHA, aj keď `testing` už obsahuje ďalšie zmeny. Vyžaduje, aby commit patril do histórie `testing` a nadväzoval na aktuálny `main`. Nepoužíva force push; pri rozídenej histórii treba pripraviť a otestovať release obsahujúci aktuálnu produkciu.

Po publikovaní dostanú aktívne aj neskôr zapnuté zákaznícke jednotky tento release cez svoj existujúci update. GitHub push sám od seba nespustí okamžitý update na jednotkách; rozhoduje ich spúšťač.

## Návrat sema-001 na produkčný kanál

S novým updaterom a po overení aktuálneho stavu zariadenia:

```bash
printf '%s\n' main | sudo tee /etc/sema/update-channel
sudo systemctl start sema-update.service
```

Je to návrat kódu na aktuálny produkčný release, nie obnova databázy alebo predchádzajúcich nastavení. Zákaznícke zariadenia sa tým nemenia.

## Lokálne testy

```bash
bash -n make_release.sh deploy_release.sh promote_release.sh scripts/update.sh scripts/instal-autoupdate.sh
python3 -m unittest discover -s tests -v
```

Testy používajú výhradne dočasné lokálne bare Git repozitáre. Npm build a systemd sú nahradené testovacími príkazmi; Git fetch/push/reset a rsync sa vykonávajú reálne iba v dočasných repozitároch. Pokrývajú oddelenie vetiev, presné povýšenie staršieho otestovaného commitu, vylúčenie tajomstiev a DB, ochranu čistého checkoutu, odmietnutie rozídenej produkcie, kompatibilitu starého updatera, oba kanály nového updatera aj chybové stavy. Nedotýkajú sa GitHubu, skutočného release checkoutu ani živých zariadení.

## Kontrola oprávnení updatera

Diagnostika chýb `Permission denied` v Git a rozdiel medzi sudo právami a vlastníctvom
sú popísané v [Automatické aktualizácie: vlastníctvo Git a sudo](UPDATE_OWNERSHIP.md).
Nový updater ponúka `--check` bez stiahnutia/reštartu; na starom updateri tento parameter
nepoužívať. Git nespúšťať cez `sudo git ...`.
