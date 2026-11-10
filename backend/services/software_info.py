"""Installed software identity. No network access and no writes to device state."""
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import subprocess
from services.device_info import get_versions

ROOT = Path(__file__).resolve().parents[2]
CHANNEL_PATHS = (Path('/etc/sema/update-channel'), Path.home()/'.config/sema/update-channel')


@lru_cache(maxsize=1)
def release_commit():
    if os.getenv('APP_ENV') == 'development':
        return None
    try:
        result = subprocess.run(['git','-C',str(ROOT),'rev-parse','HEAD'], capture_output=True,
                                text=True,timeout=2,check=False)
        value = result.stdout.strip()
        return value if result.returncode == 0 and re.fullmatch('[0-9a-f]{40}',value) else None
    except (OSError,subprocess.TimeoutExpired):
        return None


@lru_cache(maxsize=1)
def build_identity():
    # Freeze identity for this process: git reset may replace files before restart.
    versions = get_versions()
    version = versions.get('dashboard') if isinstance(versions,dict) else None
    built_at = None
    try:
        metadata = json.loads((ROOT/'release.json').read_text())
        if metadata.get('version') == version:
            built_at = metadata.get('built_at')
    except (OSError,ValueError,AttributeError):
        pass
    return dict(version=version,release_commit=release_commit(),built_at=built_at)


def software_info():
    channel = None if os.getenv('APP_ENV') == 'development' else 'main'
    try:
        for path in CHANNEL_PATHS:
            if path.exists():
                value = path.read_text().strip()
                channel = value if value in ('main','testing') else None
                break
    except OSError:
        channel = None
    return {**build_identity(), 'channel':channel}
