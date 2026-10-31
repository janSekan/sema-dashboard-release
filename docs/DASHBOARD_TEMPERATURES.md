# Teplotné karty dashboardu

Dashboard zobrazuje päť teplôt a kartu Systém v jednej mriežke.

- Šírka pod 768 px: jeden stĺpec.
- Od 768 px: dva stĺpce.
- Od 1280 px: tri stĺpce, dva riadky. Poradie: vonkajšia, vnútorná, voda; kúrenie, aktuálna žiadaná teplota kúrenie, Systém.

**Aktuálna žiadaná teplota kúrenie** používa existujúce `dashboard.equitermTemp`
z `/device-api/dashboard` a históriu `equiterm` z `/device-api/history`. Pochádza z
`tep9` v `temperatures.xml`. Backend ani databáza sa kvôli karte nemenili.

Chýbajúca hodnota sa zobrazuje ako pomlčka, nie ako nula. Pri 0 °C sa zachová jednotka.
Chýbajúca história má prázdny graf s konečnými hranicami osi. Karta Systém má v tomto
rozložení menší ukazovateľ výkonu; ostatné režimy komponentov zachovávajú predvolené správanie.

Overenie: frontend build, ESLint štyroch upravených súborov a Chromium pri šírkach
320, 390, 640, 768, 1024, 1280 a 1440 px v svetlej aj tmavej téme. Overené počty
stĺpcov, šesť kariet/grafov, rovnaké výšky, neprítomnosť pretekania, nulová hodnota
a chýbajúca história. Prehliadač používal testovacie odpovede API; neposielal zápisy
na čerpadlo. Zmena je zatiaľ iba lokálna, bez publikovania release a nasadenia.
