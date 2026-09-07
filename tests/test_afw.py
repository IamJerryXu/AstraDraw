"""Independent CLI/helper checks with synthetic fixtures, no model calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("afw", PROJECT / "scripts/afw.py")
afw = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(afw)


class AfwTests(unittest.TestCase):
    def setUp(self):
        test_root = PROJECT / ".local/forward-test"
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="afw-unit-", dir=test_root)
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.write("components/catalog.json", [{
            "id": "ode-roman", "component": "ode", "style": "roman",
            "preview": "previews/ode-roman.png", "license": "original-project",
            "tags": ["ode", "deterministic"]}])
        self.preview = self.root / "previews/ode-roman.png"
        self.preview.parent.mkdir()
        self.preview.write_bytes(b"synthetic-byte-fixture-not-for-visual-use")
        self.brief = {"title": "Decay", "scientific_source": "User equation dx/dt=-x",
                      "mechanism": "x(t)=x(0) exp(-t)",
                      "must_show": ["monotonic convergence to equilibrium"],
                      "must_not_show": ["noise", "branching"]}
        self.write("brief.json", self.brief)

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def pack(self, **kwargs):
        return afw.make_priors(self.root / "brief.json", "ode", "roman",
                               self.root / "pack", root=self.root, **kwargs)

    def private_library(self):
        source = self.root / "source.pptx"
        source.write_bytes(b"private source fixture")
        media = self.root / ".local/library/assets/photo.png"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"private bitmap fixture")
        self.write(".local/library/catalog.json", {
            "source": {"path": str(source), "sha256": afw.digest(source)},
            "slides": [{"id": "slide-1", "slide_number": 1, "title": "ODE",
                        "text": "Private reference", "tags": ["ode"]}],
            "assets": [{"id": "image-1", "kind": "bitmap", "path": "assets/photo.png",
                        "sha256": afw.digest(media)}]})
        return source, media

    def make_pptx(self, xml=None):
        if xml is None:
            xml = '''<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
                xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <p:cSld><p:spTree><p:sp><p:nvSpPr><p:cNvPr id="7" name="initial-label"/>
              </p:nvSpPr><p:txBody><a:p><a:r><a:t>Initial states</a:t></a:r></a:p></p:txBody>
              </p:sp></p:spTree></p:cSld></p:sld>'''
        path = self.root / "diagram.pptx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("ppt/slides/slide1.xml", xml)
        return path

    def test_search_scopes_style_and_private_opt_in(self):
        self.private_library()
        self.assertEqual([x["id"] for x in afw.search("ODE", "roman", root=self.root)], ["ode-roman"])
        self.assertEqual(afw.search("ODE", "comic", root=self.root), [])
        self.assertEqual(len(afw.search("ODE", root=self.root)), 1)
        private = afw.search("ODE", include_private=True, root=self.root)[1]
        self.assertEqual(private["usage"], "reference-only")
        self.assertEqual(private["license"], "unknown")

    def test_priors_carry_real_paths_hashes_science_and_pending_status(self):
        manifest = self.pack()
        reference = manifest["references"][0]
        self.assertEqual(reference["path"], str(self.preview.resolve()))
        self.assertEqual(reference["sha256"], hashlib.sha256(self.preview.read_bytes()).hexdigest())
        self.assertEqual(manifest["status"], "prepared-not-generated")
        self.assertTrue(manifest["requires_visual_inspection_before_call"])
        self.assertTrue(manifest["requires_scientific_review_after_call"])
        tool = afw.read_json(self.root / "pack/image-tool-input.json")
        self.assertEqual(tool["referenced_image_paths"], [reference["path"]])
        for phrase in ("dx/dt=-x", "x(t)=x(0) exp(-t)", "monotonic convergence", "noise", "Times/Roman"):
            self.assertIn(phrase, tool["prompt"])
        self.assertIn("not an instruction", tool["prompt"])

    def test_scientific_brief_missing_fields_rejected_without_output(self):
        for key in self.brief:
            with self.subTest(field=key):
                brief = {k: v for k, v in self.brief.items() if k != key}
                self.write("brief.json", brief)
                with self.assertRaises(ValueError):
                    self.pack()
                self.assertFalse((self.root / "pack").exists())

    def test_constraints_must_be_text_lists(self):
        self.write("brief.json", {**self.brief, "must_show": [4]})
        with self.assertRaises(ValueError):
            self.pack()

    def test_existing_output_never_overwritten(self):
        self.pack()
        before = (self.root / "pack/manifest.json").read_bytes()
        with self.assertRaises(ValueError):
            self.pack()
        self.assertEqual(before, (self.root / "pack/manifest.json").read_bytes())

    def test_missing_preview_rejected(self):
        self.preview.unlink()
        with self.assertRaises(ValueError):
            self.pack()
        self.assertFalse((self.root / "pack").exists())

    def test_reference_path_escape_rejected(self):
        with self.assertRaises(ValueError):
            afw.contained(self.root, "../outside.png")
        self.assertEqual(afw.contained(self.root, "previews/ode-roman.png"), self.preview.resolve())

    def test_private_references_need_opt_in_and_local_destination(self):
        self.private_library()
        with self.assertRaises(ValueError):
            self.pack(private_assets=["image-1"])
        with self.assertRaises(ValueError):
            self.pack(private_assets=["image-1"], allow_private=True)
        manifest = afw.make_priors(self.root / "brief.json", "ode", "roman",
                                   self.root / ".local/pack", ["image-1"], True, root=self.root)
        self.assertTrue(manifest["private"])
        self.assertFalse(manifest["references"][1]["redistributable"])
        self.assertEqual(manifest["references"][1]["role"], "style-only-reference")

    def test_private_source_and_asset_integrity(self):
        source, media = self.private_library()
        original = source.read_bytes()
        source.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "source changed"):
            afw.make_priors(self.root / "brief.json", "ode", "roman", self.root / ".local/pack",
                            ["image-1"], True, root=self.root)
        source.write_bytes(original)
        media.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            afw.make_priors(self.root / "brief.json", "ode", "roman", self.root / ".local/pack",
                            ["image-1"], True, root=self.root)

    def test_inspect_maps_id_and_name_not_numeric_id_alone(self):
        pptx = self.make_pptx()
        mapping = [{"slide_number": 1, "scene_id": "ode-comic", "objects": [
            {"pptx_shape_id": "7", "pptx_shape_name": "initial-label", "scene_object_id": "initial-label"}]}]
        self.write("diagram.object-map.json", mapping)
        result = afw.inspect_pptx(pptx, shape_id="7")
        self.assertEqual(result["shapes"][0]["scene_object_id"], "initial-label")
        mapping[0]["objects"][0]["pptx_shape_name"] = "different"
        self.write("diagram.object-map.json", mapping)
        self.assertNotIn("scene_object_id", afw.inspect_pptx(pptx)["shapes"][0])

    def test_inspect_rejects_missing_slide_shape_and_entity_declarations(self):
        pptx = self.make_pptx()
        for kwargs in ({"slide": 0}, {"slide": 2}, {"shape_id": "999"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                afw.inspect_pptx(pptx, **kwargs)
        self.make_pptx('<!DOCTYPE x [<!ENTITY y "x">]><x/>')
        with self.assertRaisesRegex(ValueError, "entity"):
            afw.inspect_pptx(pptx)

    def test_cli_inspect_real_entry_point(self):
        pptx = self.make_pptx()
        result = subprocess.run([sys.executable, str(PROJECT / "scripts/afw.py"), "inspect-pptx",
                                 "--pptx", str(pptx), "--slide", "1", "--shape-id", "7"],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["shapes"][0]["name"], "initial-label")
        failed = subprocess.run([sys.executable, str(PROJECT / "scripts/afw.py"), "inspect-pptx",
                                 "--pptx", str(pptx), "--slide", "0"], text=True, capture_output=True)
        self.assertEqual(failed.returncode, 2)
        self.assertIn("Slide numbers start at 1", failed.stderr)


if __name__ == "__main__":
    unittest.main()
