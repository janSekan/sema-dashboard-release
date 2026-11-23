#!/usr/bin/python3
"""Fixed root-owned recovery installation. Does not change app, sudoers or network."""
import ast
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

FILES = {'update_manager.py':Path('/usr/local/lib/sema-update/update_manager.py'),
         'sema-update-recovery.service':Path('/etc/systemd/system/sema-update-recovery.service'),
         'sema-update-recovery.timer':Path('/etc/systemd/system/sema-update-recovery.timer')}
TIMER = 'sema-update-recovery.timer'


def execute(*args):
    return subprocess.run(args,check=True,capture_output=True,timeout=15)


def install(source, files=FILES, backups=Path('/var/backups')):
    ast.parse((source/'update_manager.py').read_text())
    execute('systemd-analyze','verify',str(source/'sema-update-recovery.service'),str(source/'sema-update-recovery.timer'))
    active=subprocess.run(['systemctl','is-active','--quiet',TIMER],check=False,capture_output=True).returncode==0
    enabled=subprocess.run(['systemctl','is-enabled','--quiet',TIMER],check=False,capture_output=True).returncode==0
    backup=Path(tempfile.mkdtemp(prefix='sema-update-guard-',dir=backups))
    for name,dest in files.items():
        if dest.exists() or dest.is_symlink():shutil.copy2(dest,backup/name,follow_symlinks=False)
    try:
        for name,dest in files.items():
            if dest.is_symlink():raise ValueError('Refusing symlink destination')
            if dest.parent.is_symlink():raise ValueError('Refusing symlink directory')
            dest.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
            # Explicit mode: mkdir(0755) is reduced to0700 by our private umask.
            # Only public program code is made traversable; backups stay private.
            if name=='update_manager.py':dest.parent.chmod(0o755)
            # Replace instead of rewriting a live Python file in place.
            fd,temp=tempfile.mkstemp(dir=dest.parent,prefix='.install-')
            try:
                with os.fdopen(fd,'wb') as out:
                    out.write((source/name).read_bytes());out.flush();os.fsync(out.fileno())
                os.chmod(temp,0o644);os.replace(temp,dest)
            finally:Path(temp).unlink(missing_ok=True)
        # Verify access as the actual service user, not as this root installer.
        execute('/usr/sbin/runuser','-u','jan','--','/usr/bin/python3','-c',
                'import pathlib,sys; p=pathlib.Path(sys.argv[1]); compile(p.read_bytes(),str(p),"exec")',
                str(files['update_manager.py']))
        execute('systemctl','daemon-reload')
        execute('systemctl','enable',TIMER)
        execute('systemctl','restart',TIMER)
        execute('systemctl','is-active','--quiet',TIMER)
    except BaseException:
        for name,dest in files.items():
            dest.unlink(missing_ok=True)
            if (backup/name).exists() or (backup/name).is_symlink():shutil.copy2(backup/name,dest,follow_symlinks=False)
        execute('systemctl','daemon-reload')
        if not enabled:subprocess.run(['systemctl','disable',TIMER],capture_output=True,check=False)
        subprocess.run(['systemctl','restart' if active else 'stop',TIMER],capture_output=True,check=False)
        raise
    print('UPDATE_RECOVERY_GUARD_OK backup='+str(backup))


if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Explicit root installation required')
    os.umask(0o077)
    install(Path(__file__).resolve().parent)
