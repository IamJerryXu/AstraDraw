"""Design decisions must reach the real image input; invalid plans publish nothing."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
import afw
import reference_registry


class DesignPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="afw-design-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.brief = self.root / "brief.json"
        self.brief.write_text(json.dumps({
            "title": "Conditioned update", "scientific_source": "Synthetic method section 3",
            "mechanism": "A condition controls one state update",
            "must_show": ["One update and its internal matrix operation"], "must_not_show": ["A second update"]}))
        image = self.root / "reference.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nsynthetic-reference-fixture")
        reference_registry.register("ref-a", image, license="original-project", root=self.root,
                                    aesthetic_status="user-approved", approval_evidence="Synthetic test approval")
        self.plan_path = self.root / "design-plan.json"
        self.output = self.root / "pack"
        self.plan = {
            "version": 1, "reader_question": "How does the condition change the update?",
            "main_message": "One conditioned update, with its matrix action expanded",
            "brief_sha256": afw.digest(self.brief),
            "method_graph": {
                "nodes": [
                    {"id": "state", "label": "Input state", "source": "Section 3 input",
                     "emphasis": "context", "representation": "A compact stack of three state tokens"},
                    {"id": "condition", "label": "Condition", "source": "Section 3 condition",
                     "emphasis": "support", "representation": "A narrow text strip above the update"},
                    {"id": "update", "label": "State update", "source": "Equation 4",
                     "emphasis": "primary", "representation": "Two differently sized matrices, with the retained columns aligned vertically"}],
                "edges": [
                    {"id": "state-update", "from": "state", "to": "update", "kind": "data",
                     "meaning": "State enters the update", "source": "Equation 4"},
                    {"id": "condition-update", "from": "condition", "to": "update", "kind": "conditioning",
                     "meaning": "Condition controls the update", "source": "Section 3 condition"}]},
            "layouts": [{
                "id": "overview-detail", "name": "Compact overview above a wide detail",
                "reading_order": ["state", "update"],
                "regions": [
                    {"id": "overview", "purpose": "Locate the update in context",
                     "node_ids": ["state", "condition", "update"], "placement": "across the top quarter",
                     "scale_priority": "small"},
                    {"id": "detail", "purpose": "Explain the internal matrix action",
                     "node_ids": ["update"], "placement": "across the lower three quarters",
                     "scale_priority": "large"}],
                "zoom_links": [{"source_node": "update", "target_region": "detail",
                                "treatment": "paired-no-arrows", "meaning": "The lower matrices expand the upper update"}],
                "tradeoff": "Prioritizes the matrix explanation over context",
                "reason_to_choose": "The internal update is the scientific contribution"}],
            "recommendation": "overview-detail",
            "reference_jobs": [{"reference_id": "ref-a", "borrow": ["Paired outline markers around overview and detail"],
                                "do_not_borrow": ["Reference paper's diffusion mechanism"], "for_regions": ["overview", "detail"]}],
            "style": {"profile": "comic", "labels_font": "Comic Sans MS", "math_font": "Cambria Math",
                      "palette": [
                          {"role": "condition", "fill": "#EEF8FF", "stroke": "#2876A8", "meaning": "conditioning input"},
                          {"role": "retained columns", "fill": "#FFE9DF", "stroke": "#A85330", "meaning": "columns retained by the update"}],
                      "line_roles": {"data": "solid dark arrow", "conditioning": "thin dashed arrow",
                                     "zoom": "matching rounded outlines and equal badges"},
                      "text_policy": "Use short noun phrases, never explanatory paragraphs inside matrices",
                      "operator_legend": [{"symbol": "⊙", "meaning": "elementwise multiplication"}]},
            "omit": [{"item": "training schedule", "reason": "It does not explain this operator", "source": "Section 4"}],
            "review_focus": [{"region": "detail", "question": "Is this visibly the same operation as the overview?"}]}

    def pack(self, plan=None, **kwargs):
        self.plan_path.write_text(json.dumps(self.plan if plan is None else plan), encoding="utf-8")
        return afw.make_priors(self.brief, output_dir=self.output, root=self.root,
                               reference_ids=["ref-a"], design_plan_path=self.plan_path, **kwargs)

    def rejects(self, plan, message=None, **kwargs):
        with self.assertRaisesRegex(ValueError, message or "Design plan|CLI style"):
            self.pack(plan, **kwargs)
        self.assertFalse(self.output.exists(), "Invalid design published an output directory")

    def alternate(self):
        layout = copy.deepcopy(self.plan["layouts"][0])
        layout.update(id="side-detail", name="Context left, matrix detail right",
                      tradeoff="More width for context", reason_to_choose="Fits a wide page")
        layout["regions"][0]["placement"] = "in a narrow left column"
        layout["regions"][1]["placement"] = "in a broad right column"
        self.plan["layouts"].append(layout)

    def test_compiles_selected_composition_and_semantics_into_actual_image_input(self):
        manifest = self.pack()
        prompt = afw.read_json(self.output / "image-tool-input.json")["prompt"]
        self.assertEqual(prompt, (self.output / "prompt.txt").read_text())
        for detail in ("across the top quarter", "large relative visual space", "State update",
                       "retained columns aligned vertically", "Condition controls the update", "thin dashed arrow",
                       "Cambria Math", "Comic Sans MS", "fill #FFE9DF, stroke #A85330", "columns retained by the update",
                       "Image 1 [ref-a] informs regions overview, detail", "Paired outline markers",
                       "Reference paper's diffusion mechanism", "elementwise multiplication", "training schedule",
                       "NO arrowheads or dataflow arrows", "SAME operation", "unstated scientific meaning"):
            self.assertIn(detail, prompt)
        self.assertNotIn('"layouts":', prompt)
        self.assertLess(prompt.index("Style:"), prompt.index("DESIGN DECISIONS"))
        self.assertEqual(manifest["design_plan_sha256"], afw.digest(self.plan_path))
        self.assertEqual(manifest["layout_id"], "overview-detail")
        self.assertEqual(manifest["style"], "comic")
        self.assertEqual(afw.read_json(self.output / "image-tool-input.json")["referenced_image_paths"],
                         [str(self.root / "reference.png")])

    def test_stale_scientific_brief_rejected(self):
        self.brief.write_text(self.brief.read_text() + "\n")
        self.rejects(self.plan, "brief_sha256")

    def test_explicit_style_conflict_rejected(self):
        self.rejects(self.plan, "style conflicts", style="roman")

    def test_unknown_style_profile_rejected(self):
        self.plan["style"]["profile"] = "unknown"
        self.rejects(self.plan, "style profile")

    def test_zoom_arrow_and_semantic_mismatches_rejected(self):
        invalid = copy.deepcopy(self.plan)
        invalid["layouts"][0]["zoom_links"][0]["treatment"] = "dashed-arrow"
        self.rejects(invalid, "zoom treatment")
        invalid = copy.deepcopy(self.plan)
        invalid["layouts"][0]["regions"][0]["node_ids"].remove("update")
        self.rejects(invalid, "non-target overview")
        invalid = copy.deepcopy(self.plan)
        invalid["layouts"][0]["regions"][1]["node_ids"] = ["state"]
        self.rejects(invalid, "same source node")

    def test_duplicate_identifiers_rejected(self):
        for path in (("method_graph", "nodes"), ("method_graph", "edges"), ("layouts",),
                     ("layouts", 0, "regions"), ("style", "palette")):
            with self.subTest(path=path):
                invalid = copy.deepcopy(self.plan)
                values = invalid
                for key in path:
                    values = values[key]
                values.append(copy.deepcopy(values[0]))
                self.rejects(invalid, "duplicate")

    def test_unknown_endpoints_regions_and_reading_order_rejected(self):
        invalid = copy.deepcopy(self.plan)
        invalid["method_graph"]["edges"][0]["to"] = "absent"
        self.rejects(invalid, "unknown endpoint")
        invalid = copy.deepcopy(self.plan)
        invalid["layouts"][0]["reading_order"].append("absent")
        self.rejects(invalid, "unknown IDs")
        invalid = copy.deepcopy(self.plan)
        invalid["layouts"][0]["regions"][0]["node_ids"].remove("condition")
        self.rejects(invalid, "no region")

    def test_reference_ids_and_jobs_must_cover_real_inputs(self):
        invalid = copy.deepcopy(self.plan)
        invalid["reference_jobs"][0]["reference_id"] = "invented-ref"
        self.rejects(invalid, "actual selected reference-id")
        invalid = copy.deepcopy(self.plan)
        invalid["reference_jobs"] = []
        self.rejects(invalid, "reference_jobs")
        invalid = copy.deepcopy(self.plan)
        invalid["reference_jobs"][0]["for_regions"] = ["other-layout-only"]
        self.rejects(invalid, "reference for_regions")

    def test_same_color_may_have_explicit_distinct_roles(self):
        self.plan["style"]["palette"][1]["fill"] = self.plan["style"]["palette"][0]["fill"]
        self.pack()

    def test_each_attached_reference_needs_a_job(self):
        reference_registry.register("ref-b", self.root / "reference.png", license="original-project", root=self.root,
                                    aesthetic_status="user-approved", approval_evidence="Synthetic test approval")
        self.plan_path.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError, "every actual input image: ref-b"):
            afw.make_priors(self.brief, output_dir=self.output, root=self.root,
                            reference_ids=["ref-a", "ref-b"], design_plan_path=self.plan_path)
        self.assertFalse(self.output.exists())

    def test_invalid_nested_shapes_raise_value_error(self):
        for key, value in (("method_graph", []), ("style", None), ("layouts", {}), ("review_focus", "detail")):
            invalid = copy.deepcopy(self.plan)
            invalid[key] = value
            self.rejects(invalid)
        invalid = copy.deepcopy(self.plan)
        invalid["method_graph"]["nodes"][0]["representation"] = {"hardcoded_type": "matrix"}
        self.rejects(invalid, "representation")

    def test_explicit_alternative_changes_composition(self):
        self.alternate()
        manifest = self.pack(layout_id="side-detail")
        prompt = (self.output / "prompt.txt").read_text()
        self.assertEqual(manifest["layout_id"], "side-detail")
        self.assertIn("in a broad right column", prompt)
        self.assertNotIn("across the lower three quarters", prompt)

    def test_alternative_selection_revalidates_reference_and_review_regions(self):
        self.alternate()
        self.plan["layouts"][1]["regions"][1]["id"] = "alternate-detail"
        self.plan["layouts"][1]["zoom_links"][0]["target_region"] = "alternate-detail"
        self.rejects(self.plan, "reference for_regions", layout_id="side-detail")

    def test_cli_emits_chosen_layout_and_rejects_missing_plan(self):
        self.alternate()
        self.plan_path.write_text(json.dumps(self.plan))
        command = [sys.executable, str(PROJECT / "scripts/afw.py"), "--root", str(self.root),
                   "priors", "--brief", str(self.brief), "--reference-id", "ref-a",
                   "--output-dir", str(self.output), "--layout", "side-detail"]
        missing = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("requires --design-plan", missing.stderr)
        self.assertFalse(self.output.exists())
        good = subprocess.run(command + ["--design-plan", str(self.plan_path)], text=True, capture_output=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)["layout_id"], "side-detail")

    def test_original_examples_compile_one_layout_without_reference_images(self):
        for flag, chosen, absent in (("--design-plan", "stacked", "side-by-side"),
                                      ("--design", "side-by-side", "stacked")):
            output = self.root / chosen
            command = [sys.executable, str(PROJECT / "scripts/afw.py"), "--root", str(self.root),
                       "priors", "--brief", str(PROJECT / "examples/design-brief.json"),
                       flag, str(PROJECT / "examples/design-plan.json"), "--layout", chosen,
                       "--output-dir", str(output)]
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads(result.stdout)
            self.assertEqual(manifest["layout_id"], chosen)
            self.assertEqual(manifest["references"], [])
            image_input = afw.read_json(output / "image-tool-input.json")
            self.assertNotIn("referenced_image_paths", image_input)
            self.assertIn(f"Use layout {chosen}", image_input["prompt"])
            self.assertNotIn(f"Use layout {absent}", image_input["prompt"])
            self.assertNotIn("The first image is", image_input["prompt"])
            self.assertIn("NO arrowheads or dataflow arrows", image_input["prompt"])


if __name__ == "__main__":
    unittest.main()
