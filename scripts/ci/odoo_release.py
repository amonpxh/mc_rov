"""Propone entregas Odoo desde commits; nunca instala ni ejecuta el manifiesto."""

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
from datetime import date


FILES = {"__manifest__.py", "CHANGELOG.md", ".odoo-release.json"}
PRODUCT = (
    "models/",
    "wizards/",
    "views/",
    "data/",
    "security/",
    "reports/",
    "static/src/",
    "migrations/",
    "controllers/",
    "i18n/",
    "static/lib/",
    "static/description/",
)
VERSION = re.compile(r"19\.0\.(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
SUBJECT = re.compile(r"(feat|fix|perf|refactor|style|data|chore)(\([^\r\n()]+\))?(!)?: \S[^\r\n]*")
MANIFEST = re.compile(r"([\'\"]version[\'\"]\s*:\s*[\'\"])(19\.0\.\d+\.\d+\.\d+)([\'\"])")


def git(root, *args):
    """Git recibe argumentos separados: ningún título o nombre se evalúa en shell."""
    result = subprocess.run(
        ["git", "-c", "safe.directory=" + Path(root).resolve().as_posix(), "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise ValueError("Git no pudo verificar la base o el estado solicitado")
    return result.stdout.strip()


def next_version(version, kinds):
    """Conserva el prefijo Odoo y aplica la ruptura antes que una función o corrección."""
    match = VERSION.fullmatch(version)
    if not match:
        raise ValueError("Formato de versión Odoo no válido")
    x, y, z = map(int, match.groups())
    if not kinds:
        return None
    if set(kinds) - {"breaking", "feat", "fix"}:
        raise ValueError("Clasificación de entrega no válida")
    if "breaking" in kinds:
        return f"19.0.{x + 1}.0.0"
    if "feat" in kinds:
        return f"19.0.{x}.{y + 1}.0"
    return f"19.0.{x}.{y}.{z + 1}"


def load_state(root):
    """El estado acredita la última base de cálculo, no una instalación en producción."""
    state = json.loads((Path(root) / ".odoo-release.json").read_text(encoding="utf-8"))
    if state.get("schema") != 1 or not re.fullmatch(r"[0-9a-f]{40}", state.get("source", "")):
        raise ValueError("Estado de entrega no válido")
    next_version(state["version"], [])
    if not isinstance(state.get("overrides", {}), dict):
        raise ValueError("Excepciones históricas no válidas")
    for sha, kind in state.get("overrides", {}).items():
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or kind not in {"breaking", "feat", "fix"}:
            raise ValueError("Clasificación histórica no válida")
    return state


def manifest_version(text):
    """literal_eval permite comentarios Python pero no ejecutar código del módulo."""
    version = ast.literal_eval(text)["version"]
    next_version(version, [])
    if len(MANIFEST.findall(text)) != 1:
        raise ValueError("El manifiesto no tiene una única versión actualizable")
    return version


def collect_entries(root, state, source):
    """Clasifica solo commits que modifican producto y conserva excepciones explícitas."""
    commits = git(root, "rev-list", "--first-parent", "--reverse", state["source"] + ".." + source)
    entries = []
    for sha in commits.splitlines():
        paths = git(
            root, "diff-tree", "--no-commit-id", "--no-renames", "--name-only", "-r", sha
        ).splitlines()
        if not any(
            p.startswith(PRODUCT)
            or ("/" not in p and p.endswith(".py"))
            or p in {"requirements.txt", "requirements.lock"}
            for p in paths
        ):
            continue
        subject = git(root, "show", "-s", "--format=%s", sha)
        # El commit de entrega solo contiene artefactos generados, nunca producto adicional.
        if re.fullmatch(r"chore\(release\): 19\.0\.\d+\.\d+\.\d+(?: \(#\d+\))?", subject):
            if not set(paths) <= FILES:
                raise ValueError("Un commit de entrega contiene cambios de producto")
            continue
        match = SUBJECT.fullmatch(subject)
        kind = state.get("overrides", {}).get(sha)
        if kind is None:
            if match is None:
                raise ValueError(
                    "Falta clasificación explícita del commit de producto " + sha[:12]
                )
            body = git(root, "show", "-s", "--format=%b", sha)
            breaking = match.group(3) or re.search(r"^BREAKING[ -]CHANGE: \S", body, re.M)
            kind = "breaking" if breaking else ("feat" if match.group(1) == "feat" else "fix")
        entries.append({"sha": sha, "subject": subject, "kind": kind})
    return entries


def render_notes(version, entries, today):
    """Genera notas nuevas sin reescribir las entradas anteriores del CHANGELOG."""
    today = today or date.today().isoformat()
    date.fromisoformat(today)
    notes = f"## [{version}] — {today}\n\n"
    for kind, heading in [
        ("breaking", "Cambios incompatibles"),
        ("feat", "Funcionalidades"),
        ("fix", "Correcciones y mejoras"),
    ]:
        selected = [e for e in entries if e["kind"] == kind]
        if selected:
            notes += f"### {heading}\n\n"
            for entry in selected:
                title = re.sub(r"([\\`\[\]<>])", r"\\\1", entry["subject"])
                notes += f"- {title} (`{entry['sha'][:12]}`).\n"
            notes += "\n"
    notes += "Entrega de código; no acredita instalación ni activación en producción.\n\n"
    return notes


def plan_release(root, today=None):
    """Devuelve un plan de tres archivos o None; no modifica el checkout."""
    root = Path(root)
    state = load_state(root)
    manifest = (root / "__manifest__.py").read_text(encoding="utf-8")
    if manifest_version(manifest) != state["version"]:
        raise ValueError("La versión del manifiesto y el estado divergen")
    source = git(root, "rev-parse", "HEAD")
    git(root, "merge-base", "--is-ancestor", state["source"], source)
    entries = collect_entries(root, state, source)
    version = next_version(state["version"], [e["kind"] for e in entries])
    if version is None:
        return None
    notes = render_notes(version, entries, today)
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if not changelog.startswith("# Changelog\n") or f"## [{version}]" in changelog:
        raise ValueError("CHANGELOG divergente o versión ya registrada")
    proposed = {**state, "version": version, "source": source}
    return {
        "version": version,
        "source": source,
        "title": "chore(release): " + version,
        "notes": notes,
        "entries": entries,
        "files": {
            "__manifest__.py": MANIFEST.sub(lambda m: m[1] + version + m[3], manifest),
            "CHANGELOG.md": "# Changelog\n\n"
            + notes
            + changelog[len("# Changelog\n") :].lstrip("\n"),
            ".odoo-release.json": json.dumps(proposed, indent=2, ensure_ascii=False) + "\n",
        },
    }


def apply_plan(root, plan):
    """Solo aplica sobre el mismo HEAD limpio usado para generar el plan."""
    if set(plan["files"]) != FILES or git(root, "rev-parse", "HEAD") != plan["source"]:
        raise ValueError("Plan obsoleto o archivos fuera de alcance")
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("El checkout tiene cambios locales")
    for name, content in plan["files"].items():
        (Path(root) / name).write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    plan = plan_release(args.root)
    if plan and args.apply:
        apply_plan(args.root, plan)
    output = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
