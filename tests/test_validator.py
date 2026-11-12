"""Gatework's validator plugin, run by brainrc core: the deprecated aliases, the roles link, the
ticket connectors and each pack's [extensions.gatework]."""
import importlib.util
import unittest
from pathlib import PurePosixPath, PureWindowsPath
from unittest import mock

from helpers import PACK_TOML, ROOT, PackCase, brainrc, quiet, write_skill
from brainrc import naming

_spec = importlib.util.spec_from_file_location("gatework_validator", ROOT / "validator.py")
VALIDATOR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VALIDATOR)

LEGACY_TOML = PACK_TOML.replace("[extensions.gatework]", "[extensions]").replace("extensions.gatework.", "extensions.")


class BaselineTest(PackCase):
    def test_an_unmodified_copy_validates(self):
        code, out = self.validate()
        self.assertEqual(code, 0, out)


class AgentAliasTest(PackCase):
    def test_missing_alias_fails(self):
        (self.pack / "agents/verifier.md").unlink()
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("agents/verifier.md: deprecated alias for `brainrc-verifier` is missing", out)

    def test_alias_with_other_tools_fails(self):
        path = self.pack / "agents/code-reviewer.md"
        path.write_text(path.read_text().replace("tools: Read, Grep, Glob, Bash", "tools: Read, Grep, Glob, Bash, Edit"))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("alias `tools` must match `brainrc-code-reviewer`", out)

    def test_alias_without_its_removal_release_or_target_name_fails(self):
        path = self.pack / "agents/analyst.md"
        path.write_text(path.read_text().replace(naming.AGENT_ALIAS_REMOVED_IN, "later")
                        .replace("`brainrc-analyst`", "the new agent"))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("alias body must name the removal release", out)
        self.assertIn("alias body must name `brainrc-analyst`", out)

    def test_alias_whose_instructions_drift_from_its_target_fails(self):
        path = self.pack / "agents/brainrc-verifier.md"
        path.write_text(path.read_text() + "\nOne more rule.\n")
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("agents/verifier.md: alias body must end with `brainrc-verifier`'s instructions", out)

    def test_alias_without_a_deprecated_description_fails(self):
        path = self.pack / "agents/analyst.md"
        path.write_text(path.read_text().replace("description: Deprecated, use", "description: Use"))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("alias `description` must start with `Deprecated`", out)

    def test_unprefixed_new_agent_fails_and_prefixed_passes(self):
        body = "---\nname: {0}\ndescription: A test agent.\n---\nBody.\n"
        (self.pack / "agents/planner.md").write_text(body.format("planner"))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("agents/planner.md: core agent names start with `brainrc-`", out)
        (self.pack / "agents/planner.md").unlink()
        (self.pack / "agents/brainrc-planner.md").write_text(body.format("brainrc-planner"))
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_a_pack_may_still_name_an_old_reviewer(self):
        pack = self.acme()
        toml = pack / "pack.toml"
        toml.write_text(toml.read_text().replace('"brainrc-infra-reviewer"', '"infra-reviewer"'))
        code, out = self.validate()
        self.assertNotIn("unknown reviewer", out)


class SkillAliasTest(PackCase):
    def skill(self, name: str):
        return self.pack / "skills" / name / "SKILL.md"

    def test_an_alias_stays_a_stub_the_model_cant_pick(self):
        stub = self.skill("kubernetes")
        stub.write_text(stub.read_text().replace("disable-model-invocation: true\n", ""))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("skills/kubernetes/SKILL.md: alias needs `disable-model-invocation: true`", out)

    def test_an_alias_is_kept_until_its_removal_release(self):
        self.skill("runbook").unlink()
        self.skill("runbook").parent.rmdir()
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("deprecated alias for `brainrc-runbook` is missing (keep it until 0.8.0)", out)

    def test_a_command_alias_passes_its_arguments_on(self):
        stub = self.skill("spec-approve")
        stub.write_text(stub.read_text().replace("Arguments: $ARGUMENTS\n", ""))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("skills/spec-approve/SKILL.md: alias body must pass on `$ARGUMENTS`", out)


class RolesLinkTest(PackCase):
    def setUp(self):
        super().setUp()
        self.roles = self.pack / "skills/brainrc-gatework/roles"

    def assert_validate_fails(self):
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("skills/brainrc-gatework/roles", out)
        self.assertIn("Platforms", out)

    def test_the_link_passes(self):
        self.assertTrue(self.roles.is_symlink())
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_plain_file_from_a_checkout_without_symlinks_fails(self):
        self.roles.unlink()
        self.roles.write_text("../../agents")  # what git writes when core.symlinks is false
        self.assert_validate_fails()

    def test_link_to_the_wrong_place_fails(self):
        self.roles.unlink()
        self.roles.symlink_to("../../skills")
        self.assert_validate_fails()

    def test_a_windows_link_with_backslashes_passes(self):
        with mock.patch.object(VALIDATOR, "PurePath", PureWindowsPath):
            self.assertTrue(VALIDATOR.links_to_agents("..\\..\\agents"))
            self.assertTrue(VALIDATOR.links_to_agents("../../agents"))
            self.assertFalse(VALIDATOR.links_to_agents("..\\..\\skills"))

    def test_backslashes_are_not_separators_off_windows(self):
        with mock.patch.object(VALIDATOR, "PurePath", PurePosixPath):
            self.assertFalse(VALIDATOR.links_to_agents("..\\..\\agents"))
            self.assertTrue(VALIDATOR.links_to_agents("../../agents"))

    def test_doctor_reports_a_broken_link(self):
        self.roles.unlink()
        findings = brainrc.doctor_findings()
        self.assertTrue(any("skills/brainrc-gatework/roles" in f[1] for f in findings), findings)


class ConnectorCheckTest(PackCase):
    """Connector skills need a heading for every required operation (references/connectors.md)."""

    def test_connector_missing_an_operation_fails(self):
        write_skill(self.pack, "brainrc-ticket-x", "## fetch\n\n## comment\n\n## transition\n")
        code, out = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("skills/brainrc-ticket-x/SKILL.md: connector missing `##` sections for link_pr", out)

    def test_a_connector_without_create_still_validates(self):
        write_skill(self.pack, "brainrc-ticket-w", "## fetch\n\n## comment / transition / link_pr\n")
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_one_heading_may_name_several_operations(self):
        write_skill(self.pack, "brainrc-ticket-y", "## fetch (read-only)\n\n## comment / transition / link_pr\n")
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_pr_status_is_optional_for_connectors(self):
        write_skill(self.pack, "brainrc-ticket-with", "## fetch\n\n## comment / transition / link_pr\n\n## pr_status\n")
        write_skill(self.pack, "brainrc-ticket-without", "## fetch\n\n## comment / transition / link_pr\n")
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertNotIn("pr_status", out)

    def test_pr_status_does_not_replace_required_operations(self):
        write_skill(self.pack, "brainrc-ticket-z", "## fetch\n\n## comment / transition\n\n## pr_status\n")
        code, out = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("skills/brainrc-ticket-z/SKILL.md: connector missing `##` sections for link_pr", out)

    def test_another_packs_connector_missing_operations_fails(self):
        pack = self.acme(PACK_TOML.replace('connector = "brainrc-ticket-github"', 'connector = "acme-tickets"'))
        write_skill(pack, "acme-tickets", "## fetch\n")
        code, out = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("acme:skills/acme-tickets/SKILL.md: connector missing `##` sections for "
                      "comment, transition, link_pr", out)


class ExtensionsTest(PackCase):
    """Another pack's [extensions.gatework], checked and rendered into extensions.md."""

    def sync(self) -> str:
        code, out = quiet(brainrc.cmd_sync, True)
        self.assertEqual(code, 0, out)
        return (self.settings_home / "extensions.md").read_text()

    def test_namespaced_extensions_render_without_warnings(self):
        self.acme()
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertNotIn("WARN", out)
        ext = self.sync()
        self.assertIn("- (acme) Deploy plan reviewed", ext)
        self.assertIn("| `deploy/*.yaml` | acme-deploy | brainrc-infra-reviewer | acme |", ext)

    def test_legacy_top_level_extensions_still_render_with_a_warning(self):
        self.acme(LEGACY_TOML)
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertIn("[extensions] `domains` is deprecated; move it under [extensions.gatework]", out)
        self.assertIn("| `deploy/*.yaml` | acme-deploy | brainrc-infra-reviewer | acme |", self.sync())

    def test_spec_agent_table_passes_through_with_a_warning(self):
        self.acme(PACK_TOML.replace("extensions.gatework", "extensions.spec-agent"))
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertIn("[extensions.spec-agent] is deprecated", out)
        self.assertIn('"connector": "brainrc-ticket-github"', self.sync())

    def test_a_deprecated_skill_name_warns_and_renders_as_its_new_name(self):
        self.acme(PACK_TOML.replace('"brainrc-ticket-github"', '"ticket-github"'))
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertIn("acme:pack.toml: `ticket-github` is deprecated; name `brainrc-ticket-github`", out)
        ext = self.sync()
        self.assertIn('"connector": "brainrc-ticket-github"', ext)
        self.assertNotIn('"ticket-github"', ext)

    def test_errors_in_the_gatework_table_fail_validate_and_apply(self):
        self.acme(PACK_TOML.replace('skills = ["acme-deploy"]', 'skills = ["acme-nope"]'))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("acme:pack.toml: domains names unknown skill `acme-nope`", out)
        code, out = quiet(brainrc.cmd_sync, True)
        self.assertEqual(code, 1, out)
        self.assertIn("Nothing written", out)

    def test_a_ticket_table_needs_refs(self):
        self.acme(PACK_TOML.replace('refs = ["gh:*"]\n', ""))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("acme:pack.toml: ticket needs `refs`", out)


if __name__ == "__main__":
    unittest.main()
