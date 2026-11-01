"""Advertise only enabled HA API on selected LAN interfaces, without credentials."""
import asyncio
from ipaddress import ip_address, ip_network
import logging
import os
from uuid import UUID

SERVICE_TYPE = '_sema._tcp.local.'
LOG = logging.getLogger(__name__)


def lan_addresses():
    """Default SEMA customer LAN is wlan0; pump Ethernet/VPN are not advertised."""
    import ifaddr

    names = {name.strip() for name in os.getenv('SEMA_HA_DISCOVERY_INTERFACES', 'wlan0').split(',') if name.strip()}
    result = set()
    for adapter in ifaddr.get_adapters():
        if adapter.name not in names and adapter.nice_name not in names:
            continue
        for address in adapter.ips:
            if not isinstance(address.ip, str):
                continue  # IPv6 can be added later; publish real reachable IPv4 now.
            ip = ip_address(address.ip)
            if (ip.version == 4 and not ip.is_loopback and not ip.is_unspecified
                    and not ip.is_multicast and not ip.is_link_local
                    and ip not in ip_network('100.64.0.0/10')):
                result.add(str(ip))
    return sorted(result)


def service_info(uid, addresses, port, scheme):
    from zeroconf import ServiceInfo

    uid = str(UUID(uid))
    return ServiceInfo(SERVICE_TYPE, f'SEMA {uid}.{SERVICE_TYPE}',
        addresses=[ip_address(address).packed for address in addresses], port=port,
        server=f'sema-{UUID(uid).hex}.local.',
        properties={'device_uid': uid, 'api_version': '1', 'scheme': scheme})


def zeroconf_instance(addresses):
    from zeroconf import IPVersion
    from zeroconf.asyncio import AsyncZeroconf

    return AsyncZeroconf(interfaces=addresses, ip_version=IPVersion.V4Only)


class HADiscovery:
    def __init__(self, store):
        self.store = store
        self._wake = asyncio.Event()
        self._zc = None
        self._service = None
        self._signature = None

    def notify(self):
        """Called on the event loop after token creation/rotation/revocation."""
        self._wake.set()

    async def reconcile(self):
        data = await asyncio.to_thread(self.store.read)
        if not data.get('token_hash') or data.get('scope') != 'read':
            await self.close()
            return
        addresses = await asyncio.to_thread(lan_addresses)
        if not addresses:
            await self.close()
            return
        port = int(os.getenv('SEMA_HA_DISCOVERY_PORT', '80'))
        scheme = os.getenv('SEMA_HA_DISCOVERY_SCHEME', 'http')
        if not 1 <= port <= 65535 or scheme not in ('http', 'https'):
            raise ValueError('Invalid HA discovery endpoint')
        uid = str(UUID(data['device_uid']))
        signature = (uid, tuple(addresses), port, scheme)
        if signature == self._signature:
            return
        await self.close()
        info = service_info(uid, addresses, port, scheme)
        self._zc = zeroconf_instance(addresses)
        try:
            # Zeroconf returns an announcement task; await it for a clean lifecycle.
            announcement = await self._zc.async_register_service(info)
            await announcement
        except BaseException:
            await self.close()
            raise
        self._service = info
        self._signature = signature

    async def close(self):
        zc, self._zc = self._zc, None
        self._service = None
        self._signature = None
        if zc is not None:
            try:
                await zc.async_unregister_all_services()
            finally:
                await zc.async_close()

    async def run(self):
        failed = False
        try:
            while True:
                self._wake.clear()
                try:
                    await self.reconcile()
                    failed = False
                except Exception:
                    # Optional discovery must not break the API. Do not log config/credentials.
                    await self.close()
                    if not failed:
                        LOG.warning('HA discovery unavailable; manual address setup remains available')
                    failed = True
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=30)
                except TimeoutError:
                    pass
        finally:
            await self.close()
