# Produkčné vydanie 1.4.3 – DERP a chránený updater

Používateľ 23.11.2026 výslovne požiadal priame vydanie do distribučného main,
bez predchádzajúceho živého testing/001 kola. Testing sa týmto nemení.
Základ je presná produkcia1.4.2 a43e02f; aplikačný backend, frontendové assety,
requirements a DB schéma sa nemenia. Verzia sa mení na1.4.3.

- Tailscale ping --until-direct=false akceptuje funkčný pong cez DERP;
  preferuje portál a stabilne zoradené online Linux peery. Režim watchdogu
  zostáva zachovaný, existujúce recover/observe nastavenia sa neprepínajú.
- Chránený updater: konzistentná DB/env záloha, kontrola API/HTML/JS,
  kódový rollback bez prepísania aktuálnych dát a karanténa chybných SHA.
- Root-owned nezávislý recovery engine a jan timer pre prerušený updater/boot.
- Dokončenie watchdog hook aj pri nezmenenom SHA, aby adopcia starým updaterom
  nezanechala v /usr/local starú sondu. Opakovaná inštalácia je idempotentná.

Prvý update starým1.4.2 updaterom ešte nie je chránený. Pri ďalšom behu sa
nainštaluje recovery guard a dokončí watchdog hook aj bez nového commitu.
Počítať až s dvoma bežnými aktualizačnými behmi na dokončenie adopcie.
GitHub push nespúšťa aktualizáciu sám; zariadenia ju dostanú svojím časovačom.

Vydanie neobsahuje rozpracovaný Home Assistant, DHCP/3B, hardvér ani retenciu.
174 izolovaných testov, vrátane lokálneho Git/SQLite/SIGKILL rollbacku a DERP,
Bash/Python syntax a distribučný diff prešli. Živý boot/recovery na RPi sa
v tomto vydaní netestoval; je to známy limit pri priamom main vydaní.
Frontend je bitovo nezmenený z produkčného artefaktu, bez nového buildu.
