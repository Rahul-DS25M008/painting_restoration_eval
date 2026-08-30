from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from restoration_eval.schemas import (
    SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA,
    SPATIAL_EXPLANATIONS_SCHEMA,
    get_schema,
    validate_dataframe,
)
from restoration_eval.spatial_explanations import (
    SPATIAL_EXPLANATIONS_MODULE_VERSION,
    attach_normalization_vmax,
    build_component_integration_plan,
    build_map_asset_record,
    build_spatial_explanation_population,
    compute_global_normalization,
    compute_group_uncertainty_map,
    load_group_work_map,
    load_numeric_map_archive,
    load_spatial_explanations_config,
    render_uncertainty_overlay,
    render_uncertainty_panel,
    render_selected_explanation_panel,
    select_representative_candidates,
    select_representative_explanations,
    summarize_group_uncertainty_map,
    validate_map_manifest,
    validate_spatial_explanations,
    write_group_work_map,
    write_numeric_map_archive,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/evaluation/spatial_explanations.yaml"


class SpatialExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_spatial_explanations_config(CONFIG_PATH)

    def _small_config(self) -> dict:
        config = deepcopy(self.config)
        settings = config["spatial_explanations"]
        settings["expected_counts"].update({
            "uncertainty_groups": 1,
            "unique_cases": 1,
            "candidates": 4,
            "generic_groups": 1,
            "scratch_aware_groups": 0,
            "representative_candidates": 1,
            "spatial_explanation_rows": 6,
            "numeric_map_archive_entries": 1,
            "map_manifest_rows": 1,
        })
        return config

    @staticmethod
    def _write_population_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        height, width = 32, 40
        yy, xx = np.mgrid[:height, :width]
        clean = np.stack([
            (xx * 5 + yy * 2) % 256,
            (yy * 7 + 20) % 256,
            ((xx + yy) * 4 + 30) % 256,
        ], axis=2).astype(np.uint8)
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[9:24, 12:29] = 255
        damaged = clean.copy()
        damaged[mask > 0] = 245
        paths: dict[str, str] = {}
        for name, array in {"clean": clean, "damaged": damaged, "mask": mask}.items():
            path = root / f"{name}.png"
            Image.fromarray(array).save(path)
            paths[name] = path.relative_to(root).as_posix()
        records = []
        for candidate_index, seed in enumerate((2026, 2027, 2028, 2029)):
            restored = clean.copy().astype(np.int16)
            restored[mask > 0] = np.clip(
                restored[mask > 0] + candidate_index * 6, 0, 255
            )
            restored_path = root / f"restored_{seed}.png"
            Image.fromarray(restored.astype(np.uint8)).save(restored_path)
            records.append({
                "candidate_id": f"candidate_{seed}",
                "case_id": "canonical__p001__scratch_thin",
                "model_id": "stable_diffusion_inpainting",
                "candidate_index": candidate_index,
                "seed": seed,
                "prompt_policy_id": "sd15_prompt_policy.v3",
                "prompt_variant_id": "p00_generic",
                "execution_role": "primary" if seed == 2026 else "uncertainty_extension",
                "configuration_id": "sd15_inpaint_fixed_policy_v1",
                "restored_path": restored_path.relative_to(root).as_posix(),
                "restored_sha256": f"sha{seed}",
                "mask_threshold": 128,
                "technical_validation_passed": True,
                "source_table_id": "notebook_11_stable_diffusion",
                "dataset_id": "painting_restoration_eval",
                "dataset_scope": "controlled_50",
                "experiment_id": "canonical_missing_region",
                "painting_id": "p001",
                "input_image_path": paths["damaged"],
                "clean_image_path": paths["clean"],
                "mask_or_effect_id": "mask_p001",
                "mask_or_effect_path": paths["mask"],
                "damage_or_degradation_type": "binary_missing_region",
                "target_damage_fraction": 0.05,
                "realized_damage_fraction": 0.06,
                "content_x_min": 0,
                "content_y_min": 0,
                "content_x_max": width,
                "content_y_max": height,
                "is_zero_control": False,
                "status": "completed",
            })
        artworks = pd.DataFrame([{
            "painting_id": "p001",
            "category": "portrait_figure",
            "style_or_period": "Baroque",
        }])
        return pd.DataFrame(records), artworks

    def test_config_and_schemas_are_registered(self) -> None:
        self.assertEqual(SPATIAL_EXPLANATIONS_MODULE_VERSION, "1.0.1")
        self.assertIs(get_schema("spatial_explanations"), SPATIAL_EXPLANATIONS_SCHEMA)
        self.assertIs(
            get_schema("spatial_explanation_map_images"),
            SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA,
        )
        settings = self.config["spatial_explanations"]
        self.assertEqual(settings["expected_counts"]["canonical_file_count"], 431)
        self.assertFalse(settings["evidence_policy"]["combined_explanation_score_retained"])
        self.assertEqual(settings["population"]["filename_identity"], "uncertainty_group_id")

    def test_exact_map_and_six_region_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist, artworks = self._write_population_inputs(root)
            config = self._small_config()
            population = build_spatial_explanation_population(
                worklist, artworks, config=config
            )
            representatives = select_representative_candidates(population, config=config)
            self.assertEqual(len(representatives), 1)
            uncertainty_map, regions = compute_group_uncertainty_map(
                population, project_root=root, config=config
            )
            arrays = [
                np.asarray(Image.open(root / f"restored_{seed}.png").convert("RGB"), dtype=np.float32) / 255.0
                for seed in (2026, 2027, 2028, 2029)
            ]
            expected_map = np.stack(arrays).std(axis=0, ddof=0).mean(axis=2)
            np.testing.assert_allclose(uncertainty_map, expected_map, atol=1e-7)
            summary = summarize_group_uncertainty_map(
                population, uncertainty_map, regions, config=config, normalization_vmax=0.2
            )
            validation = validate_spatial_explanations(summary, config=config)
            self.assertTrue(validation["passed"], validation)
            self.assertEqual(set(summary["region_id"]), set(config["spatial_explanations"]["regions"]["region_order"]))
            masked = summary.loc[summary["region_id"].eq("masked_region")].iloc[0]
            self.assertAlmostEqual(
                float(masked["mean_value"]),
                float(expected_map[regions["masked_region"].mask].mean()),
                places=7,
            )

    def test_checkpoint_archive_and_global_scale_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            array_a = np.linspace(0, 0.2, 120, dtype=np.float32).reshape(10, 12)
            array_b = np.flipud(array_a) * 0.8
            work_path = root / "work" / "ug_a.npz"
            write_group_work_map(work_path, "ug_a", (2026, 2027, 2028, 2029), array_a)
            loaded = load_group_work_map(
                work_path,
                expected_group_id="ug_a",
                expected_seeds=(2026, 2027, 2028, 2029),
            )
            np.testing.assert_allclose(loaded, array_a)
            maps = {"ug_a": array_a, "ug_b": array_b}
            masks = {key: np.ones_like(value, dtype=bool) for key, value in maps.items()}
            scale = compute_global_normalization(maps, masks, config=self.config)
            self.assertGreater(scale["vmax"], 0.0)
            self.assertLessEqual(scale["clipped_pixel_fraction"], 0.02)
            archive_path = root / "uncertainty_maps.npz"
            write_numeric_map_archive(maps, archive_path, archive_dtype="float16")
            reloaded = load_numeric_map_archive(archive_path)
            self.assertEqual(set(reloaded), set(maps))
            for key in maps:
                np.testing.assert_allclose(reloaded[key], maps[key], atol=5e-4)

    def test_uncertainty_panel_and_overlay_render(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist, artworks = self._write_population_inputs(root)
            config = self._small_config()
            population = build_spatial_explanation_population(worklist, artworks, config=config)
            uncertainty_map, regions = compute_group_uncertainty_map(
                population, project_root=root, config=config
            )
            panel_path = root / "panel.png"
            overlay_path = root / "overlay.png"
            render_uncertainty_panel(
                uncertainty_map, regions, panel_path,
                title="Synthetic uncertainty", vmin=0.0, vmax=0.2,
            )
            base = np.asarray(Image.open(root / "restored_2026.png").convert("RGB"))
            render_uncertainty_overlay(
                base, uncertainty_map, regions, overlay_path,
                title="Synthetic overlay", vmin=0.0, vmax=0.2,
            )
            for path in (panel_path, overlay_path):
                self.assertTrue(path.is_file())
                with Image.open(path) as image:
                    self.assertEqual(image.format, "PNG")
                    self.assertGreater(image.width, 500)
                    self.assertGreater(image.height, 300)
            with Image.open(panel_path) as image:
                self.assertEqual(image.mode, "RGBA")
                alpha_minimum, alpha_maximum = image.getchannel("A").getextrema()
                self.assertEqual(alpha_minimum, 0)
                self.assertEqual(alpha_maximum, 255)
            selected_path = root / "selected.png"
            render_selected_explanation_panel(
                [("Uncertainty", panel_path), ("Overlay", overlay_path)],
                selected_path,
                title="Selected synthetic explanation",
                columns=2,
            )
            with Image.open(selected_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 500)

    def test_component_integration_plan_separates_links_and_missing_local_maps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worklist, artworks = self._write_population_inputs(root)
            config = self._small_config()
            settings = config["spatial_explanations"]
            settings["expected_counts"]["upstream_error_component_links"] = 2
            settings["expected_counts"]["upstream_generic_local_component_links"] = 0
            settings["expected_counts"]["owned_scratch_aware_local_component_maps"] = 3
            population = build_spatial_explanation_population(
                worklist, artworks, config=config
            )
            representatives = select_representative_candidates(population, config=config)
            representatives["prompt_variant_id"] = "p05_scratch_aware"
            source_columns = [
                "map_image_id", "asset_kind", "candidate_id", "map_type",
                "relative_path", "sha256", "size_bytes", "width", "height",
                "image_mode", "format", "cmap", "vmin", "vmax", "center",
                "scale_scope", "quantization_policy", "no_data_policy",
                "renderer_version", "status",
            ]
            source_records = []
            for map_type in ("restored_absolute_error", "signed_improvement"):
                source_records.append({
                    "map_image_id": f"source_{map_type}",
                    "asset_kind": "candidate_map",
                    "candidate_id": representatives.iloc[0]["candidate_id"],
                    "map_type": map_type,
                    "relative_path": f"outputs/16/maps/{map_type}.png",
                    "sha256": "b" * 64,
                    "size_bytes": 100,
                    "width": 40,
                    "height": 32,
                    "image_mode": "P",
                    "format": "PNG",
                    "cmap": "magma" if map_type == "restored_absolute_error" else "RdBu",
                    "vmin": 0.0 if map_type == "restored_absolute_error" else -1.0,
                    "vmax": 1.0,
                    "center": np.nan if map_type == "restored_absolute_error" else 0.0,
                    "scale_scope": "test",
                    "quantization_policy": "indexed_uint8_documented_scale",
                    "no_data_policy": "not_applicable",
                    "renderer_version": "spatial_map_renderer.v1",
                    "status": "passed",
                })
            spatial_manifest = pd.DataFrame(source_records, columns=source_columns)
            local_manifest = pd.DataFrame(columns=source_columns)
            links, missing_local = build_component_integration_plan(
                representatives,
                spatial_manifest,
                local_manifest,
                config=config,
            )
            self.assertEqual(len(links), 2)
            self.assertEqual(set(links["map_type"]), {
                "restored_absolute_error", "signed_improvement"
            })
            self.assertEqual(len(missing_local), 3)
            self.assertEqual(set(missing_local["map_type"]), {"texture", "colour", "seam"})

    def test_manifest_record_and_validation(self) -> None:
        config = self._small_config()
        record = build_map_asset_record(
            {
                "uncertainty_group_id": "ug_test",
                "case_id": "canonical__p001__scratch_thin",
                "candidate_id": "candidate_2026",
                "model_id": "stable_diffusion_inpainting",
                "painting_id": "p001",
                "prompt_variant_id": "p00_generic",
            },
            asset_kind="uncertainty_panel",
            ownership="owned",
            map_type="uncertainty_variants",
            relative_path="outputs/19_uncertainty_and_spatial_explanation_maps/images/uncertainty/stable_diffusion_inpainting/ug_test.png",
            status="passed",
            sha256="a" * 64,
            size_bytes=100,
            width=1000,
            height=400,
            image_mode="RGBA",
            format="PNG",
            cmap="magma",
            vmin=0.0,
            vmax=0.2,
            scale_scope="test",
            normalization_policy_id="global_content_p99_5.v1",
            quantization_policy="RGBA uint8 presentation",
            no_data_policy="transparent_outside_selected_region",
        )
        frame = pd.DataFrame([record])
        schema = validate_dataframe(
            frame, SPATIAL_EXPLANATION_MAP_IMAGE_SCHEMA, allow_extra_columns=False
        )
        self.assertTrue(schema.passed, schema.to_dict())
        validation = validate_map_manifest(frame, config=config)
        self.assertTrue(validation["passed"], validation)

    def test_representative_selection_is_balanced_and_deterministic(self) -> None:
        config = deepcopy(self.config)
        settings = config["spatial_explanations"]
        settings["representative_panels"]["categories"] = ["portrait_figure"]
        settings["representative_panels"]["panel_count"] = 3
        rows = []
        group_specs = [
            ("ug_loss", "canonical__p001__loss_large", "loss_large", "p00_generic", 0.10, 0.04),
            ("ug_scratch_generic", "canonical__p002__scratch_thin", "scratch_thin", "p00_generic", 0.06, 0.05),
            ("ug_scratch_aware", "canonical__p002__scratch_thin", "scratch_thin", "p05_scratch_aware", 0.09, 0.05),
        ]
        for group_id, case_id, case_label, prompt_id, masked, boundary in group_specs:
            for region_id, value in (
                ("full_image", masked / 2),
                ("content_region", masked / 2),
                ("masked_region", masked),
                ("mask_bbox_crop", masked * 0.8),
                ("boundary_ring", boundary),
                ("outside_mask_content", masked / 4),
            ):
                rows.append({
                    "uncertainty_group_id": group_id,
                    "case_id": case_id,
                    "painting_id": case_id.split("__")[1],
                    "category": "portrait_figure",
                    "case_label": case_label,
                    "prompt_variant_id": prompt_id,
                    "representative_candidate_id": f"candidate_{group_id}",
                    "region_id": region_id,
                    "mean_value": value,
                })
        frame = pd.DataFrame(rows)
        first = select_representative_explanations(frame, config=config)
        second = select_representative_explanations(frame, config=config)
        pd.testing.assert_frame_equal(first, second)
        self.assertEqual(len(first), 3)
        self.assertEqual(first["selection_role"].nunique(), 3)


if __name__ == "__main__":
    unittest.main()
