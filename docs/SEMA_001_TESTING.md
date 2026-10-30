# sema-001 – aktivovaný testovací kanál

Overené 30. 10. 2026 cez SSH, používateľ `jan`, Tailscale IP `100.89.145.76`. Hostname aj `DEVICE_ID` sú `sema-001`.

## Aktuálny stav

- Release GitHub repozitár: `janSekan/sema-dashboard-release`.
- Produkčný `main` zostal na `4d9078e5d861f9718748741834b93a234cf4bfb2`.
- Prvý publikovaný `testing` a nainštalovaný release: `fbc772a55dec58531a46a3a78bc8b4d335e1cc43`.
- Kanál je v `/home/jan/.config/sema/update-channel`, obsah `testing`.
- `/etc/sema/update-channel` neexistuje. Ak sa neskôr vytvorí, má prednosť.
- `sema` a `sema-update.timer` sú aktívne. Aktualizačná služba po spustení skončila `Result=success`, `ExecMainStatus=0`.
- Lokálna Git vetva na jednotke nemusí mať názov kanála: updater inštaluje commit z explicitne vybraného vzdialeného refu. Rozhoduje súbor kanála a `git rev-parse HEAD`, nie názov lokálnej vetvy.

Staršia nainštalovaná systemd služba spúšťa updater ako root. Nový updater sa cez `runuser` prepína na `jan`, aby Git používal jeho prostredie a prístup. Reštart aplikácie používa už existujúce oprávnenie `sudo systemctl` bez hesla. Systémové sudo oprávnenia ani systemd jednotky neboli menené.

## Ďalší testovací update

Na vývojovom počítači zo zdrojového projektu:

```bash
cd /home/jan/Projects/sema_dashboard/sema
./deploy_release.sh --testing "Popis zmeny"
```

Potom na jednotke:

```bash
ssh jan@100.89.145.76
sudo systemctl start sema-update.service
git -C /home/jan/sema rev-parse HEAD
systemctl show sema-update.service --property=Result --property=ExecMainStatus
```

Publikovať do produkcie až po samostatnom testovaní podľa [release workflow](RELEASE_WORKFLOW.md). Žiadny produkčný release nebol pri aktivácii testovacieho kanála vydaný.

## Záloha pred prepnutím

Súkromný adresár na jednotke:

```text
/home/jan/sema-backups/before-testing-20261030-202004
```

Obsahuje konzistentnú SQLite zálohu cez backup API, lokálne environment súbory, pôvodný updater, existujúci `backend/auth.py.bak` a pôvodný release SHA. Adresár má práva 700, citlivé zálohované súbory 600. Nie je súčasťou Gitu.

Po update sa porovnaním bajtov overilo, že lokálna konfigurácia a `backend/auth.py.bak` zostali nezmenené. Backendový kód ani requirements sa v tomto release nemenili. Konfigurácia nginx sa iba stiahla ako súbor v repozitári; nenainštalovala sa do systému.

## Čo sa overilo

- Štyri lokálne integračné testy release workflow a Bash syntax.
- Reálny update cez existujúcu systemd službu na sema-001.
- GET dashboardu na lokálnom porte 8000 aj cez nginx na porte 80.
- GET nového frontendového assetu, ktorý obsahuje podporu `sema-pump-url`.
- GET autentifikovaného sync/status so zhodou `device_id=sema-001`, bez vypísania tokenu.
- GET access-mode API, aktívna aplikácia aj timer.
- Kontrola vzdialených refov na GitHube: `main` nezmenený, nový commit iba v `testing`.

Nerobili sa POST požiadavky do čerpadla ani zmeny jeho nastavení. Portálový backend nebol nasadený, takže nové otvorenie pumpy cez portál vyžaduje ešte samostatné nasadenie portálovej časti. Zákaznícke jednotky, lokálny checkout `sema-release` a bootstrap neboli upravované.

## Nočné aktualizácie

Overený timer má `OnBootSec=3min`, nie opakovaný nočný interval. Aktuálny boot aplikácie bol o 02:00 a posledný pôvodný update o 02:03. Používateľ `jan` nemá crontab; systémový `/etc/crontab` neobsahoval priamy SEMA update. Rootov crontab nebol prístupný bez hesla, takže presný zdroj nočného rebootu ostáva neoverený. Po ďalšom nočnom cykle je vhodné overiť kanál, SHA a výsledok služby. Bežná bootová aktualizácia cez overenú službu už používa `testing`.

## Návrat na aktuálnu produkciu

Na sema-001, ak stále neexistuje systémový súbor kanála:

```bash
printf '%s\n' main > /home/jan/.config/sema/update-channel
sudo systemctl start sema-update.service
```

Ide o návrat kódu; databázu ani nastavenia tým neobnovuješ. Po nainštalovaní dnešnej starej produkčnej verzie sa môže obnoviť aj starý main-only updater. Pred ďalším prepnutím na testing preto znovu nainštalovať nový updater podľa [návodu](RELEASE_WORKFLOW.md).
