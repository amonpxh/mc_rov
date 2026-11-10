"""Fronteras de autorización del bot sin llamar a GitHub."""

import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from release_bot import (
    checks_ready,
    validate_generated,
    release_commit_version,
    run_bot,
    publish_draft,
    update_proposal,
)


class BotBoundaries(unittest.TestCase):
    """Verifica identidad, integridad y CI antes de habilitar escrituras."""

    def checks(self):
        return [
            {"id": i, "name": name, "status": "completed", "conclusion": "success"}
            for i, name in enumerate(
                [
                    "pre-commit (hygiene, pylint-odoo, black)",
                    "Odoo module tests",
                    "Gitleaks (historial)",
                ]
            )
        ]

    def test_all_checks_required(self):
        self.assertTrue(checks_ready(self.checks()))
        self.assertFalse(checks_ready(self.checks()[:-1]))

    def test_failure_blocks(self):
        checks = self.checks()
        checks[0]["conclusion"] = "failure"
        self.assertFalse(checks_ready(checks))

    def test_new_incomplete_rerun_blocks_old_success(self):
        checks = self.checks()
        checks.append({**checks[0], "id": 99, "status": "in_progress", "conclusion": None})
        self.assertFalse(checks_ready(checks))

    def generated(self):
        return {
            "author": {"login": "github-actions[bot]"},
            "commit": {"message": "chore(release): 19.0.25.7.0"},
            "parents": [{"sha": "a" * 40}],
        }

    def test_generated_head_must_be_bot(self):
        value = self.generated()
        value["author"]["login"] = "persona"
        with self.assertRaises(ValueError):
            validate_generated(
                value, "a" * 40, {"__manifest__.py", ".odoo-release.json", "CHANGELOG.md"}
            )

    def test_bot_cannot_touch_product(self):
        with self.assertRaises(ValueError):
            validate_generated(self.generated(), "a" * 40, {"models/repair.py"})

    def test_generated_parent_must_match(self):
        with self.assertRaises(ValueError):
            validate_generated(
                self.generated(),
                "b" * 40,
                {"__manifest__.py", ".odoo-release.json", "CHANGELOG.md"},
            )

    def test_valid_generated_head(self):
        validate_generated(
            self.generated(), "a" * 40, {"__manifest__.py", ".odoo-release.json", "CHANGELOG.md"}
        )

    def test_release_squash_title(self):
        self.assertEqual(
            release_commit_version("chore(release): 19.0.25.7.0 (#120)"), "19.0.25.7.0"
        )

    def test_arbitrary_title_not_a_release(self):
        for title in [
            "feat: 19.0.25.7.0",
            "chore(release): 1.2.3",
            "chore(release): 19.0.25.7.0; shell",
        ]:
            self.assertIsNone(release_commit_version(title))


class FakeGitHub:
    """Respuestas deterministas que hacen fallar llamadas de API no previstas."""

    repository = "qa/repository"

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def request(self, method, endpoint, payload=None):
        self.calls.append((method, endpoint, payload))
        if (method, endpoint) == ("GET", "git/matching-refs/tags/v19.0.25.7.0"):
            return self.responses.get((method, endpoint), [])
        return self.responses[(method, endpoint)]

    def file(self, name, ref):
        return '{"source": "' + "a" * 40 + '", "version": "19.0.25.7.0"}'


class BotOperations(unittest.TestCase):
    """Prueba las decisiones del orquestador sin credenciales ni red."""

    def test_stale_main_never_writes(self):
        client = FakeGitHub(
            {
                ("GET", "git/ref/heads/main"): {"object": {"sha": "b" * 40}},
                ("GET", "commits/" + "a" * 40): {"commit": {"message": "docs: una nota"}},
            }
        )
        with patch("release_bot.git", side_effect=["a" * 40, ""]):
            run_bot(Path("unused"), client)
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_missing_ci_never_writes(self):
        sha = "a" * 40
        client = FakeGitHub(
            {
                ("GET", "git/ref/heads/main"): {"object": {"sha": sha}},
                ("GET", "commits/" + sha): {"commit": {"message": "docs: una nota"}},
                ("GET", f"commits/{sha}/check-runs?filter=latest&per_page=100"): {
                    "check_runs": []
                },
            }
        )
        with patch("release_bot.git", side_effect=[sha, ""]):
            run_bot(Path("unused"), client)
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_release_followed_by_docs_still_prepares_its_draft(self):
        release_sha, main_sha = "a" * 40, "b" * 40
        commit = {"commit": {"message": "chore(release): 19.0.25.7.0 (#120)"}}
        client = FakeGitHub(
            {
                ("GET", "git/ref/heads/main"): {"object": {"sha": main_sha}},
                ("GET", "commits/" + release_sha): commit,
                ("GET", f"commits/{release_sha}/check-runs?filter=latest&per_page=100"): {
                    "check_runs": BotBoundaries().checks()
                },
            }
        )
        with patch("release_bot.git", side_effect=[release_sha, "", ""]), patch(
            "release_bot.load_state", return_value={"version": "19.0.25.7.0"}
        ), patch("release_bot.publish_draft") as publish:
            run_bot(Path("unused"), client)
        publish.assert_called_once_with(
            Path("unused"), client, release_sha, {"version": "19.0.25.7.0"}, commit
        )

    def test_repeated_proposal_preserves_head(self):
        sha, old = "a" * 40, "b" * 40
        commit = BotBoundaries().generated()
        client = FakeGitHub(
            {
                ("GET", "git/matching-refs/heads/ci/release-odoo"): [
                    {"ref": "refs/heads/ci/release-odoo", "object": {"sha": old}}
                ],
                ("GET", "pulls?state=open&base=main&head=qa:ci/release-odoo&per_page=100"): [
                    {"html_url": "https://example.invalid/pr/1"}
                ],
                ("GET", "commits/" + old): commit,
                ("GET", f"compare/{sha}...{old}"): {
                    "files": [
                        {"filename": name}
                        for name in ["__manifest__.py", ".odoo-release.json", "CHANGELOG.md"]
                    ]
                },
            }
        )
        update_proposal(Path("unused"), client, sha, {"version": "19.0.25.7.0"})
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def release_fixture(self):
        # TestCase.enterContext posee y cierra el recurso incluso ante errores.
        # pylint: disable=consider-using-with
        # unittest conserva el contexto y garantiza su salida al terminar el caso.
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "__manifest__.py").write_text('{"version": "19.0.25.7.0"}', encoding="utf-8")
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [19.0.25.7.0] — 2026-11-10\n\nEntrega.\n\n## [19.0.25.6.0]\nAnterior.\n",
            encoding="utf-8",
        )
        state = {"version": "19.0.25.7.0", "source": "a" * 40}
        commit = {
            "commit": {"message": "chore(release): 19.0.25.7.0 (#120)"},
            "parents": [{"sha": "a" * 40}],
        }
        return root, state, commit

    def test_release_draft_never_publishes_or_includes_older_notes(self):
        root, state, commit = self.release_fixture()
        client = FakeGitHub(
            {
                ("GET", "releases?per_page=100"): [],
                ("POST", "releases"): {"html_url": "https://example.invalid/draft"},
            }
        )
        with patch(
            "release_bot.git", return_value="__manifest__.py\n.odoo-release.json\nCHANGELOG.md"
        ):
            publish_draft(root, client, "b" * 40, state, commit)
        payload = client.calls[-1][2]
        self.assertTrue(payload["draft"])
        self.assertEqual(payload["target_commitish"], "b" * 40)
        self.assertNotIn("Anterior", payload["body"])

    def test_release_different_existing_commit_rejected(self):
        root, state, commit = self.release_fixture()
        client = FakeGitHub(
            {
                ("GET", "releases?per_page=100"): [
                    {"tag_name": "v19.0.25.7.0", "target_commitish": "c" * 40}
                ]
            }
        )
        with patch(
            "release_bot.git", return_value="__manifest__.py\n.odoo-release.json\nCHANGELOG.md"
        ), self.assertRaises(ValueError):
            publish_draft(root, client, "b" * 40, state, commit)
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_stale_release_parent_rejected(self):
        root, state, commit = self.release_fixture()
        commit["parents"] = [{"sha": "c" * 40}]
        client = FakeGitHub({})
        with patch(
            "release_bot.git", return_value="__manifest__.py\n.odoo-release.json\nCHANGELOG.md"
        ), self.assertRaises(ValueError):
            publish_draft(root, client, "b" * 40, state, commit)
        self.assertFalse(client.calls)

    def test_existing_tag_for_other_code_blocks_draft(self):
        root, state, commit = self.release_fixture()
        client = FakeGitHub(
            {
                ("GET", "releases?per_page=100"): [],
                ("GET", "git/matching-refs/tags/v19.0.25.7.0"): [
                    {
                        "ref": "refs/tags/v19.0.25.7.0",
                        "object": {"type": "commit", "sha": "c" * 40},
                    }
                ],
            }
        )
        with patch(
            "release_bot.git", return_value="__manifest__.py\n.odoo-release.json\nCHANGELOG.md"
        ), self.assertRaises(ValueError):
            publish_draft(root, client, "b" * 40, state, commit)
        self.assertTrue(all(call[0] == "GET" for call in client.calls))

    def test_annotated_tag_is_resolved_before_draft(self):
        root, state, commit = self.release_fixture()
        client = FakeGitHub(
            {
                ("GET", "releases?per_page=100"): [],
                ("GET", "git/matching-refs/tags/v19.0.25.7.0"): [
                    {
                        "ref": "refs/tags/v19.0.25.7.0",
                        "object": {"type": "tag", "sha": "d" * 40},
                    }
                ],
                ("GET", "git/tags/" + "d" * 40): {"object": {"type": "commit", "sha": "b" * 40}},
                ("POST", "releases"): {"html_url": "https://example.invalid/draft"},
            }
        )
        with patch(
            "release_bot.git", return_value="__manifest__.py\n.odoo-release.json\nCHANGELOG.md"
        ):
            publish_draft(root, client, "b" * 40, state, commit)
        self.assertIn(("GET", "git/tags/" + "d" * 40, None), client.calls)


if __name__ == "__main__":
    unittest.main()
