# Produkčná oprava TÚV – 10. 11. 2026

Verzia 1.3.1: oba teplotné limity TÚV majú rozsah 0–60 °C, krok 0,5 °C.
Izolovaný hotfix z produkčného a4c9031: backend, skripty a závislosti bezo zmeny.
Východiskový frontend bol bajtovo zhodný s produkciou. Superuser ani koeficient
sa týmto nevydávajú. Priame publikovanie do main schválené používateľom.
Bez riadiacich príkazov čerpadlám, jednotky sa aktualizujú vlastným spúšťačom.
