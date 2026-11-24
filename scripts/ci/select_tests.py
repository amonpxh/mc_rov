"""Selecciona pruebas desde el diff completo del commit de CI."""

import argparse
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import unquote, urlsplit


def is_doc(path):
    """Admite solo Markdown en ubicaciones reservadas a documentación."""
    return path in {
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "CHANGELOG.md",
        "INVENTARIO.md",
    } or (path.startswith("docs/") and path.endswith(".md"))


def profile(paths):
    """Solo casos conocidos pueden omitir parte de la regresión."""
    changed = set(paths)
    product = changed - {path for path in changed if is_doc(path)}
    if not changed:
        return "full"
    if not product:
        return "docs"
    unit = {path for path in product if re.fullmatch(r"tests/unit/test_[\w]+\.py", path)}
    if product == unit:
        return "unit"
    if product == {"models/work_kpi_metrics.py"} | (
        unit & {"tests/unit/test_work_kpi_metrics.py"}
    ):
        return "work_kpi"
    return "full"


def git(*args):
    """Devuelve bytes para conservar correctamente nombres con Unicode."""
    return subprocess.check_output(["git", *args])


def check_links(root, filename, lines):
    """Comprueba enlaces relativos agregados y mantiene el destino dentro del repo."""
    root = root.resolve()
    for line in lines:
        for link in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)", line):
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (root / PurePosixPath(filename).parent / unquote(url.path)).resolve()
            if not target.is_relative_to(root) or not target.exists():
                raise ValueError(f"{filename}: destino local inválido: {link}")


def select(base, head, merge_base):
    """Un rango no verificable conserva el perfil integral."""
    if not all(re.fullmatch(r"[a-f0-9]{40}", ref or "") for ref in (base, head)):
        return "full"
    try:
        if git("rev-parse", "HEAD").decode().strip() != head:
            raise ValueError("El checkout no coincide con el HEAD solicitado")
        if merge_base:
            base = git("merge-base", base, head).decode().strip()
        paths = git("diff", "--no-renames", "--name-only", "-z", base, head, "--")
    except subprocess.CalledProcessError:
        return "full"
    changed = [os.fsdecode(path) for path in paths.split(b"\0") if path]
    selected = profile(changed)
    if selected == "docs":
        for path in changed:
            diff = git("diff", "--no-renames", "--unified=0", base, head, "--", path)
            check_links(
                Path.cwd(),
                path,
                (
                    line[1:]
                    for line in diff.decode("utf-8").splitlines()
                    if line.startswith("+") and not line.startswith("+++ ")
                ),
            )
    if selected == "work_kpi" and not merge_base:
        return "full"
    return selected


def main():
    """Publica el perfil y lo deja visible en el log."""
    parser = argparse.ArgumentParser()
    parser.add_argument("base")
    parser.add_argument("head")
    parser.add_argument("--merge-base", action="store_true")
    args = parser.parse_args()
    selected = select(args.base, args.head, args.merge_base)
    print(f"CI_TEST_PROFILE={selected}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"profile={selected}\n")


if __name__ == "__main__":
    main()
