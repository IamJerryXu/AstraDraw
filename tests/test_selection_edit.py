import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("selection_edit", Path(__file__).resolve().parents[1] / "scripts/selection_edit.py")
editor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(editor)


def fixture():
    return {"schema_version": 1, "id": "example", "component": "ode", "style": "roman",
            "width": 500, "height": 300, "scientific_notes": ["Illustrative only"],
            "objects": [
                {"id": "a", "type": "rect", "role": "source", "x": 20, "y": 20,
                 "width": 40, "height": 40, "fill": "#fff", "stroke": "#000", "strokeWidth": 1},
                {"id": "b", "type": "ellipse", "role": "target", "x": 200, "y": 20,
                 "width": 40, "height": 40, "fill": "#fff", "stroke": "#000", "strokeWidth": 1},
                {"id": "label", "type": "text", "role": "label", "x": 20, "y": 100,
                 "width": 100, "height": 20, "text": "ODE", "fontFamily": "Times New Roman",
                 "fontSize": 14, "fill": "#000"},
                {"id": "wire", "type": "polyline", "role": "connection",
                 "points": [[60, 40], [100, 40], [200, 40]], "fill": "none",
                 "stroke": "#000", "strokeWidth": 1, "source": "a", "target": "b",
                 "source_anchor": "right", "target_anchor": "left"}]}


def request(ids=None, operations=None, **kwargs):
    return {"scene_id": "example", "selected_ids": ids or ["a"],
            "operations": operations or [{"op": "move", "dx": 10, "dy": 5}], **kwargs}


class SelectionTests(unittest.TestCase):
    def test_multiple_selected_and_attached_endpoints(self):
        original = fixture()
        snapshot = copy.deepcopy(original)
        result, audit = editor.apply_request(original, request(["a", "b"]))
        self.assertEqual(original, snapshot)
        self.assertEqual(result["objects"][3]["points"], [[70, 45], [100, 40], [210, 45]])
        self.assertEqual(result["objects"][2], original["objects"][2])
        self.assertEqual(audit["changed_ids"], ["a", "b", "wire"])
        self.assertEqual(len(audit["related_endpoints"]), 2)
        self.assertEqual(audit["object_hashes"]["label"]["before"], audit["object_hashes"]["label"]["after"])
        self.assertTrue(audit["no_unselected_drift"])

    def test_polyline_moves_all_points(self):
        result, audit = editor.apply_request(fixture(), request(["wire"]))
        self.assertEqual(result["objects"][3]["points"], [[70, 45], [110, 45], [210, 45]])
        self.assertEqual(audit["changed_ids"], ["wire"])

    def test_explicit_text_requires_scientific_review(self):
        _, audit = editor.apply_request(fixture(), request(["label"], [{"op": "set", "properties": {"text": "SDE"}}]))
        self.assertTrue(audit["scientific_review_required"])

    def test_semantic_color_needs_explicit_flag(self):
        scene = fixture()
        scene["objects"][0]["semantic_color"] = True
        req = request(operations=[{"op": "set", "properties": {"fill": "#f00"}}])
        with self.assertRaises(editor.EditError):
            editor.apply_request(scene, req)
        _, audit = editor.apply_request(scene, {**req, "allow_semantic_color": True})
        self.assertTrue(audit["scientific_review_required"])

    def test_invalid_selection(self):
        for ids in ([], ["missing"], ["a", "a"], [1]):
            with self.subTest(ids=ids), self.assertRaises(editor.EditError):
                editor.apply_request(fixture(), {**request(), "selected_ids": ids})

    def test_missing_and_ambiguous_scene_ids(self):
        for change in (lambda s: s["objects"].append(copy.deepcopy(s["objects"][0])),
                       lambda s: s["objects"][0].pop("id")):
            scene = fixture()
            change(scene)
            with self.assertRaises(editor.EditError):
                editor.apply_request(scene, request())
        with self.assertRaises(editor.EditError):
            editor.apply_request(fixture(), {**request(), "scene_id": "wrong"})

    def test_locked_objects_and_connectors(self):
        for index in (0, 3):
            scene = fixture()
            scene["objects"][index]["locked"] = True
            with self.assertRaises(editor.EditError):
                editor.apply_request(scene, request())

    def test_bad_values_unsupported_setters_and_clipping(self):
        operations = [
            {"op": "move", "dx": float("nan"), "dy": 0},
            {"op": "move", "dx": True, "dy": 0},
            {"op": "move", "dx": -100, "dy": 0},
            {"op": "set", "properties": {"width": 10}},
            {"op": "set", "properties": {"strokeWidth": float("inf")}},
            {"op": "set", "properties": {"strokeWidth": -1}},
            {"op": "set", "properties": {"text": "wrong object type"}},
            {"op": "delete"}]
        for operation in operations:
            with self.subTest(op=operation), self.assertRaises(editor.EditError):
                editor.apply_request(fixture(), request(operations=[operation]))

    def test_stale_hash(self):
        with self.assertRaises(editor.EditError):
            editor.apply_request(fixture(), request(expected_sha256="old"), "new")
        editor.apply_request(fixture(), request(expected_sha256="same"), "same")

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(editor.EditError):
            editor.parse_json('{"id":"a","id":"b"}')

    def test_files_atomic_validation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, req, output = (root / p for p in ("source.json", "request.json", "new.json"))
            source.write_text(json.dumps(fixture()))
            original = source.read_bytes()
            bad = request(operations=[{"op": "move", "dx": 2, "dy": 0}, {"op": "delete"}])
            req.write_text(json.dumps(bad))
            with self.assertRaises(editor.EditError):
                editor.edit_files(source, req, output)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix(".audit.json").exists())
            self.assertEqual(source.read_bytes(), original)
            req.write_text(json.dumps(request(expected_sha256=editor.digest(original))))
            audit = editor.edit_files(source, req, output)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(audit["output_sha256"], editor.digest(output.read_bytes()))
            self.assertTrue(output.with_suffix(".audit.json").exists())
            saved = output.read_bytes()
            with self.assertRaises(editor.EditError):
                editor.edit_files(source, req, output)
            self.assertEqual(saved, output.read_bytes())
            with self.assertRaises(editor.EditError):
                editor.edit_files(source, req, source)

    def test_publish_failure_rolls_back_first_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_link = editor.os.link
            calls = []
            def fail_second(source, destination):
                calls.append(destination)
                if len(calls) == 2:
                    raise OSError("simulated audit publication failure")
                real_link(source, destination)
            with patch.object(editor.os, "link", side_effect=fail_second):
                with self.assertRaises(OSError):
                    editor.write_exclusive_pair(root / "out.json", b"{}", root / "out.audit.json", b"{}")
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
