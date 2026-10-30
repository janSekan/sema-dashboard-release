> Historický prevádzkový návod. Pre aktuálne spustenie vývoja začni v [hlavnom README](../README.md). Publikovanie release a kanály `testing`/`main` sa riadia [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md); staršie update postupy nižšie nie sú aktuálnym publikačným workflow.

# SEMA Dashboard Deployment Guide v1.0

Autor: Jan Sekan

Posledná aktualizácia: 2026-06

---

# 1. Prehľad

SEMA Dashboard beží na:

- Raspberry Pi Zero 2W
- Raspberry Pi OS Lite
- FastAPI backend
- React frontend (buildnutý do dist)
- SQLite databáza
- Tailscale vzdialený prístup
- Ethernet pripojenie k tepelnému čerpadlu
- WiFi provisioning cez AP mód

Architektúra:

Internet
↓
Tailscale
↓
RPi Zero 2W
├── wlan0 → domáca WiFi
└── eth0 → tepelné čerpadlo

---

# 2. Požiadavky

Hardware:

- Raspberry Pi Zero 2W
- SD karta (odporúčané 16 GB+)
- Ethernet adaptér pre RPi Zero 2W
- Ethernet kábel
- Napájanie

Softvér:

- Raspberry Pi OS Lite
- GitHub release repository
- Tailscale účet

---

# 3. Flash Raspberry Pi OS Lite

Flash pomocou Raspberry Pi Imager.

Odporúčané:

- Raspberry Pi OS Lite
- SSH enabled
- hostname
- username
- password
- WiFi

POZNÁMKA:

Počas prvého nasadenia Raspberry Pi Imager neaplikoval:

- hostname
- username
- password
- WiFi

Po flashnutí preto vždy overiť lokálne na monitore.

---

# 4. Prvé spustenie

Prihlásenie lokálne.

Overenie hostname:

```bash
hostname
```

Overenie WiFi:

```bash
nmcli device
```

---

# 5. Oprava WiFi ak nefunguje

Príznak:

```text
wlan0 unavailable
```

alebo

```text
Soft blocked: yes
```

Kontrola:

```bash
rfkill list
```

Oprava:

```bash
sudo rfkill unblock wifi
```

Zapnutie WiFi rádia:

```bash
sudo nmcli radio wifi on
```

Kontrola:

```bash
nmcli radio wifi
```

Očakávaný výsledok:

```text
enabled
```

---

# 6. Pripojenie na WiFi

Cez raspi-config alebo nmcli.

Kontrola:

```bash
nmcli device
```

Očakávaný výsledok:

```text
wlan0 connected
```

---

# 7. SSH

Zistenie IP:

```bash
hostname -I
```

Pripojenie:

```bash
ssh jan@IP_ADRESA
```

Po úspešnom SSH už nie je potrebný monitor.

---

# 8. Aktualizácia systému

```bash
sudo apt update
sudo apt upgrade -y
```

Reboot:

```bash
sudo reboot
```

---

# 9. Tailscale

Inštalácia:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

Prihlásenie:

```bash
sudo tailscale up
```

Overenie:

```bash
tailscale status
```

IP:

```bash
tailscale ip -4
```

SSH test:

```bash
ssh jan@TAILSCALE_IP
```

---

# 10. Inštalácia potrebných balíkov

```bash
sudo apt install git python3-pip python3-venv -y
```

---

# 11. Release repository

Vytvorenie adresára:

```bash
mkdir -p ~/sema
cd ~/sema
```

Clone:

```bash
git clone https://github.com/USERNAME/sema-dashboard-release.git .
```

---

# 12. Python prostredie

Vytvorenie:

```bash
python3 -m venv .venv
```

Aktivácia:

```bash
source .venv/bin/activate
```

Inštalácia závislostí:

```bash
pip install -r requirements.txt
```

---

# 13. Environment

Súbor:

```text
/home/jan/sema/.env
```

Nie je súčasťou release repozitára.

Musí existovať lokálne.

---

# 14. Backend test

```bash
cd ~/sema/backend

source ../.venv/bin/activate

uvicorn main:app --host 0.0.0.0 --port 8000
```

Test:

```bash
curl http://localhost:8000/api/health
```

---

# 15. Systemd

Vytvoriť:

```bash
sudo nano /etc/systemd/system/sema.service
```

Obsah:

```ini
[Unit]
Description=SEMA Dashboard FastAPI
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
User=jan
WorkingDirectory=/home/jan/sema/backend
EnvironmentFile=/home/jan/sema/.env
ExecStart=/home/jan/sema/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Aktivácia:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sema
sudo systemctl start sema
```

Kontrola:

```bash
sudo systemctl status sema --no-pager
```

---

# 16. Automatický denný reboot

Voliteľné.

```bash
sudo crontab -e
```

Pridať:

```cron
0 2 * * * /sbin/reboot
```

Denný reboot o 02:00.

---

# 17. Ethernet pripojenie čerpadla

Čerpadlo:

```text
IP: 192.168.69.2
Maska: 255.255.255.0
DHCP: OFF
```

RPi:

```text
IP: 192.168.69.10
Maska: 255.255.255.0
```

Zistenie profilu:

```bash
nmcli connection show
```

Nastavenie:

```bash
sudo nmcli connection modify "LAN" \
ipv4.method manual \
ipv4.addresses 192.168.69.10/24
```

Aktivácia:

```bash
sudo nmcli connection up "LAN"
```

Kontrola:

```bash
ip -4 addr show dev eth0
```

### Pridanie služby na reboot

Vprípade že sa nenačíta ethernet adaptér po boote, zariadenie sa rebootne

Vytvoriť

Vytvoriť script a zmeniť práva

```bash
sudo nano /usr/local/bin/check-usb-ethernet.sh
sudo chmod +x /usr/local/bin/check-usb-ethernet.sh
```

```bash
#!/bin/bash

ADAPTER_ID="1a86:e396"
COUNT_FILE="/var/tmp/sema-usb-eth-reboot-count"
MAX_REBOOTS=10

sleep 20

if lsusb | grep -q "$ADAPTER_ID"; then
    logger "SEMA: USB Ethernet found"
    rm -f "$COUNT_FILE"
    exit 0
fi

count=0
if [ -f "$COUNT_FILE" ]; then
    count=$(cat "$COUNT_FILE")
fi

count=$((count + 1))
echo "$count" > "$COUNT_FILE"

logger "SEMA: USB Ethernet missing. Reboot attempt $count/$MAX_REBOOTS"

if [ "$count" -le "$MAX_REBOOTS" ]; then
    reboot
else
    logger "SEMA: USB Ethernet still missing after $MAX_REBOOTS attempts. Leaving system running."
    exit 1
fi
```

```bash
sudo chmod +x /usr/local/bin/check-usb-ethernet.sh
```

Služba

```bash
sudo nano /etc/systemd/system/eth-reboot.service
```

```ini
[Unit]
Description=Check USB Ethernet
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/check-usb-ethernet.sh

[Install]
WantedBy=multi-user.target
```

Aktivácia:

```bash
sudo systemctl daemon-reload
sudo systemctl enable eth-reboot
sudo systemctl start eth-reboot
```

---

# 18. Test komunikácie s čerpadlom

Ping:

```bash
ping -c 4 192.168.69.2
```

Status XML:

```bash
curl --user "$DEVICE_USER" http://192.168.69.2/status.xml
```

Očakávaný výsledok:

XML odpoveď čerpadla.

---

# 19. WiFi Provisioning

Balíky:

```bash
sudo apt install hostapd dnsmasq -y
```

---

# 20. AP profil

Súbor:

```bash
/etc/NetworkManager/system-connections/sema-ap.nmconnection
```

Obsah:

```ini
[connection]
id=sema-ap
type=wifi
interface-name=wlan0
autoconnect=false

[wifi]
mode=ap
ssid=SEMA-Setup

[wifi-security]
key-mgmt=wpa-psk
psk=sema1234

[ipv4]
method=shared
address1=192.168.4.1/24

[ipv6]
method=disabled
```

Práva:

```bash
sudo chmod 600 /etc/NetworkManager/system-connections/sema-ap.nmconnection
```

Reload:

```bash
sudo nmcli connection reload
```

---

# 21. AP Fallback Watcher

Skript:

```text
/home/jan/sema/scripts/wifi-watch.sh
```

Spúšťa AP ak nie je dostupná WiFi.

---

# 22. Povolenie nmcli bez hesla

Nutné pre provisioning.

```bash
sudo visudo -f /etc/sudoers.d/sema-nmcli
```

Obsah:

```text
jan ALL=(root) NOPASSWD: /usr/bin/nmcli
```

Práva:

```bash
sudo chmod 440 /etc/sudoers.d/sema-nmcli
```

---

# 23. WiFi Watch Service

Súbor:

```text
/etc/systemd/system/sema-wifi-watch.service
```

Obsah:

```ini
[Unit]
Description=SEMA WiFi AP fallback watcher
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/home/jan/sema/scripts/wifi-watch.sh
```

---

# 24. WiFi Watch Timer

Súbor:

```text
/etc/systemd/system/sema-wifi-watch.timer
```

Obsah:

```ini
[Unit]
Description=Run SEMA WiFi watcher periodically

[Timer]
OnBootSec=30
OnUnitActiveSec=30
Unit=sema-wifi-watch.service

[Install]
WantedBy=timers.target
```

Aktivácia:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sema-wifi-watch.timer
sudo systemctl start sema-wifi-watch.timer
```

Kontrola:

```bash
systemctl list-timers | grep sema
```

---

# 25. Nginx Reverse Proxy

Cieľ:

Namiesto:

```text
http://IP:8000
```

používať:

```text
http://IP
```

Zároveň umožniť prístup k pôvodnému webovému rozhraniu tepelného čerpadla cez:

```text
http://IP:8081
```

---

## Inštalácia

```bash
sudo apt update
sudo apt install nginx -y
```

---

## Kontrola

```bash
systemctl status nginx --no-pager
```

Očakávaný výsledok:

```text
active (running)
```

---

## Odstránenie default konfigurácie

```bash
sudo rm /etc/nginx/sites-enabled/default
```

---

## Vytvorenie konfigurácie

```bash
sudo nano /etc/nginx/sites-available/sema
```

Obsah:

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 8081;
    server_name _;

    location / {
        proxy_pass http://192.168.69.2/;

        proxy_set_header Host 192.168.69.2;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Aktivácia

```bash
sudo ln -s /etc/nginx/sites-available/sema /etc/nginx/sites-enabled/sema
```

---

## Test konfigurácie

```bash
sudo nginx -t
```

Očakávaný výsledok:

```text
syntax is ok
test is successful
```

---

## Reload konfigurácie

```bash
sudo systemctl reload nginx
```

---

## Test Dashboardu

```bash
curl http://localhost/api/health
```

---

## Test webového rozhrania čerpadla

```bash
curl -I http://localhost:8081
```

Očakávaný výsledok:

```text
HTTP/1.1 200 OK
```

(alebo odpoveď webového servera čerpadla)

---

## Výsledok

SEMA Dashboard je dostupný na:

```text
http://IP
```

bez portu 8000.

Pôvodné webové rozhranie tepelného čerpadla je dostupné na:

```text
http://IP:8081
```

---

## Poznámka

Prístup k čerpadlu cez samostatný port 8081 bol zvolený zámerne.

Pokus o sprístupnenie čerpadla cez:

```text
http://IP/pump/
```

spôsoboval problémy s JavaScriptom a AJAX komunikáciou (`gweth.js`, `status.xml`, `parameters.htm`, `timer.htm`).

Samostatný port 8081 zabezpečuje plnú kompatibilitu s pôvodným webovým rozhraním čerpadla.

Výhodou je tiež možnosť ponechať na všetkých inštaláciách rovnakú IP adresu čerpadla:

```text
192.168.69.2
```

bez potreby individuálneho adresovania jednotlivých zariadení.

# 26. Automatická aktualizácia po boote

Cieľ:

Po každom štarte zariadenia automaticky skontrolovať dostupnosť novej verzie Dashboardu.

Dôvod:

SEMA zariadenia môžu byť nainštalované aj niekoľko mesiacov po vytvorení Golden Image.

Automatická aktualizácia zabezpečí, že po prvom pripojení do internetu sa zariadenie aktualizuje na najnovšiu verziu.

---

## Systemd služba

Vytvorenie:

```bash
sudo nano /etc/systemd/system/sema-update.service
```

Obsah:

```ini
[Unit]
Description=SEMA Auto Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/home/jan/sema/scripts/update.sh
```

---

## Systemd timer

Vytvorenie:

```bash
sudo nano /etc/systemd/system/sema-update.timer
```

Obsah:

```ini
[Unit]
Description=Run SEMA update after boot

[Timer]
OnBootSec=3min
Unit=sema-update.service

[Install]
WantedBy=timers.target
```

---

## Aktivácia

```bash
sudo systemctl daemon-reload

sudo systemctl enable sema-update.timer
sudo systemctl start sema-update.timer
```

---

## Kontrola

```bash
systemctl list-timers | grep sema-update
```

Očakávaný výsledok:

```text
sema-update.timer
```

---

## Správanie

Po štarte zariadenia:

```text
Boot
↓
SEMA Dashboard sa spustí
↓
Po 3 minútach
↓
Kontrola aktualizácie
↓
GitHub release repo
↓
Aktualizácia (ak existuje)
↓
Reštart služby SEMA
```

---

## Poznámka

Zariadenie sa aktualizuje po každom boote.

Momentálne je systém denne reštartovaný watchdogom približne o:

```text
02:00
```

čo znamená, že kontrola aktualizácií prebehne automaticky každý deň približne o:

```text
02:03
```

---

# 27 Aktualizácia aplikácie

Manuálna aktualizácia:

```bash
./scripts/update.sh
```

Skript vykoná:

```text
Git fetch
↓
Reset na origin/main
↓
Reštart služby SEMA
```

Obsah skriptu:

```bash
#!/bin/bash
set -e

cd /home/jan/sema

echo "Fetching latest release..."
git fetch origin

echo "Resetting to origin/main..."
git reset --hard origin/main

echo "Restarting SEMA service..."
sudo systemctl restart sema

echo "Status:"
sudo systemctl status sema --no-pager
```

# 28. Helper Scripts

Adresár:

```text
scripts/
```

Obsah:

```text
scripts/
├── update.sh
├── health.sh
├── logs.sh
└── wifi-watch.sh
```

update.sh:

```bash
#!/bin/bash
set -e

cd /home/jan/sema

git pull

sudo systemctl restart sema

echo "Update complete."
```

health.sh:

```bash
#!/bin/bash

echo "=== SEMA SERVICE ==="
systemctl status sema --no-pager

echo
echo "=== WIFI WATCH TIMER ==="
systemctl status sema-wifi-watch.timer --no-pager

echo
echo "=== NETWORK ==="
nmcli device

echo
echo "=== TAILSCALE ==="
tailscale status

echo
echo "=== IP ADDRESSES ==="
ip -4 addr
```

logs.sh:

```bash
#!/bin/bash

journalctl -u sema -f
```

Práva:

```bash
chmod +x scripts/*.sh
```

---

# 29. Default účty

User:

```text
username: user
password: sema-eco
```

Admin:

```text
username: admin
password: KatkaMarekMatej
```

---

# 30. Diagnostika

SEMA log:

```bash
journalctl -u sema -f
```

Status služby:

```bash
sudo systemctl status sema --no-pager
```

Nginx:

```bash
sudo systemctl status nginx --no-pager
```

WiFi:

```bash
nmcli device
```

Tailscale:

```bash
tailscale status
```

IP adresy:

```bash
ip addr
```

---

# 31. Overenie úspešného nasadenia

Musí fungovať:

- Dashboard
- Grafy
- Login
- Settings
- Tailscale
- Ethernet komunikácia s čerpadlom
- AP fallback
- WifiSetup
- Git update workflow
- Nginx reverse proxy

Ak všetky body fungujú, nasadenie je úspešné.

---

# 32. Automatické generovanie SSH host keys

Cieľ:

Po flashnutí Golden Image musí každé zariadenie automaticky vygenerovať vlastné unikátne SSH host keys.

SSH host keys sa pred vytvorením image zámerne odstránia:

```bash
sudo rm /etc/ssh/ssh_host_*
```

Aby SSH fungovalo bez manuálneho zásahu po prvom boote, vytvorí sa firstboot skript a systemd väzba pred štartom SSH služby.

---

## Firstboot skript

Súbor:

```bash
/usr/local/bin/sema-firstboot.sh
```

Vytvorenie:

```bash
sudo nano /usr/local/bin/sema-firstboot.sh
```

Obsah:

```bash
#!/bin/bash

set -e

if ! ls /etc/ssh/ssh_host_* >/dev/null 2>&1; then
    echo "SSH host keys not found. Generating..."
    ssh-keygen -A
fi
```

Práva:

```bash
sudo chmod +x /usr/local/bin/sema-firstboot.sh
```

---

## Firstboot systemd služba

Súbor:

```bash
/etc/systemd/system/sema-firstboot.service
```

Vytvorenie:

```bash
sudo nano /etc/systemd/system/sema-firstboot.service
```

Obsah:

```ini
[Unit]
Description=SEMA First Boot Tasks
Before=ssh.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/sema-firstboot.sh

[Install]
WantedBy=multi-user.target
```

---

## SSH override

Súbor:

```bash
/etc/systemd/system/ssh.service.d/override.conf
```

Vytvorenie:

```bash
sudo systemctl edit ssh.service
```

Obsah:

```ini
[Unit]
Requires=sema-firstboot.service
After=sema-firstboot.service
```

Pozor:

Do override súboru vložiť iba uvedený blok nad riadok:

```text
### Edits below this comment will be discarded
```

---

## Aktivácia

```bash
sudo systemctl daemon-reload
sudo systemctl enable sema-firstboot.service
```

---

## Test

```bash
sudo rm /etc/ssh/ssh_host_*
sudo reboot
```

Po reboote overiť:

```bash
ls -l /etc/ssh/ssh_host_*
systemctl status ssh --no-pager
```

Očakávaný výsledok:

```text
SSH host keys existujú
ssh.service je active (running)
```

---

## Výsledok

Po flashnutí Golden Image:

```text
Boot
↓
sema-firstboot.service
↓
ssh-keygen -A
↓
ssh.service
↓
SSH funguje bez manuálneho zásahu
```

# 33. Golden Image

Pred vytvorením image:

### Tailscale

Odhlásenie:

```bash
sudo tailscale logout
```

Zastavenie služby:

```bash
sudo systemctl stop tailscaled
```

Odstránenie súborov:

```bash
sudo rm -rf /var/lib/tailscale
```

### Wifi

Odstrániť zákaznícke WiFi profily:

```bash
sudo nmcli connection delete NAZOV_WIFI
```

### SSH

Vymazať SSH host keys:

```bash
sudo rm /etc/ssh/ssh_host_*
```

Po prvom boote budú automaticky vygenerované službou:

```text
sema-firstboot.service
```

### DB

Vyčistiť databázu na default stav.

```bash
rm ~/sema/backend/data.db
```

### Vypnutie

Vypnúť Raspberry:

```bash
sudo shutdown now
```

### Complete Cleanup

```bash
sudo tailscale logout
sudo systemctl stop tailscaled
sudo rm -rf /var/lib/tailscale
sudo nmcli connection delete SEKAN
sudo rm /etc/ssh/ssh_host_*
rm ~/sema/backend/data.db
sudo shutdown now
```

Vytvoriť image SD karty.

Výsledok:

```text
SEMA-OS-v1.0.img
```

Prvé spustenie novej jednotky:

```text
Boot
↓
SEMA-Setup AP
↓
WifiSetup
↓
Pripojenie do siete
↓
tailscale up
↓
Hotovo
```
