# Automatické aktualizácie: vlastníctvo Git a sudo

## Rýchla kontrola cez SSH pri ďalšej montáži

Na svojom počítači nahraď `IP_ZARIADENIA` Tailscale adresou kontrolovanej jednotky:

```bash
ssh jan@IP_ZARIADENIA 'find /home/jan/sema -xdev \( ! -user jan -o ! -group jan \) -printf "%u:%g %p\n"'
```

- Ak príkaz nič nevypíše a neohlási chybu, všetky skontrolované súbory patria `jan:jan`.
- Ak vypíše súbory/adresáre, majú iného vlastníka alebo skupinu.
- Pri chybe SSH, chýbajúcom adresári alebo `Permission denied` kontrola nie je úspešná; samotný chýbajúci zoznam nie je dôkaz správneho vlastníctva.

Pri potvrdenom nesprávnom vlastníctve vykonaj jednorazovú opravu:

```bash
ssh -t jan@IP_ZARIADENIA 'sudo chown -R jan:jan /home/jan/sema'
```

Heslo zadaj iba v termináli a potom zopakuj prvý príkaz. Oprava nemení obsah súborov,
nespúšťa update a nereštartuje zariadenie ani dashboard. Overuje/opravuje vlastníctvo,
nie celý aktualizačný cyklus. Príkazy fungujú aj na starších jednotkách bez nového
bootstrapového kontrolného skriptu.

## Incident sema-005 (31. 10. 2026)

Zariadenie `100.74.74.89` malo `sema-update.service` nastavenú na `User=jan` a platné
bezheslové oprávnenie na `/usr/bin/systemctl`. Log nočného behu ukázal skutočnú chybu:

```text
cannot update the ref 'refs/remotes/origin/main':
unable to append to '.git/logs/refs/remotes/origin/main': Permission denied
```

Reflog, niektoré refs/objects a časť pracovných súborov patrili rootovi. Nadradený
adresár `/home/jan/sema` pritom patril jan, takže pôvodná povrchná kontrola vlastníctva
prešla. Na disku už bol po neskoršom ručnom zásahu release `7d7b82a` a dashboard bol
aktívny; zlyhanie nočnej aktualizácie zostalo zaznamenané v updater službe.

Presný starší príkaz, ktorý vytvoril prvé root-owned Git súbory, z dostupných logov
nie je potvrdený. Takýto stav vzniká pri Git operáciách spustených ako root, napríklad
cez starý root-run updater alebo `sudo git fetch/reset`. Nový updater sa pri root
spustení prepína na jan, ale už existujúce nesprávne vlastníctvo sám neopravoval.

Bootstrap `9d024b4` už klonoval pod jan a na konci používal `chown -R jan:jan`.
Nie je teda preukázané, že nesprávne súbory vytvorila čistá inštalácia bootstrapu.
Samostatný starší `scripts/instal-autoupdate.sh` však vytváral službu bez `User=jan`;
jeho definícia bola zjednotená s bootstrapom.

## Jednorazová oprava postihnutej jednotky

Najprv prečítať log, vlastníctvo a stav; nespúšťať bootstrap ani update naslepo:

```bash
systemctl cat sema-update.service
journalctl -u sema-update.service -n 60 --no-pager
stat -c '%U:%G %a %n' /home/jan/sema /home/jan/sema/.git/logs/refs/remotes/origin/main
```

Administrátor pri potvrdenom zlom vlastníctve opraví iba aplikačný strom:

```bash
sudo chown -R jan:jan /home/jan/sema
```

Tento príkaz nemení obsah ani nereštartuje služby. Zvyčajne vyžaduje heslo, pretože
SEMA sudoers povoľuje bez hesla nmcli a systemctl, nie chown ani ľubovoľný skript.
Po oprave skontrolovať updater ako jan. Pri novej verzii:

```bash
bash /home/jan/sema/scripts/update.sh --check
```

Pozor: stará verzia updatera parameter `--check` nepozná a môže napriek nemu vykonať
plný update. Kontrolu používať až po overení verzie skriptu. Nový bootstrap obsahuje
samostatnú bezpečnú kontrolu `sudo /usr/local/sbin/sema-check-updates`.

Až v dohodnutom servisnom čase spustiť skutočnú aktualizáciu:

```bash
sudo -n /usr/bin/systemctl start sema-update.service
systemctl show sema-update.service -p Result -p ExecMainStatus
```

To už môže stiahnuť release a reštartovať dashboard. Nespoliehať sa na to, že samotný
aktuálny HEAD dokazuje úspešný nočný update; treba skontrolovať aj výsledok služby.

## Prevencia v novom kóde

- `scripts/update.sh`: Git vždy pod jan, vrátane staršej root služby/manuálneho sudo.
- Pred fetch/reset: vnorené vlastníctvo Git aj checkoutu (bez závislostí .venv/node_modules),
  zapisovateľné Git metadata a skutočné bezheslové systemctl cez neinteraktívny `sudo -n`.
- Pri chybe sa skončí ešte pred stiahnutím/zmenou checkoutu a vypíše sa konkrétna diagnóza.
- `--check` nevykonáva fetch/reset/reštart ani nevytvára aktualizačný zámok.
- Reštart/status používajú `sudo -n /usr/bin/systemctl`; updater sa nikdy nepýta na heslo.
- `instal-autoupdate.sh` vytvára `User=jan`, `WorkingDirectory=/home/jan/sema` a overuje
  pripravenosť pred povolením timeru.
- Bootstrap po inštalácii a vo `verify.sh` overí aj vnorené vlastníctvo, syntax updatera,
  účet služby a efektívne sudo. Nestačí iba syntax sudoers a vlastník hlavného adresára.

Opravy zdrojov samy nezmenia vypnuté jednotky ani oprávnenia existujúcich poškodených
checkoutov. Nové inštalácie potrebujú novú verziu bootstrapu; nové aplikačné vydanie
musí obsahovať opravený updater. Publikovanie sa robí samostatne podľa release workflow.

## Overenie

8 lokálnych integračných testov release/updatera a 4 testy bootstrap preflightu.
Overujú kanály main/testing, presné povýšenie release, odmietnutie zlého sudo/vlastníctva
pred fetch, režim --check bez mutácií a delegovanie root → jan. Bootstrap testy nespúšťajú
skutočné sudo/systemd ani inštaláciu OS. Skripty navyše prešli `bash -n`.

## Výsledok opravy sema-005

Používateľ vykonal jednorazové `sudo chown -R jan:jan /home/jan/sema`.
Následná SSH kontrola potvrdila správne vlastníctvo; reálny `git fetch` pod účtom
jan prešiel bez chyby. Nový updater bol prenesený iba do dočasného súboru a jeho
`--check` na zariadení úspešne overil vlastníctvo, neinteraktívne sudo a kanál main;
dočasný súbor sa odstránil.

HEAD zostal `7d7b82a`, pracovný strom čistý, aplikácia aj timer aktívne a čas štartu
aplikácie nezmenený. Počas diagnostiky neprebehol git reset, plný update ani reštart.
Historický výsledok zlyhanej nočnej systemd úlohy sa zámerne neprepisoval; úspech
celého automatického cyklu potvrdí až ďalšie skutočné spustenie služby.

Zdrojové opravy updatera a bootstrapu sú zatiaľ lokálne commitnuté, nie publikované.
