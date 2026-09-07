"""Exercise registration, retrieval, selection and CLI output using real PNG fixtures."""
import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("registry_afw", PROJECT / "scripts/afw.py")
afw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(afw)
registry = afw.reference_registry
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")


class ReferenceRegistryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="afw-registry-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.image = self.root / ".local/images/approved.png"
        self.image.parent.mkdir(parents=True)
        self.image.write_bytes(PNG)
        self.brief = self.root / "brief.json"
        self.brief.write_text(json.dumps({"title": "ODE transport", "scientific_source": "Supplied method section",
                                          "mechanism": "Deterministic transport", "must_show": ["state and time"],
                                          "must_not_show": ["noise"]}), encoding="utf-8")

    def register(self, reference_id="selected-v1", **kwargs):
        options = {"aesthetic_status": "user-approved", "approval_evidence": "User explicitly selected this image in the design review.",
                   "title": "ODE transport", "tags": ["ode", "transport"], "style": "modern", "license": "original-project"}
        options.update(kwargs)
        return registry.register(reference_id, self.image, root=self.root, **options)

    def pack(self, ids=("selected-v1",), **kwargs):
        return afw.make_priors(self.brief, output_dir=self.root / ".local/pack-v1", root=self.root,
                               reference_ids=ids, **kwargs)

    def alter(self, reference_id, **fields):
        path = registry.record_path(self.root, reference_id)
        value = json.loads(path.read_text())
        value.update(fields)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_records_real_file_and_evidence_without_implying_publication(self):
        record = self.register(private=True, role="mechanism")
        self.assertEqual(record["sha256"], afw.digest(self.image))
        self.assertEqual(record["path"], ".local/images/approved.png")
        self.assertEqual(record["role"], "mechanism")
        self.assertTrue(record["private"])
        self.assertEqual(record["aesthetic_status"], "user-approved")
        self.assertIn("explicitly selected", record["approval_evidence"])
        self.assertFalse(record["publication_authorized"])
        self.assertFalse(record["upload_authorized"])
        self.assertEqual(registry.load("selected-v1", root=self.root), record)

    def test_registration_defaults_to_unapproved_candidate(self):
        record = registry.register("candidate", self.image, root=self.root)
        self.assertEqual(record["aesthetic_status"], "candidate")
        with self.assertRaisesRegex(ValueError, "candidate"):
            self.pack(("candidate",))
        self.assertFalse((self.root / ".local/pack-v1").exists())

    def test_candidate_explicit_opt_in_preserves_candidate_status_and_evidence(self):
        self.register(aesthetic_status="candidate", approval_evidence="")
        with self.assertRaisesRegex(ValueError, "candidate"):
            self.pack()
        manifest = self.pack(allow_candidates=True)
        reference = manifest["references"][0]
        self.assertEqual(reference["aesthetic_status"], "candidate")
        self.assertEqual(reference["approval_evidence"], "")
        self.assertEqual(reference["selection"], "explicit-candidate-reference-id")
        self.assertTrue(manifest["candidate_references_explicitly_allowed"])
        self.assertEqual(registry.load("selected-v1", root=self.root)["aesthetic_status"], "candidate")

    def test_candidate_opt_in_never_admits_rejected_or_superseded_references(self):
        self.register(aesthetic_status="candidate", approval_evidence="")
        self.register("selected-v2", aesthetic_status="rejected", supersedes="selected-v1")
        for reference_id, error in (("selected-v1", "superseded"), ("selected-v2", "rejected")):
            with self.subTest(reference_id=reference_id), self.assertRaisesRegex(ValueError, error):
                registry.selected([reference_id], root=self.root, allow_candidates=True)
        with self.assertRaisesRegex(ValueError, "requires explicit --reference-id"):
            self.pack((), allow_candidates=True)

    def test_approval_requires_nonempty_text_evidence(self):
        for evidence in ("", "  ", None, 123):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                self.register(approval_evidence=evidence)
        self.assertFalse(registry.record_path(self.root, "selected-v1").exists())

    def test_duplicate_registration_never_changes_approved_record(self):
        self.register()
        path = registry.record_path(self.root, "selected-v1")
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "new version"):
            self.register(aesthetic_status="rejected")
        self.assertEqual(before, path.read_bytes())

    def test_reference_only_pack_needs_no_component_catalog_or_style(self):
        self.register()
        manifest = self.pack()
        self.assertIsNone(manifest["component"])
        self.assertIsNone(manifest["style"])
        self.assertEqual(len(manifest["references"]), 1)
        self.assertEqual(manifest["references"][0]["path"], str(self.image))
        self.assertEqual(manifest["references"][0]["priority"], "primary")
        tool = afw.read_json(self.root / ".local/pack-v1/image-tool-input.json")
        self.assertEqual(tool["referenced_image_paths"], [str(self.image)])
        self.assertIn("primary selected reference", tool["prompt"])
        self.assertNotIn("Times/Roman", tool["prompt"])
        self.assertEqual(manifest["status"], "prepared-not-generated")

    def test_rejected_reference_excluded_from_search_and_preparation(self):
        self.register(aesthetic_status="rejected", approval_evidence="User rejected it")
        self.assertEqual(afw.search("ode", include_private=True, root=self.root), [])
        with self.assertRaisesRegex(ValueError, "rejected"):
            self.pack()

    def test_unknown_license_requires_local_image_and_local_pack(self):
        outside_local = self.root / "public.png"
        outside_local.write_bytes(PNG)
        with self.assertRaisesRegex(ValueError, "under .local"):
            registry.register("unknown", outside_local, root=self.root)
        self.register(license="unknown")
        with self.assertRaisesRegex(ValueError, "under .local"):
            afw.make_priors(self.brief, output_dir=self.root / "public-pack", root=self.root,
                            reference_ids=["selected-v1"], allow_private=True)
        self.assertFalse((self.root / "public-pack").exists())

    def test_private_selection_needs_explicit_allow_and_stays_local(self):
        self.register(private=True, license="original-project")
        self.assertEqual(afw.search("ode", root=self.root), [])
        self.assertEqual(afw.search("ode", include_private=True, root=self.root)[0]["id"], "selected-v1")
        with self.assertRaisesRegex(ValueError, "--allow-private"):
            self.pack()
        manifest = self.pack(allow_private=True)
        self.assertTrue(manifest["private"])
        self.assertTrue(manifest["local_only"])
        self.assertFalse(manifest["upload_authorized"])

    def test_unknown_license_requires_private_opt_in_even_if_private_false(self):
        self.register(license="unknown", private=False)
        self.assertEqual(afw.search("ode", root=self.root), [])
        self.assertEqual(afw.search("ode", include_private=True, root=self.root)[0]["id"], "selected-v1")
        with self.assertRaisesRegex(ValueError, "unknown-license.*--allow-private"):
            self.pack()
        manifest = self.pack(allow_private=True)
        self.assertTrue(manifest["local_only"])

    def test_legacy_notes_coexist_without_becoming_registered_references(self):
        self.register()
        directory = self.root / ".local/references"
        legacy = directory / "user-planar-field.json"
        legacy.write_text(json.dumps({"id": "user-planar-field", "source": "local user screenshot",
                                      "status": "user-approved", "image_path": ".local/old.png"}))
        before = legacy.read_bytes()
        self.assertEqual([x["id"] for x in afw.search("ode", include_private=True, root=self.root)], ["selected-v1"])
        self.assertEqual(self.pack()["references"][0]["id"], "selected-v1")
        self.assertEqual(legacy.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "Invalid reference record"):
            registry.selected(["user-planar-field"], allow_private=True, root=self.root)

    def test_changed_historical_image_can_be_superseded(self):
        self.register()
        old_path = registry.record_path(self.root, "selected-v1")
        before = old_path.read_bytes()
        self.image.write_bytes(PNG + b"new-version")
        replacement = self.register("selected-v2", supersedes="selected-v1")
        self.assertEqual(old_path.read_bytes(), before)
        self.assertEqual(registry.list_references(root=self.root), [replacement])
        self.assertEqual(self.pack(("selected-v2",))["references"][0]["sha256"], afw.digest(self.image))
        with self.assertRaisesRegex(ValueError, "superseded"):
            registry.selected(["selected-v1"], root=self.root)

    def test_damaged_unrelated_image_does_not_block_valid_selection(self):
        broken_image = self.image.parent / "old.png"
        broken_image.write_bytes(PNG)
        registry.register("old", broken_image, root=self.root, license="original-project",
                          aesthetic_status="user-approved", approval_evidence="User selected old image")
        broken_image.write_bytes(PNG + b"changed")
        self.register()
        self.assertEqual([r["id"] for r in registry.list_references(root=self.root)], ["selected-v1"])
        self.assertEqual(self.pack()["references"][0]["id"], "selected-v1")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            registry.selected(["old"], root=self.root)

    def test_missing_historical_image_does_not_block_new_version(self):
        self.register()
        original_image = self.image
        self.image = self.image.parent / "replacement.png"
        self.image.write_bytes(PNG)
        original_image.unlink()
        self.register("selected-v2", supersedes="selected-v1")
        self.assertEqual([r["id"] for r in registry.list_references(root=self.root)], ["selected-v2"])
        self.assertEqual(self.pack(("selected-v2",))["references"][0]["id"], "selected-v2")

    def test_registered_approved_modern_precedes_old_roman_demo(self):
        catalog = self.root / "components/catalog.json"
        catalog.parent.mkdir()
        catalog.write_text(json.dumps([{"id": "ode-roman", "component": "ode", "style": "roman", "tags": ["ode"]}]))
        self.register(private=True)
        self.assertEqual([x["id"] for x in afw.search("ode", include_private=True, root=self.root)],
                         ["selected-v1", "ode-roman"])
        self.assertEqual([x["id"] for x in afw.search("ode", "modern", True, self.root)], ["selected-v1"])

    def test_file_changes_fail_before_creating_pack(self):
        self.register()
        self.image.write_bytes(PNG + b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.pack()
        self.assertFalse((self.root / ".local/pack-v1").exists())

    def test_outside_paths_and_symlink_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "external.png"
            external.write_bytes(PNG)
            with self.assertRaisesRegex(ValueError, "escapes"):
                registry.register("outside", external, root=self.root)
            link = self.image.parent / "link.png"
            link.symlink_to(external)
            with self.assertRaisesRegex(ValueError, "escapes"):
                registry.register("link", link, root=self.root)
        self.register()
        self.alter("selected-v1", path="../external.png")
        with self.assertRaisesRegex(ValueError, "traversal"):
            self.pack()

    def test_record_directory_cannot_escape_via_symlink(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / ".local/references").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "escapes"):
                self.register()
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_bad_id_and_fake_image_rejected(self):
        for reference_id in ("../escape", "/absolute", "a/b", ""):
            with self.subTest(reference_id=reference_id), self.assertRaises(ValueError):
                self.register(reference_id)
        self.image.write_bytes(b"not a raster")
        with self.assertRaisesRegex(ValueError, "raster"):
            self.register()

    def test_multiple_references_preserve_order_and_refuse_duplicates(self):
        self.register("a")
        self.register("b", role="mechanism")
        with self.assertRaisesRegex(ValueError, "distinct"):
            self.pack(("a", "a"))
        manifest = self.pack(("b", "a"))
        self.assertEqual([r["id"] for r in manifest["references"]], ["b", "a"])
        self.assertEqual([r["priority"] for r in manifest["references"]], ["primary", "supporting"])
        self.assertEqual(manifest["references"][0]["role"], "mechanism-reference")

    def test_registered_reference_stays_primary_when_legacy_demo_requested(self):
        self.register()
        catalog = self.root / "components/catalog.json"
        catalog.parent.mkdir()
        catalog.write_text(json.dumps([{"id": "ode-roman", "component": "ode", "style": "roman",
                                        "preview": str(self.image.relative_to(self.root)), "license": "original-project"}]))
        manifest = self.pack(component="ode", style="roman")
        self.assertEqual([r["id"] for r in manifest["references"]], ["selected-v1", "ode-roman"])
        self.assertEqual(manifest["references"][1]["priority"], "supporting")

    def test_rejection_new_version_blocks_old_approval_without_overwriting(self):
        original = self.register()
        rejected = self.register("selected-v2", aesthetic_status="rejected", supersedes="selected-v1")
        self.assertEqual(registry.load("selected-v1", root=self.root), original)
        self.assertEqual(registry.list_references(root=self.root), [rejected])
        with self.assertRaisesRegex(ValueError, "superseded"):
            self.pack()
        with self.assertRaisesRegex(ValueError, "rejected"):
            self.pack(("selected-v2",))

    def test_pack_existing_version_is_not_overwritten(self):
        self.register()
        self.pack()
        path = self.root / ".local/pack-v1/manifest.json"
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "new version"):
            self.pack()
        self.assertEqual(path.read_bytes(), before)

    def test_cli_register_search_and_private_pack(self):
        def invoke(script, *args):
            return subprocess.run([sys.executable, str(PROJECT / "scripts" / script),
                                   "--root", str(self.root), *args], text=True, capture_output=True)
        registered = invoke("reference_registry.py", "register", "--id", "selected-v1", "--path", str(self.image),
                            "--private", "--status", "user-approved", "--approval-evidence", "User selected this figure.",
                            "--tag", "transport")
        self.assertEqual(registered.returncode, 0, registered.stderr)
        result = invoke("afw.py", "search", "transport", "--include-private")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["id"], "selected-v1")
        args = ("priors", "--brief", str(self.brief), "--reference-id", "selected-v1", "--output-dir", str(self.root / ".local/cli-pack"))
        rejected = invoke("afw.py", *args)
        self.assertEqual(rejected.returncode, 2)
        success = invoke("afw.py", *args, "--allow-private")
        self.assertEqual(success.returncode, 0, success.stderr)
        self.assertEqual(json.loads(success.stdout)["references"][0]["path"], str(self.image))


if __name__ == "__main__":
    unittest.main()
