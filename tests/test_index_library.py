"""Synthetic OOXML fixtures test metadata parsing, not deliverable generation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import warnings
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location("index_library", Path(__file__).resolve().parents[1] / "scripts/index_library.py")
lib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lib)

P = lib.NS["p"]
A = lib.NS["a"]
R = lib.NS["r"]


def fixture(path, bad_member=None, image_target="../media/image1.png"):
    with ZipFile(path, "w") as z:
        z.writestr("ppt/presentation.xml", f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="9" r:id="second"/><p:sldId id="8" r:id="first"/></p:sldIdLst><p:sldSz cx="1000" cy="500"/></p:presentation>')
        z.writestr("ppt/_rels/presentation.xml.rels", f'<Relationships xmlns="{lib.REL}"><Relationship Id="first" Target="slides/slide1.xml"/><Relationship Id="second" Target="slides/slide2.xml"/></Relationships>')
        content = f'<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"><p:cSld><p:spTree><p:grpSp><p:nvGrpSpPr><p:cNvPr id="4" name="group"/></p:nvGrpSpPr><p:sp><p:nvSpPr><p:cNvPr id="5" name="flow-label"/></p:nvSpPr><p:spPr><a:xfrm><a:off x="10" y="20"/><a:ext cx="30" cy="40"/></a:xfrm></p:spPr><p:txBody><a:p><a:r><a:t>Flow Matching ODE</a:t></a:r></a:p></p:txBody></p:sp></p:grpSp><p:pic><p:nvPicPr><p:cNvPr id="6" name="photo"/></p:nvPicPr><p:blipFill><a:blip r:embed="image"/></p:blipFill></p:pic><p:pic><p:nvPicPr><p:cNvPr id="7" name="external"/></p:nvPicPr><p:blipFill><a:blip r:link="external"/></p:blipFill></p:pic></p:spTree></p:cSld></p:sld>'
        z.writestr("ppt/slides/slide2.xml", content)
        z.writestr("ppt/slides/slide1.xml", f'<p:sld xmlns:p="{P}"><p:cSld><p:spTree/></p:cSld></p:sld>')
        z.writestr("ppt/slides/_rels/slide2.xml.rels", f'<Relationships xmlns="{lib.REL}"><Relationship Id="image" Target="{image_target}"/><Relationship Id="external" Target="https://invalid.example/private.png" TargetMode="External"/></Relationships>')
        z.writestr("ppt/media/image1.png", b"fixture image, no renderer invoked")
        if bad_member:
            z.writestr(bad_member, "unsafe")


class LibraryTests(unittest.TestCase):
    def test_order_relationships_groups_and_privacy(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            src = base / "source.pptx"
            fixture(src)
            before = src.read_bytes()
            result = lib.index_library(src, base / "out")
            self.assertEqual(before, src.read_bytes())
            self.assertEqual(result["slides"][0]["source"]["archive_member"], "ppt/slides/slide2.xml")
            self.assertEqual(result["slides"][0]["tags"], ["flow", "flow-matching", "ode"])
            child = result["slides"][0]["elements"][1]
            self.assertEqual(child["shape_id"], "5")
            self.assertEqual(child["group_ids"], ["4"])
            self.assertEqual(child["bbox_emu"], {"x": 10, "y": 20, "width": 30, "height": 40})
            self.assertEqual(result["summary"]["unique_extracted_asset_count"], 1)
            self.assertFalse(result["assets"][0]["redistributable"])
            self.assertEqual(result["slides"][0]["scientific_meaning"], "unknown")
            self.assertEqual(result["slides"][0]["elements"][-1]["image_assets"][0]["status"], "external-not-fetched")
            first = (base / "out/catalog.json").read_bytes()
            lib.index_library(src, base / "out")
            self.assertEqual(first, (base / "out/catalog.json").read_bytes())
            self.assertFalse(list((base / "out").rglob("*.pptx")))

    def test_bad_archive_paths_rejected(self):
        for name in ("../escape", "/absolute", "C:/escape", "ppt\\escape"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                fixture(base / "source.pptx", bad_member=name)
                with self.assertRaises(ValueError):
                    lib.index_library(base / "source.pptx", base / "out")
                self.assertFalse((base / "out").exists())

    def test_escaping_relationship_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            fixture(base / "source.pptx", image_target="../../../escape.png")
            with self.assertRaises(ValueError):
                lib.index_library(base / "source.pptx", base / "out")

    def test_tags_require_explicit_word_match(self):
        self.assertEqual(lib.explicit_tags("model code sides"), [])
        self.assertEqual(lib.explicit_tags("SDE flow-matching"), ["flow", "flow-matching", "sde"])

    def test_duplicate_archive_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            fixture(base / "source.pptx")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with ZipFile(base / "source.pptx", "a") as z:
                    z.writestr("ppt/presentation.xml", "duplicate")
            with self.assertRaises(ValueError):
                lib.index_library(base / "source.pptx", base / "out")

    def test_entity_declarations_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "unsafe.zip"
            with ZipFile(path, "w") as z:
                z.writestr("part.xml", '<!DOCTYPE x [<!ENTITY secret "expanded">]><x>&secret;</x>')
            with ZipFile(path) as z, self.assertRaises(ValueError):
                lib.xml(z, "part.xml")


if __name__ == "__main__":
    unittest.main()
