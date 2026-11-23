# Vydanie1.4.4 – oprava prístupových práv recovery guardu

Malá oprava nad presným produkčným1.4.3 dec24db. Žiadna nová funkcia,
frontend, app backend, Python závislosť ani DB migrácia.

Inštalátor pri umask0077 teraz explicitne nastaví kódový adresár0755,
súbory ostávajú0644 a zálohy private0700. Odmieta symlink adresára.
Pred aktiváciou overí čitateľnosť a kompiláciu helpera cez runuser ako jan,
bez vykonania helpera alebo manipulácie s čerpadlom. Kontrola dôvery
bezpečne spracuje nečitateľný starý adresár a umožní jeho opätovnú inštaláciu.

Už zasiahnuté1.4.3 s adresárom0700 môžu zastaviť updater ešte pred fetch;
potrebujú jednorazovú opravu práv (008 už overená755/Result success).
Jednotky na1.4.2 môžu dostať priamo opravenú1.4.4 bez chyby1.4.3.
Pri prechode starým updaterom môže dokončenie inštalácie vyžadovať druhý beh.
Prvý prenos ešte nie je spätne chránený. Presný Git SHA je zdroj pravdy.

176 izolovaných testov vrátane fresh/existing700 adresára pri reálnom
umask0077, readonly guardu, lokálneho Git/SQLite/rollbacku. Bash/Python syntax,
staged file allowlist a bitovo nezmenené app/backend/requirements overené.
Živý root install nového balíka/boot na RPi sa netestoval. Priame main vydanie
na výslovný používateľský pokyn; testing ostáva1.4.2. Nevydaná automatika,
retencia, portálové UI/changelog ani hardvér nie sú v balíku.
