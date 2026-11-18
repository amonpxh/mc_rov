"""Genera un ejecutor SSH efímero para un único lote F2 congelado."""

import re


def runner_source(token, hashes):
    """Ningún comando del cliente se interpola en el proceso privilegiado."""
    assert re.fullmatch(r"[a-f0-9]{32}", token)
    assert hashes and all(
        re.fullmatch(r"[a-zA-Z0-9_.-]+", name) and re.fullmatch(r"[a-f0-9]{64}", digest)
        for name, digest in hashes.items()
    )
    return """import fcntl, hashlib, json, os, pathlib, subprocess, sys, tempfile, time
ROOT = pathlib.Path("/root/mc-rov-f2-access-TOKEN")
PAYLOAD = pathlib.Path("/var/tmp/mc-rov-detention-races-TOKEN")
HASHES = HASH_VALUES
command = os.environ.get("SSH_ORIGINAL_COMMAND", "")
if command not in ("run-f2", "status-f2", "revoke-f2"):
    sys.exit("Comando no autorizado")
if time.time() >= int((ROOT / "expires").read_text()):
    sys.exit("Acceso caducado")
if command == "revoke-f2":
    auth = pathlib.Path("/root/.ssh/authorized_keys")
    if auth.is_symlink() or auth.parent.is_symlink():
        sys.exit("Ruta SSH insegura")
    with (auth.parent / "mc-rov-f2-access.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        line = (ROOT / "authorized-line").read_bytes().rstrip(b"\\r\\n")
        remaining = b"".join(row for row in auth.read_bytes().splitlines(keepends=True) if row.rstrip(b"\\r\\n") != line)
        descriptor, temporary = tempfile.mkstemp(prefix=".f2-revoke-", dir=str(auth.parent))
        try:
            with os.fdopen(descriptor, "wb") as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(remaining)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, auth)
            directory = os.open(str(auth.parent), os.O_DIRECTORY)
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    print("F2_ACCESS_REVOKED=True", flush=True)
    sys.exit(0)
if command == "status-f2":
    print("F2_ACCESS_ATTEMPTED=" + str((ROOT / "attempted").exists()), flush=True)
    result = ROOT / "result.txt"
    if result.exists():
        if result.stat().st_size > 12000000: sys.exit("Evidencia excede el límite")
        sys.stdout.write(result.read_text())
    sys.exit(0)
for directory in (ROOT, PAYLOAD):
    info = directory.lstat()
    if directory.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
        sys.exit("Directorio inseguro")
for name, expected in HASHES.items():
    file = PAYLOAD / name
    info = file.lstat()
    if file.is_symlink() or info.st_uid != 0 or info.st_mode & 0o022:
        sys.exit("Archivo inseguro")
    if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
        sys.exit("Paquete modificado")
try: (ROOT / "attempted").mkdir()
except FileExistsError: sys.exit("Intento consumido: consultar resultado y diagnosticar")
environment = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "HOME": "/root", "LANG": "C.UTF-8"}
# Un supervisor separado conserva resultado y cleanup si se desconecta el cliente.
supervisor = "import pathlib,subprocess,sys; p=subprocess.run(['/bin/bash',sys.argv[1]+'/run.sh',sys.argv[1]],stdin=subprocess.DEVNULL); pathlib.Path(sys.argv[2]).write_text(str(p.returncode)); print('F2_ACCESS_EXIT_CODE='+str(p.returncode),flush=True)"
with (ROOT / "result.txt").open("x") as output:
    subprocess.Popen(["/usr/bin/python3", "-I", "-c", supervisor, str(PAYLOAD), str(ROOT / "exit-code")], stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, env=environment, start_new_session=True, cwd=str(ROOT))
print("F2_ACCESS_STARTED=True", flush=True)
""".replace(
        "TOKEN", token
    ).replace(
        "HASH_VALUES", repr(hashes)
    )
