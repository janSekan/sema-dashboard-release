# Testing kandidát 1.4.1 – 21. 11. 2026

Základ: presný zdroj produkcie 1.4.0 (2ef243d). Pridaný len device watchdog,
voliteľný update hook, vylúčenie scripts bytecode a testy/návod. Nezahŕňa
lokálne rozpracované DHCP/3B ani ďalšie zmeny hlavného development checkoutu.
Nová automatická inštalácia začína observe; existujúci recover sa zachová.
Cieľ iba testing/sema-001, produkčný distribučný main sa nemení.


## Testing 1.4.1 – rollout overený 21. 11. 2026, 20:26 CET

Na výslovný pokyn publikovaný iba distribučný testing
`817e5614a1869808e0ea427b1784a536e6607399`; main zostal
`ab6c9188d788ca7ee9c9ec1c56db913d57aacc71` (1.4.0).
Izolovaný zdroj release/watchdog-1.4.1, kandidát c865a91 zo stabilného 2ef243d;
worktree /tmp/sema-watchdog-release-v9jipfoj/sema. Nepribalené lokálne DHCP,
3B ani ostatné rozpracované zmeny development checkoutu.

69 cielených testov kandidáta (36 watchdog, 22 rollout/installer, 11 release),
Bash syntax, systemd verify, diff check a frontend build úspešné.
Pred update konzistentná SQLite záloha integrity=ok:
`/home/jan/sema-backups/before-watchdog-141-20261121T192613Z`.
Záloha pôvodne hľadala backend/.env; runtime má .env v koreni. Koreňová .env
má po update stále mtime 28. 10. 2026; kópia po update je výslovne označená
.env.post-update, nie predaktualizačná záloha. Hash pred/po nie je k dispozícii.

Prvý priamy update.sh nainštaloval release a reštartoval dashboard, ešte bez
nového hooku. Druhý update.sh vyvolal root oneshot cez sudo systemctl;
`SEMA_WATCHDOG_ROLLOUT install_job_succeeded`, root journal potvrdil
`DEVICE_WATCHDOG_AUTO skip_current`. Runtime install unit potom not-found,
staging odstránený (0 /var/tmp/sema-watchdog-*). Existujúci watchdog zostal
recover, pôvodný proces zo 20:02:33 CET, NRestarts=0, active. SEMA/nginx/Tailscale
aktívne, HTTP backend/HTML/JS asset=200, DB quick_check=ok, verzia 1.4.1,
RPi uptime zachovaný. Na čerpadlo sa neposlali riadiace príkazy.

Overený je most so skutočnými obmedzenými sudo oprávneniami a no-op aktualizácia
už nainštalovaného watchdogu. Prvú automatickú inštaláciu na úplne čistom RPi
naďalej pokrývajú iba izolované testy; nezhadzovala sa ochrana 001 na jej simuláciu.
Nočný reboot/update ešte čaká na overenie. Zdrojový development a bootstrap
sa nepushovali, produkčný portál ani zákaznícke main sa nemenili.
