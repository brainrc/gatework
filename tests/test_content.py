"""What Gatework ships: the namespaced skills and agents, their deprecated aliases, the plugin
manifests and the trigger evals."""
import json
import re
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from helpers import ROOT, brainrc
from brainrc import naming

OLD_AGENTS = ("analyst", "architect", "code-reviewer", "doc-writer", "implementer", "infra-reviewer",
              "researcher", "security-reviewer", "test-writer", "verifier")
REMOVED_SKILLS = ("work", "review", "plan", "aws", "terraform")  # aliases removed in 0.6.1
USER_INVOKED = ("work", "review", "plan")  # slash commands: take $ARGUMENTS
KNOWLEDGE = ("aws", "terraform")           # auto-triggered
ARGUMENT_HINTS = {
    "work": "<gh:42 | jira:PROJ-7 | issue URL | local:path.md | free text | --campaign <epic|query>> "
            "[--local] [--batch-size N] [--dry-run] [--shape playbook|ordered] [--auto]",
    "review": "[extra focus]",
    "plan": "<topic> [--web] [--dry-run] [--oneshot] [--local]",
}
TRIGGER_STARTS = {
    "aws": "AWS account safety, CLI usage, and review checklists",
    "terraform": "Terraform/OpenTofu and Terragrunt conventions",
}
SKILLS, AGENTS = ROOT / "skills", ROOT / "agents"


def meta(name: str) -> dict:
    path = SKILLS / name / "SKILL.md"
    return brainrc.frontmatter(path) if path.is_file() else {}


def body(name: str) -> str:
    path = SKILLS / name / "SKILL.md"
    return path.read_text().split("\n---\n", 1)[-1] if path.is_file() else ""


def agent(name: str) -> dict:
    return brainrc.frontmatter(AGENTS / f"{name}.md")


class PackTest(unittest.TestCase):
    def test_the_pack_is_self_contained(self):
        for p in ROOT.rglob("*"):
            if p.is_symlink():
                with self.subTest(link=str(p.relative_to(ROOT))):
                    self.assertTrue(p.resolve().is_relative_to(ROOT), "a link that leaves the pack breaks a clone")
        meta_ = brainrc.load_pack(ROOT, "gatework").meta
        self.assertEqual((meta_["id"], meta_["validator"]), ("brainrc/gatework", "validator.py"))


class SkillsTest(unittest.TestCase):
    def test_namespaced_skills_exist_with_matching_name(self):
        for n in REMOVED_SKILLS:
            with self.subTest(skill=n):
                self.assertEqual(meta(f"brainrc-{n}").get("name"), f"brainrc-{n}")
                self.assertFalse((SKILLS / n).exists(), f"skills/{n} was removed in 0.6.1")

    def test_user_invoked_skills_keep_hint_and_flag(self):
        for n in USER_INVOKED:
            with self.subTest(skill=n):
                m = meta(f"brainrc-{n}")
                self.assertEqual(m.get("argument-hint"), ARGUMENT_HINTS[n])
                self.assertEqual(m.get("disable-model-invocation"), "true")
                self.assertIn("$ARGUMENTS", body(f"brainrc-{n}"))

    def test_knowledge_skills_keep_trigger_description_and_stay_auto_triggerable(self):
        for n in KNOWLEDGE:
            with self.subTest(skill=n):
                m = meta(f"brainrc-{n}")
                self.assertTrue(m.get("description", "").startswith(TRIGGER_STARTS[n]), m.get("description"))
                self.assertNotIn("disable-model-invocation", m)
        self.assertIn("## Account safety", body("brainrc-aws"))

    def test_spec_agent_is_a_deprecated_alias_for_one_minor_release(self):
        alias = meta("spec-agent")
        self.assertEqual(meta("brainrc-gatework")["name"], "brainrc-gatework")
        self.assertEqual(alias["description"], "Deprecated, use brainrc-gatework (removed in 0.8.0)")
        self.assertEqual(alias["disable-model-invocation"], "true")
        self.assertIn("`brainrc-gatework` skill", (SKILLS / "spec-agent/SKILL.md").read_text())
        for old, new in naming.SKILL_ALIASES.items():
            with self.subTest(alias=old):
                self.assertEqual(meta(old)["description"], f"Deprecated, use {new} (removed in 0.8.0)")
                self.assertEqual(meta(new)["name"], new)
        for name in ("brainrc-work", "brainrc-plan", "brainrc-gatework-approve", "brainrc-gatework-resume"):
            with self.subTest(skill=name):
                text = (SKILLS / name / "SKILL.md").read_text()
                self.assertIn("`brainrc-gatework` skill", text)
                self.assertNotIn("`spec-agent` skill", text)

    def test_connectors_document_create(self):
        for name in ("brainrc-ticket-local", "brainrc-ticket-github"):
            text = (SKILLS / name / "SKILL.md").read_text()
            self.assertRegex(text, r"(?m)^## create\b", name)
            self.assertRegex(text, r"Implements the ticket connector interface:.*`create`", name)
        contract = (SKILLS / "brainrc-gatework/references/connectors.md").read_text()
        self.assertRegex(contract, r"\| `create` \| no \| outward \| after an approved Ticket gate \|")


class UnslopSplitTest(unittest.TestCase):
    SKILL = SKILLS / "brainrc-unslop"

    def test_no_rule_line_was_lost(self):
        text = "\n".join(p.read_text() for p in sorted(self.SKILL.rglob("*.md")))
        for line in (ROOT / "tests/fixtures/unslop-rules.txt").read_text().splitlines():
            with self.subTest(line=line[:60]):
                self.assertIn(line, text)

    def test_skill_md_is_short_and_links_its_references(self):
        text = (self.SKILL / "SKILL.md").read_text()
        self.assertLess(len(text), 6000)
        for ref in ("structure.md", "clarity.md", "change-prose.md"):
            self.assertIn(f"references/{ref}", text)
        self.assertLessEqual(brainrc.estimate_tokens(meta("brainrc-unslop")["description"]), 60)


class AgentsTest(unittest.TestCase):
    def test_every_agent_is_prefixed_or_a_declared_alias(self):
        self.assertEqual(set(naming.AGENT_ALIASES), set(OLD_AGENTS))
        for f in AGENTS.glob("*.md"):
            with self.subTest(agent=f.stem):
                self.assertTrue(f.stem.startswith("brainrc-") or f.stem in OLD_AGENTS)
                self.assertEqual(agent(f.stem).get("name"), f.stem)

    def test_each_alias_runs_as_its_target(self):
        for n in OLD_AGENTS:
            with self.subTest(agent=n):
                new, alias = agent(f"brainrc-{n}"), agent(n)
                text = (AGENTS / f"{n}.md").read_text()
                self.assertEqual((alias.get("tools"), alias.get("model")), (new.get("tools"), new.get("model")))
                self.assertTrue(alias["description"].startswith("Deprecated"), alias["description"])
                self.assertLessEqual(len(alias["description"]), 80, "always-loaded token budget")
                self.assertIn(f"`brainrc-{n}`", text)
                self.assertIn(naming.AGENT_ALIAS_REMOVED_IN, text)
                target = (AGENTS / f"brainrc-{n}.md").read_text().split("\n---\n", 1)[1]
                self.assertTrue(text.endswith(target), "a subagent can't find another file, so it carries the instructions")

    def test_the_engine_dispatches_the_new_names(self):
        text = (SKILLS / "brainrc-gatework/SKILL.md").read_text()
        for n in OLD_AGENTS:
            with self.subTest(agent=n):
                self.assertIn(f"[roles/brainrc-{n}.md](roles/brainrc-{n}.md)", text)
                self.assertNotIn(f"(roles/{n}.md)", text)

    def test_role_lookup_order(self):
        text = (SKILLS / "brainrc-gatework/SKILL.md").read_text()
        self.assertLess(text.index("gatework:<role>"), text.index("brainrc:<role>"))
        self.assertLess(text.index("brainrc:<role>"), text.index("ai-config:<role>"))


class PluginInstallTest(unittest.TestCase):
    """Codex (through .claude-plugin/) and Antigravity (root plugin.json) find the skills."""

    def setUp(self):
        # Codex's install copy drops symlinks; copy the repo the same way.
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self.copy = tmp / "plugin"
        shutil.copytree(ROOT, self.copy, symlinks=True, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        for link in [p for p in self.copy.rglob("*") if p.is_symlink()]:
            link.unlink()
        self.expected = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}

    def found(self, paths) -> set[str]:
        paths = [paths] if isinstance(paths, str) else paths
        return {s.parent.name for d in paths for s in (self.copy / d).glob("*/SKILL.md")}

    def test_codex_reads_one_skills_dir_from_the_claude_manifest(self):
        manifest = json.loads((self.copy / ".claude-plugin/plugin.json").read_text())
        self.assertEqual(manifest["name"], "gatework")
        self.assertIsInstance(manifest["skills"], str)  # the form Codex documents
        self.assertTrue(manifest["skills"].startswith("./"))
        self.assertEqual(self.found(manifest["skills"]), self.expected)

    def test_antigravity_reads_skills_at_the_root(self):
        manifest = json.loads((self.copy / "plugin.json").read_text())
        self.assertEqual(manifest, {"name": "gatework"})  # its schema rejects other keys
        self.assertEqual(self.found("skills"), self.expected)

    def test_the_engine_finds_its_roles_without_the_roles_link(self):
        engine = self.copy / "skills/brainrc-gatework"
        self.assertFalse((engine / "roles").exists())
        self.assertIn("../../agents/<role>.md", (engine / "SKILL.md").read_text())
        for role in AGENTS.glob("brainrc-*.md"):
            self.assertTrue((engine / "../../agents" / role.name).is_file(), role.name)


def domain_skills() -> set[str]:
    text = (SKILLS / "brainrc-gatework/SKILL.md").read_text()
    table = text.split("## Domains", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"\[([a-z0-9-]+)\]\(\.\./\1/SKILL\.md\)", table))


class TriggerCasesTest(unittest.TestCase):
    def test_every_domain_skill_has_a_positive_and_a_negative_trigger(self):
        cases = tomllib.loads((ROOT / "evals/triggers.toml").read_text())["case"]
        skills = domain_skills()
        self.assertGreaterEqual(len(skills), 10)
        for skill in sorted(skills):
            with self.subTest(skill=skill):
                self.assertTrue(any(skill in c.get("expect", []) for c in cases), "no positive case")
                self.assertTrue(any(skill in c.get("forbid", []) for c in cases), "no negative case")

    def test_cases_name_skills_that_exist(self):
        names = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
        for case in tomllib.loads((ROOT / "evals/triggers.toml").read_text())["case"]:
            for name in case.get("expect", []) + case.get("forbid", []):
                with self.subTest(skill=name):
                    self.assertIn(name, names)


if __name__ == "__main__":
    unittest.main()
