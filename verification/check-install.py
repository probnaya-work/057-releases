"""Black-box checks of public release bytes, only on disposable GitHub runners.

No application source, signing credentials or real user telemetry is needed.
Direct executable launch tests runtime startup, not Finder/Gatekeeper interaction.
"""
import hashlib
import json
import os
import platform
import plistlib
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Disposable CI only; never run against a user account'
assert os.environ.get('GITHUB_REPOSITORY') == 'probnaya-work/057-releases'
assert platform.system() == 'Darwin' and platform.machine() == 'arm64'
VERSION = '1.6.0'
DMG_SHA = '1c64b00b74f26381109fe8f2be0fbdd728e748bf4f826e4c895bc00148a135dd'
APP = Path('/Applications/057.app')
USER_DIR = Path.home()
STORE = USER_DIR / '.057/events.db'
RECORD = Path(str(STORE) + '.core.json')
LOG = USER_DIR / 'Library/Logs/057/core.log'
assert not APP.exists() and not STORE.parent.exists(), 'Runner must have no previous 057 installation or history'
assert not any(k.startswith('O57_') for k in os.environ), 'No test-specific 057 settings'
results = []
scratch = Path(tempfile.mkdtemp(prefix='057-install-'))
app_process = None
log_offset = 0
mounted = False
mount = scratch / 'volume'


def checked(label, detail=''):
    results.append({'check': label, 'result': 'pass', 'detail': detail})
    print('PASS:', label, detail, flush=True)


def run(*args, timeout=90, required=True):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if required and result.returncode:
        raise RuntimeError(f'{args[0]} exited {result.returncode}: {result.stdout[-4000:]}')
    return result


def get(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def until(predicate, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.5)
    raise TimeoutError('Timed out waiting for ' + predicate.__name__)


def ready():
    if app_process.poll() is not None:
        raise RuntimeError(f'Native app exited {app_process.returncode}')
    try:
        record = json.loads(RECORD.read_text())
        health = json.loads(get(record['url'] + '/api/health'))
        log = LOG.read_text()[log_offset:]
        if health['version'] == VERSION and health['health']['ok'] and 'health LIVE' in log and 'first landscape' in log:
            return record, health
    except (OSError, ValueError, KeyError):
        pass
    return None


def start():
    global app_process, log_offset
    log_offset = len(LOG.read_text()) if LOG.exists() else 0
    output = (scratch / 'app-output.log').open('a')
    app_process = subprocess.Popen([str(APP / 'Contents/MacOS/057')], stdout=output, stderr=subprocess.STDOUT)
    output.close()
    return until(ready)


def stop(core_pid):
    app_process.terminate()  # Test process shutdown/pipe ownership, not the menu's Quit action.
    app_process.wait(timeout=15)
    until(lambda: not alive(core_pid) and not RECORD.exists(), 20)


try:
    checked('Fresh Apple silicon runner', run('sw_vers', '-productVersion').stdout.strip())
    dmg = scratch / f'057-{VERSION}-arm64.dmg'
    dmg.write_bytes(get(f'https://057.probnaya.work/releases/{VERSION}/{dmg.name}'))
    assert hashlib.sha256(dmg.read_bytes()).hexdigest() == DMG_SHA
    checked('Published DMG matches release SHA-256')
    run('hdiutil', 'verify', str(dmg))
    run('codesign', '--verify', '--strict', str(dmg))
    run('xcrun', 'stapler', 'validate', str(dmg))
    checked('DMG integrity, signature and stapled ticket')
    run('hdiutil', 'attach', '-readonly', '-nobrowse', '-mountpoint', str(mount), str(dmg))
    mounted = True
    assert (mount / 'Applications').is_symlink()
    run('ditto', str(mount / '057.app'), str(APP))
    run('hdiutil', 'detach', str(mount))
    mounted = False
    with (APP / 'Contents/Info.plist').open('rb') as handle:
        info = plistlib.load(handle)
    assert info['CFBundleShortVersionString'] == VERSION and str(info['CFBundleVersion']) == '299'
    assert info['CFBundleIdentifier'] == 'work.probnaya.057'
    run('codesign', '--verify', '--strict', '--deep', str(APP))
    signature = run('codesign', '-dv', '--verbose=4', str(APP)).stdout
    assert 'TeamIdentifier=PQC9LY4W26' in signature and 'runtime' in signature
    run('xcrun', 'stapler', 'validate', str(APP))
    checked('Installed app version, nested Developer ID signatures, hardened runtime and ticket')
    policy = run('spctl', '--status', required=False).stdout.strip()
    assessment = run('spctl', '--assess', '--type', 'execute', '--verbose=4', str(APP), required=False)
    if assessment.returncode == 0 and 'Notarized Developer ID' in assessment.stdout:
        checked('Explicit Gatekeeper assessment', policy + '; Notarized Developer ID')
    else:
        results.append({'check': 'Explicit Gatekeeper assessment', 'result': 'not-passed',
                        'detail': policy + '; ' + assessment.stdout[-1000:]})
        print('NOT PASSED: explicit Gatekeeper assessment:', policy, assessment.stdout, flush=True)
    core, health = start()
    checked('Ordinary native executable starts its bundled Core and reaches LIVE with a landscape')
    assert health['health']['store']['ok'] and not health['health']['failingSources']
    assert STORE.exists() and STORE.stat().st_mode & 0o777 == 0o600
    assert STORE.parent.stat().st_mode & 0o777 == 0o700
    checked('Default history location, permissions and healthy observation')
    base = core['url']
    state = json.loads(get(base + '/api/state'))
    assert state['mode'] == 'os-only', state.get('mode')
    checked('No harness history is reported as OS-only')
    assert b'<div id="root">' in get(base + '/')
    for days in [1, 7]:
        report = json.loads(get(base + f'/api/analysis?days={days}'))
        assert report['schemaVersion'] == '057.analysis.v1'
        assert report['runs']['records'] == 0 and report['runs']['items'] == []
        assert report['findings']['findings'] == []
    checked('Browser surface and 1-day/7-day Analysis answer; no fabricated runs or findings')
    second = run(str(APP / 'Contents/MacOS/057'), timeout=20)
    assert json.loads(RECORD.read_text())['pid'] == core['pid'] and app_process.poll() is None
    checked('Second native launch exits successfully and keeps the original Core')
    stop(core['pid'])
    checked('Terminating app stops its Core and removes discovery record')
    inode = STORE.stat().st_ino
    core2, _ = start()
    assert STORE.stat().st_ino == inode and core2['pid'] != core['pid']
    checked('Native relaunch reuses the existing history with a new healthy Core')
    stop(core2['pid'])
    assert all(item['result'] == 'pass' for item in results), 'At least one gate did not pass; see summary'
finally:
    if app_process is not None and app_process.poll() is None:
        app_process.terminate()
    if mounted:
        run('hdiutil', 'detach', str(mount), required=False)
    summary = Path(os.environ['GITHUB_STEP_SUMMARY'])
    with summary.open('a') as handle:
        handle.write('# Published 057 1.6.0 install verification\n\n')
        for item in results:
            handle.write(f"- **{item['result']}**: {item['check']} {item['detail']}\n")
        handle.write('\nLimits: automated runner, direct executable launch, online. No browser quarantine, '
                     'Finder drag/drop, first-open dialog, visual frame assessment or offline first launch claimed.\n')
    # Only the fresh runner's app diagnostics. Never print its discovery/control token or environment.
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            if any(marker in line for marker in ['health ', 'first landscape', 'Core stopped', 'error', 'Error']):
                print(line[-1000:])
