"""Gatework's validator plugin, run by brainrc core: the skill and agent names, the roles link, the
ticket connectors and each pack's [extensions.gatework]."""
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import sys
import tomllib
import types
import unittest
from pathlib import PurePosixPath, PureWindowsPath
from unittest import mock

from helpers import PACK_TOML, ROOT, PackCase, brainrc, quiet, write_skill

COPIES_STAND_INS = importlib.util.find_spec("brainrc.gitlinks") is not None  # brainrc with #120


def remove_git(path) -> None:
    """Git marks its object files read-only, and Windows won't delete a read-only file."""
    def writable(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, **{"onexc" if sys.version_info >= (3, 12) else "onerror": writable})


def brainrc_source(root):
    """What the validator needs of brainrc's Source for a pack at root."""
    return types.SimpleNamespace(root=root, rel=lambda p: p.relative_to(root).as_posix())

_spec = importlib.util.spec_from_file_location("gatework_validator", ROOT / "validator.py")
VALIDATOR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VALIDATOR)

LEGACY_TOML = PACK_TOML.replace("[extensions.gatework]", "[extensions]").replace("extensions.gatework.", "extensions.")


class BaselineTest(PackCase):
    def test_an_unmodified_copy_validates(self):
        code, out = self.validate()
        self.assertEqual(code, 0, out)


class AgentNamesTest(PackCase):
    def test_an_old_agent_name_fails_and_names_the_new_one(self):
        (self.pack / "agents/verifier.md").write_text((self.pack / "agents/brainrc-verifier.md").read_text())
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("agents/verifier.md: core agent names start with `brainrc-`; it was renamed "
                      "`brainrc-verifier` in Gatework 0.8.0", out)

    def test_unprefixed_new_agent_fails_and_prefixed_passes(self):
        body = "---\nname: {0}\ndescription: A test agent.\n---\nBody.\n"
        (self.pack / "agents/planner.md").write_text(body.format("planner"))
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("agents/planner.md: core agent names start with `brainrc-`", out)
        self.assertNotIn("renamed", out)
        (self.pack / "agents/planner.md").unlink()
        (self.pack / "agents/brainrc-planner.md").write_text(body.format("brainrc-planner"))
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_a_pack_may_still_name_an_old_reviewer_with_a_warning(self):
        pack = self.acme()
        toml = pack / "pack.toml"
        toml.write_text(toml.read_text().replace('"brainrc-infra-reviewer"', '"infra-reviewer"'))
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertNotIn("unknown reviewer", out)
        self.assertIn("acme:pack.toml: `infra-reviewer` was renamed `brainrc-infra-reviewer` and Gatework "
                      "0.8.0 no longer installs it; use the new name (the old one is read until Gatework 0.9.0)", out)


class SkillNamesTest(PackCase):
    def test_an_old_skill_name_fails_and_names_the_new_one(self):
        write_skill(self.pack, "spec-agent")
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("skills/spec-agent: Gatework skill names start with `brainrc-`; it was renamed "
                      "`brainrc-gatework` in Gatework 0.8.0", out)

    def test_an_unprefixed_new_skill_fails(self):
        write_skill(self.pack, "helm")
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("skills/helm: Gatework skill names start with `brainrc-`", out)
        self.assertNotIn("renamed", out)


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

    def stand_in(self) -> None:
        """roles as a checkout without symlinks leaves it: git's index records the link, and a plain
        file holding its target stands in for it (brainrc reads the index to tell the two apart)."""
        def git(*args):
            subprocess.run(["git", "-C", str(self.pack), *args], check=True, capture_output=True)
        git("init", "-q")
        self.addCleanup(remove_git, self.pack / ".git")  # before PackCase's rmtree, which can't on Windows
        git("add", "-A")  # the link is a symlink here, so git records it as one (mode 120000)
        self.roles.unlink()
        self.roles.write_text("../../agents")

    @unittest.skipUnless(COPIES_STAND_INS and shutil.which("git"), "needs git and a brainrc that copies stand-ins")
    def test_git_stand_in_passes_where_brainrc_copies_it(self):
        self.stand_in()
        with mock.patch.dict(os.environ, {"BRAINRC_LINK_MODE": "copy"}):
            code, out = self.validate()
        self.assertEqual(code, 0, out)

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_git_stand_in_fails_in_link_mode(self):
        self.stand_in()
        with mock.patch.dict(os.environ, {"BRAINRC_LINK_MODE": "symlink"}):
            code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertIn("skills/brainrc-gatework/roles is git's plain-file stand-in", out)
        self.assertIn('link_mode = "copy"', out)

    @unittest.skipUnless(COPIES_STAND_INS, "needs a brainrc that copies stand-ins")
    def test_a_plain_file_git_does_not_record_as_a_link_fails_in_copy_mode(self):
        self.roles.unlink()
        self.roles.write_text("../../agents")  # no git index: an extracted archive, not a checkout
        with mock.patch.dict(os.environ, {"BRAINRC_LINK_MODE": "copy"}):
            self.assertIn("stand-in", VALIDATOR.roles_error(brainrc_source(self.pack)))

    def test_a_stand_in_is_accepted_only_with_a_brainrc_that_copies_it(self):
        self.roles.unlink()
        self.roles.write_text("../../agents")
        with mock.patch.object(VALIDATOR, "brainrc_copies", return_value=True):
            self.assertIsNone(VALIDATOR.roles_error(brainrc_source(self.pack)))
        with mock.patch.object(VALIDATOR, "brainrc_copies", return_value=False):
            self.assertIn("stand-in", VALIDATOR.roles_error(brainrc_source(self.pack)))
        self.roles.write_text("..\\..\\agents")  # as git on Windows may write it
        with mock.patch.object(VALIDATOR, "brainrc_copies", return_value=True):
            self.assertIsNone(VALIDATOR.roles_error(brainrc_source(self.pack)))
        self.roles.write_text("../../skills")  # a stand-in for the wrong link is never accepted
        with mock.patch.object(VALIDATOR, "brainrc_copies", return_value=True):
            self.assertIn("a plain file", VALIDATOR.roles_error(brainrc_source(self.pack)))

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

    def test_an_old_skill_name_warns_and_renders_as_its_new_name(self):
        self.acme(PACK_TOML.replace('"brainrc-ticket-github"', '"ticket-github"'))
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertIn("acme:pack.toml: `ticket-github` was renamed `brainrc-ticket-github` and Gatework 0.8.0 "
                      "no longer installs it; use the new name (the old one is read until Gatework 0.9.0)", out)
        ext = self.sync()
        self.assertIn('"connector": "brainrc-ticket-github"', ext)
        self.assertNotIn('"ticket-github"', ext)

    def test_an_old_reviewer_renders_as_its_new_name(self):
        self.acme(PACK_TOML.replace('"brainrc-infra-reviewer"', '"infra-reviewer"'))
        self.assertIn("| `deploy/*.yaml` | acme-deploy | brainrc-infra-reviewer | acme |", self.sync())

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


REVIEWER = """
[[extensions.gatework.reviewers]]
name = "acme-reviewer"
domains = ["acme-deploy"]
veto = true
"""


class ReviewersTest(PackCase):
    """#143: a pack's agent reviews beside Gatework's, by domain, with or without veto."""

    sync = ExtensionsTest.sync

    def check(self, table: str) -> list[str]:
        return VALIDATOR.check_extensions(tomllib.loads(table)["extensions"]["gatework"],
                                          "acme:pack.toml", {"acme-deploy", "brainrc-terraform"},
                                          {"acme-reviewer", "brainrc-code-reviewer"})

    def test_a_reviewer_validates_and_renders(self):
        self.acme(PACK_TOML + REVIEWER)
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertNotIn("WARN", out)
        ext = self.sync()
        self.assertIn("## Reviewers", ext)
        self.assertIn("never in place of one", ext)
        self.assertIn("veto `yes` is a stop", ext)
        self.assertIn("| acme-reviewer | acme-deploy | yes | acme |", ext)

    def test_a_reviewer_on_every_run(self):
        ext = {"reviewers": [{"name": "acme-reviewer"}]}
        self.assertIn("| acme-reviewer | every run | no | acme |",
                      VALIDATOR.render_extensions([("acme", ext)]))

    def test_a_reviewer_listed_twice_in_one_pack_fails(self):
        errors = self.check('[extensions.gatework]\nreviewers = [{name = "acme-reviewer"}, '
                            '{name = "acme-reviewer", domains = ["acme-deploy"]}]\n')
        self.assertEqual(errors, ["acme:pack.toml: reviewers[1]: `acme-reviewer` is listed twice; list each "
                                  "reviewer once, with all its domains"])

    def test_two_packs_naming_one_reviewer_render_one_row(self):
        tables = [("acme", {"reviewers": [{"name": "acme-reviewer", "domains": ["acme-deploy"]}]}),
                  ("beta", {"reviewers": [{"name": "acme-reviewer", "domains": ["brainrc-terraform", "acme-deploy"],
                                           "veto": True}]})]
        out = VALIDATOR.render_extensions(tables)
        self.assertIn("| acme-reviewer | acme-deploy, brainrc-terraform | yes | acme, beta |", out)
        self.assertEqual(out.count("| acme-reviewer |"), 1)
        tables.append(("gamma", {"reviewers": [{"name": "acme-reviewer"}]}))
        self.assertIn("| acme-reviewer | every run | yes | acme, beta, gamma |",
                      VALIDATOR.render_extensions(tables))

    def test_a_domain_that_is_not_a_list_of_names_fails_without_a_crash(self):
        for domains in ('[["acme-deploy"]]', "[3]", '[{x = 1}]'):
            with self.subTest(domains=domains):
                table = f'[extensions.gatework]\nreviewers = [{{name = "acme-reviewer", domains = {domains}}}]\n'
                self.assertEqual(self.check(table), ["acme:pack.toml: reviewers[0]: domains must be a list "
                                                     "of domain skill names"])
                ext = tomllib.loads(table)["extensions"]["gatework"]
                VALIDATOR.warn_extensions(ext, "w")

    def test_a_domain_no_run_can_have_warns(self):
        ext = {"reviewers": [{"name": "acme-reviewer", "domains": ["acme-context", "brainrc-scripting"]}]}
        warnings = VALIDATOR.warn_extensions(ext, "w")
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("runs on `acme-context`, which isn't a domain skill", warnings[0])
        ext["domains"] = [{"files": ["deploy/*"], "skills": ["acme-context"]}]
        self.assertEqual(VALIDATOR.warn_extensions(ext, "w"), [])

    def test_domain_skills_is_the_domains_table(self):
        text = (ROOT / "skills/brainrc-gatework/SKILL.md").read_text()
        table = text.split("## Domains", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(VALIDATOR.DOMAIN_SKILLS, set(re.findall(r"\[(brainrc-[a-z-]+)\]", table)))

    def test_a_gatework_role_cannot_be_a_pack_reviewer(self):
        errors = self.check('[extensions.gatework]\nreviewers = [{name = "brainrc-code-reviewer"}]\n')
        self.assertEqual(errors, ["acme:pack.toml: reviewers[0]: `brainrc-code-reviewer` is one of Gatework's "
                                  "roles, which run already; a pack reviewer adds its own agent and never "
                                  "replaces one of Gatework's"])

    def test_bad_entries_fail_with_what_is_wrong(self):
        errors = self.check('[extensions.gatework]\nreviewers = [{name = "acme-nope", domains = ["acme-x"], '
                            'veto = "yes", when = "always"}, {domains = "acme-deploy"}]\n')
        self.assertEqual(errors, [
            "acme:pack.toml: reviewers[0]: unknown key `when` (keys: name, domains, veto)",
            "acme:pack.toml: reviewers[0]: names unknown agent `acme-nope`",
            "acme:pack.toml: reviewers[0]: domains names unknown skill `acme-x`",
            "acme:pack.toml: reviewers[0]: veto must be true or false",
            "acme:pack.toml: reviewers[1]: needs `name`, the pack agent that reviews",
            "acme:pack.toml: reviewers[1]: domains must be a list of domain skill names"])
        self.assertEqual(self.check('[extensions.gatework]\nreviewers = "acme-reviewer"\n'),
                         ["acme:pack.toml: reviewers must be a list of tables ([[extensions.gatework.reviewers]])"])

    def test_an_old_domain_name_warns_and_is_read_as_the_new_one(self):
        table = '[extensions.gatework]\nreviewers = [{name = "acme-reviewer", domains = ["kubernetes"]}]\n'
        self.assertEqual(VALIDATOR.check_extensions(tomllib.loads(table)["extensions"]["gatework"],
                                                    "w", {"brainrc-kubernetes"}, {"acme-reviewer"}), [])
        ext = tomllib.loads(table)["extensions"]["gatework"]
        self.assertIn("`kubernetes` was renamed `brainrc-kubernetes`", VALIDATOR.warn_extensions(ext, "w")[0])
        self.assertIn("| acme-reviewer | brainrc-kubernetes | no | acme |",
                      VALIDATOR.render_extensions([("acme", ext)]))

    def test_gatework_agents_is_every_agent_it_ships(self):
        self.assertEqual(VALIDATOR.GATEWORK_AGENTS, {f.stem for f in (ROOT / "agents").glob("*.md")})


class RunModeTest(PackCase):
    """#144: a pack, or this machine, sets the execution mode without a rule over Gatework's."""

    sync = ExtensionsTest.sync

    def test_a_pack_sets_its_mode_and_it_renders(self):
        self.acme(PACK_TOML.replace("[extensions.gatework]\n",
                                    '[extensions.gatework]\nmode = "inline"\nforbid_writing_subagents = true\n'))
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        ext = self.sync()
        self.assertIn("## Run mode", ext)
        self.assertIn("| acme | inline | forbidden |", ext)
        self.assertIn("| beta | subagent | allowed |", VALIDATOR.render_extensions(
            [("beta", {"mode": "subagent", "forbid_writing_subagents": False})]))

    def test_no_section_without_a_setting(self):
        self.acme()
        self.assertNotIn("## Run mode", self.sync())

    def test_bad_values_fail(self):
        ext = {"mode": "parallel", "forbid_writing_subagents": "yes"}
        self.assertEqual(VALIDATOR.check_extensions(ext, "w", set(), set()),
                         ["w: mode must be one of auto, inline, subagent",
                          "w: forbid_writing_subagents must be true or false"])

    def test_this_machine_sets_only_the_mode(self):
        where = "~/brainrc/brainrc.local.toml"
        self.assertEqual(VALIDATOR.check_extensions({"mode": "inline", "forbid_writing_subagents": True},
                                                    where, set(), set()), [])
        errors = VALIDATOR.check_extensions({"mode": "inline", "unavailable_gates": ["dast"],
                                             "reviewers": []}, where, set(), set())
        self.assertEqual(errors, [
            f"{where}: [extensions.gatework] `reviewers` belongs in a pack; this machine sets only "
            "forbid_writing_subagents, mode",
            f"{where}: [extensions.gatework] `unavailable_gates` belongs in a pack; this machine sets only "
            "forbid_writing_subagents, mode"])

    def test_this_machine_sets_it_through_core(self):
        """Core 0.8.30 reads brainrc.local.toml's [extensions.gatework] and checks it here."""
        if not hasattr(brainrc.plugins, "machine_findings"):
            self.skipTest("core before 0.8.30")
        self.acme()
        (self.core / "brainrc.local.toml").write_text('[extensions.gatework]\nmode = "subagent"\n')
        ext = self.sync()
        self.assertIn("## This machine", ext)
        self.assertIn('"mode": "subagent"', ext)
        (self.core / "brainrc.local.toml").write_text('[extensions.gatework]\nmode = "fast"\n')
        code, out = quiet(brainrc.cmd_sync, True)
        self.assertEqual(code, 1, out)
        self.assertIn("mode must be one of auto, inline, subagent", out)


if __name__ == "__main__":
    unittest.main()
