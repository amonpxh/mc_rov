"""Activa únicamente un lote F2 congelado; se ejecuta desde el terminal del usuario."""

# Protocolo CLI del activador; no imprimir secretos.
# pylint: disable=unknown-option-value,print-used

import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

from detention_access import runner_source


def sha(data):
    """Huella de los bytes que realmente se transportan."""
    return hashlib.sha256(data).hexdigest()


def check(folder):
    """Ni un cambio en pruebas, ejecutor o acceso permite activar otra versión."""
    prepared = json.loads((folder / "prepared.json").read_text(encoding="utf-8"))
    assert (prepared["phase"], prepared["tests"], prepared["races"]) in (
        ("races-green", 35, 8),
        ("events-characterization", 45, 0),
        ("events-green", 45, 10),
        ("interface-red", 69, 0),
        ("interface-green", 69, 10),
        ("interface-browser", 7, 0),
    )
    assert prepared["isolated_test_version"] == "19.0.25.9.0"
    for name, digest in prepared["files"].items():
        assert sha((folder / name).read_bytes()) == digest, name
    for name, digest in json.loads((folder / "access-files.json").read_text()).items():
        assert sha((folder / name).read_bytes()) == digest, name
    return prepared


def activate(folder):
    """Una clave por activación; no reutiliza claves revocadas ni ejecuta pruebas."""
    prepared = check(folder)
    access = folder / "temporary-access"
    access.mkdir(exist_ok=False)
    account = subprocess.check_output(["whoami"], text=True).strip()
    subprocess.run(
        [
            "icacls",
            str(access),
            "/inheritance:r",
            "/grant:r",
            account + ":(OI)(CI)F",
            "SYSTEM:(OI)(CI)F",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    key = access / "id_ed25519"
    token = uuid.uuid4().hex
    subprocess.run(
        [
            "ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "mc-rov-f2-" + token,
            "-f",
            str(key),
        ],
        check=True,
    )
    public = key.with_suffix(".pub").read_text().strip().split()
    assert len(public) == 3 and public[0] == "ssh-ed25519"
    root = "/root/mc-rov-f2-access-" + token
    remote = "/var/tmp/mc-rov-detention-races-" + token
    files = {name: (folder / name).read_bytes() for name in prepared["files"]}
    files["run.py"] = runner_source(token, prepared["files"]).encode()
    wire = 'set -euo pipefail\numask 077\ntest "$(id -u)" = 0\n'
    wire += "test ! -L /root/.ssh\ninstall -d -m 700 /root/.ssh\ntest ! -L /root/.ssh/authorized_keys\n"
    wire += "mkdir '" + root + "' '" + remote + "'\nchmod 700 '" + root + "' '" + remote + "'\n"
    for name, data in files.items():
        target = root if name == "run.py" else remote
        wire += (
            "printf '%s' '"
            + base64.b64encode(data).decode()
            + "' | base64 -d > '"
            + target
            + "/"
            + name
            + "'\n"
        )
        wire += (
            "printf '%s  %s\\n' '"
            + sha(data)
            + "' '"
            + target
            + "/"
            + name
            + "' | sha256sum -c -\n"
        )
    wire += "python3 - <<'F2_ACCESS_PY'\nimport datetime,fcntl,os,pathlib,time\n"
    wire += "root=pathlib.Path(" + repr(root) + ")\nexpires=int(time.time())+7200\n"
    wire += "(root/'expires').write_text(str(expires))\n"
    wire += "stamp=datetime.datetime.fromtimestamp(expires,datetime.timezone.utc).strftime('%Y%m%d%H%M%SZ')\n"
    line = (
        'restrict,expiry-time="STAMP",command="/usr/bin/python3 -I '
        + root
        + '/run.py" '
        + " ".join(public)
    )
    wire += "line=" + repr(line) + ".replace('STAMP',stamp).encode()+b'\\n'\n"
    wire += "with open('/root/.ssh/mc-rov-f2-access.lock','a') as lock:\n"
    wire += "    fcntl.flock(lock,fcntl.LOCK_EX)\n    auth=pathlib.Path('/root/.ssh/authorized_keys')\n"
    wire += "    data=auth.read_bytes() if auth.exists() else b''\n    with auth.open('ab') as output:\n"
    wire += "        if data and not data.endswith(b'\\n'): output.write(b'\\n')\n        output.write(line)\n"
    wire += "    os.chmod(auth,0o600)\n    (root/'authorized-line').write_bytes(line)\n"
    wire += "print('F2_TEMPORARY_ACCESS_READY=True EXPIRES_UTC='+stamp)\nF2_ACCESS_PY\n"
    (access / "bootstrap.sh").write_bytes(wire.encode())
    (access / "access.json").write_bytes(
        (
            json.dumps(
                {
                    "key_path": str(key),
                    "token": token,
                    "package_hashes": prepared["files"],
                    "duration_seconds": 7200,
                    "commands": ["run-f2", "status-f2", "revoke-f2"],
                },
                indent=2,
            )
            + "\n"
        ).encode()
    )
    print("F2_ACCESS_LOCAL_PREPARED=True SSH_EXECUTED=False")


if __name__ == "__main__":
    target_folder = Path(__file__).resolve().parent
    if sys.argv[1:] == ["--check"]:
        check(target_folder)
        print("F2_ACCESS_LOCAL=PASSED SSH_EXECUTED=False")
    elif sys.argv[1:] == ["--activate"]:
        activate(target_folder)
    else:
        sys.exit("Usar únicamente el activador revisado")
