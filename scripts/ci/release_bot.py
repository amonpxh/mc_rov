"""Mantiene un PR de entrega y releases borrador; no integra ni despliega."""

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess

from odoo_release import FILES, git, load_state, manifest_version, plan_release


BRANCH = "ci/release-odoo"
REQUIRED = {
    "pre-commit (hygiene, pylint-odoo, black)",
    "Odoo module tests",
    "Gitleaks (historial)",
}


def checks_ready(checks):
    """Un rerun incompleto o fallido invalida el éxito anterior del mismo control."""
    latest = {}
    for check in checks:
        if check["name"] not in latest or check["id"] > latest[check["name"]]["id"]:
            latest[check["name"]] = check
    return all(
        name in latest
        and latest[name]["status"] == "completed"
        and latest[name]["conclusion"] == "success"
        for name in REQUIRED
    )


def release_commit_version(subject):
    match = re.fullmatch(r"chore\(release\): (19\.0\.\d+\.\d+\.\d+)(?: \(#\d+\))?", subject)
    return match[1] if match else None


def validate_generated(commit, source, changed):
    """No sobrescribir ramas humanas ni usar un título de entrega para ocultar producto."""
    if (
        (commit.get("author") or {}).get("login") != "github-actions[bot]"
        or not release_commit_version(commit["commit"]["message"].splitlines()[0])
        or commit["parents"] != [{"sha": source}]
        or set(changed) != FILES
    ):
        raise ValueError("La rama de entrega no es un artefacto íntegro generado por el bot")


class GitHub:
    """Cliente mínimo sobre gh autenticado por el token efímero del workflow."""

    def __init__(self, repository):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Repositorio no válido")
        self.repository = repository

    def request(self, method, endpoint, payload=None):
        command = ["gh", "api", "--method", method, f"repos/{self.repository}/{endpoint}"]
        if payload is not None:
            command += ["--input", "-"]
        result = subprocess.run(
            command,
            input=json.dumps(payload) if payload is not None else None,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
        )
        if result.returncode:
            raise RuntimeError("GitHub rechazó " + method + " " + endpoint.split("?")[0])
        return json.loads(result.stdout) if result.stdout.strip() else None

    def file(self, path, ref):
        value = self.request("GET", f"contents/{path}?ref={ref}")
        return base64.b64decode(value["content"]).decode("utf-8")


def tag_commit(client, version):
    """Resuelve tags livianos o anotados sin confundir el objeto tag con su código."""
    ref_name = "refs/tags/v" + version
    refs = client.request("GET", "git/matching-refs/tags/v" + version)
    exact = [ref for ref in refs if ref["ref"] == ref_name]
    if not exact:
        return None
    target = exact[0]["object"]
    seen = set()
    while target["type"] == "tag":
        if target["sha"] in seen or len(seen) >= 10:
            raise ValueError("Tag anotado cíclico o demasiado profundo")
        seen.add(target["sha"])
        target = client.request("GET", "git/tags/" + target["sha"])["object"]
    if target["type"] != "commit":
        raise ValueError("El tag de entrega no identifica un commit")
    return target["sha"]


def publish_draft(root, client, sha, state, commit):
    """Solo el merge de entrega exacto y al día puede producir su borrador."""
    subject = commit["commit"]["message"].splitlines()[0]
    version = release_commit_version(subject)
    changed = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", sha).splitlines()
    if (
        version != state["version"]
        or set(changed) != FILES
        or [p["sha"] for p in commit["parents"]] != [state["source"]]
        or manifest_version((Path(root) / "__manifest__.py").read_text(encoding="utf-8"))
        != version
    ):
        raise ValueError("Entrega divergente o desactualizada; no se crea release")
    existing_tag = tag_commit(client, version)
    if existing_tag is not None and existing_tag != sha:
        raise ValueError("El tag ya identifica otro código; no se crea ni mueve la entrega")
    releases = client.request("GET", "releases?per_page=100")
    for release in releases:
        if release["tag_name"] == "v" + version:
            if release["target_commitish"] != sha:
                raise ValueError("La versión ya identifica otro commit; no se mueve la release")
            print("Release existente; no se duplica ni publica")
            return
    changelog = (Path(root) / "CHANGELOG.md").read_text(encoding="utf-8")
    header = f"## [{version}]"
    if not changelog.startswith("# Changelog\n\n" + header):
        raise ValueError("La entrega no encabeza CHANGELOG")
    notes = changelog.split("\n\n", 1)[1].split("\n## [", 1)[0]
    value = client.request(
        "POST",
        "releases",
        {
            "tag_name": "v" + version,
            "target_commitish": sha,
            "name": version,
            "body": notes,
            "draft": True,
        },
    )
    print("Release borrador: " + value["html_url"])


def create_generated_commit(client, sha, plan):
    """Crea objetos Git inmutables, sin mover ninguna referencia compartida."""
    main_commit = client.request("GET", "git/commits/" + sha)
    tree = client.request(
        "POST",
        "git/trees",
        {
            "base_tree": main_commit["tree"]["sha"],
            "tree": [
                {"path": name, "mode": "100644", "type": "blob", "content": content}
                for name, content in plan["files"].items()
            ],
        },
    )
    new_commit = client.request(
        "POST",
        "git/commits",
        {
            "message": plan["title"],
            "tree": tree["sha"],
            "parents": [sha],
            "author": {
                "name": "github-actions[bot]",
                "email": "41898282+github-actions[bot]@users.noreply.github.com",
            },
        },
    )
    return new_commit


def update_proposal(root, client, sha, plan):
    """El lease protege la referencia remota frente a ediciones simultáneas."""
    refs = client.request("GET", "git/matching-refs/heads/" + BRANCH)
    refs = [r for r in refs if r["ref"] == "refs/heads/" + BRANCH]
    old = refs[0]["object"]["sha"] if refs else ""
    owner = client.repository.split("/")[0]
    prs = client.request("GET", f"pulls?state=open&base=main&head={owner}:{BRANCH}&per_page=100")
    if len(prs) > 1:
        raise ValueError("Más de un PR de entrega abierto")
    if old:
        previous = client.request("GET", "commits/" + old)
        prior_state = json.loads(client.file(".odoo-release.json", old))
        comparison = client.request("GET", f"compare/{prior_state['source']}...{old}")
        # La API de commits agrega url/html_url a cada padre: se valida su SHA, no esos metadatos.
        normalized = {**previous, "parents": [{"sha": p["sha"]} for p in previous["parents"]]}
        validate_generated(
            normalized, prior_state["source"], [f["filename"] for f in comparison["files"]]
        )
        if prior_state["source"] == sha and prior_state["version"] == plan["version"] and prs:
            print("PR de entrega ya actualizado: " + prs[0]["html_url"])
            return
        if not prs:
            raise ValueError("Rama de entrega sin PR abierto; revisar antes de reutilizar")
    new_commit = create_generated_commit(client, sha, plan)
    if client.request("GET", "git/ref/heads/main")["object"]["sha"] != sha:
        raise ValueError("Main avanzó; conservar referencias y volver a ejecutar")
    # El checkout del runner usa persist-credentials=false; gh proporciona credenciales efímeras.
    subprocess.run(["gh", "auth", "setup-git"], check=True, capture_output=True)
    git(root, "fetch", "origin", new_commit["sha"])
    git(
        root,
        "push",
        "--force-with-lease=refs/heads/" + BRANCH + ":" + old,
        "origin",
        new_commit["sha"] + ":refs/heads/" + BRANCH,
    )
    body = (
        "Entrega propuesta automáticamente desde main `"
        + sha
        + "`.\n\n"
        + plan["notes"]
        + "\nSin auto-merge ni despliegue. Revisar CI y migraciones antes de integrar. "
        "Si GitHub lo solicita, pulsar Approve workflows to run para ejecutar CI del PR del bot."
    )
    if prs:
        value = client.request(
            "PATCH", "pulls/" + str(prs[0]["number"]), {"title": plan["title"], "body": body}
        )
    else:
        value = client.request(
            "POST",
            "pulls",
            {
                "title": plan["title"],
                "body": body,
                "head": BRANCH,
                "base": "main",
                "draft": True,
            },
        )
    print("PR de entrega: " + value["html_url"])


def run_bot(root, client):
    sha = git(root, "rev-parse", "HEAD")
    if git(root, "status", "--porcelain"):
        raise ValueError("El checkout del bot debe estar limpio")
    main_sha = client.request("GET", "git/ref/heads/main")["object"]["sha"]
    commit = client.request("GET", "commits/" + sha)
    is_release = release_commit_version(commit["commit"]["message"].splitlines()[0])
    if main_sha != sha and not is_release:
        print("Ejecución antigua; main ya avanzó")
        return
    if main_sha != sha:
        # La entrega merece su borrador aunque después entre documentación a main.
        # Debe seguir perteneciendo al historial vigente; nunca publicar un HEAD ajeno.
        git(root, "merge-base", "--is-ancestor", sha, main_sha)
    checks = client.request("GET", f"commits/{sha}/check-runs?filter=latest&per_page=100")[
        "check_runs"
    ]
    if not checks_ready(checks):
        print("Sin cambios: CI de main incompleto o fallido")
        return
    state = load_state(root)
    if is_release:
        publish_draft(root, client, sha, state, commit)
        return
    plan = plan_release(root)
    if plan is None:
        print("Sin cambios de producto pendientes de entrega")
        return
    update_proposal(root, client, sha, plan)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()
    run_bot(Path(args.root), GitHub(args.repository))


if __name__ == "__main__":
    main()
