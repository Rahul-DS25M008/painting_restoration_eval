# Painting Restoration Evaluation Review Package

This package contains the validated supervisor, publication, and reproducibility material produced by Notebook 36.

## Start here

1. Read [Supervisor Summary](reports/supervisor_summary.md).
2. Open [Final Evaluation Report](reports/final_evaluation.html).
3. Review the four model reports under `reports/models/`.
4. Use `tables/` for compact evidence and report indexes.
5. Use `figures/thesis/` and `figures/publication/` for final figures.
6. Read [Limitations and Deviations](reports/limitations_and_deviations.md).
7. Inspect the [Reproducibility Snapshot](provenance/reproducibility_snapshot.json).

## Package scope

The package contains:

- one final self-contained HTML report;
- four self-contained model reports;
- the Notebook 35 deployment-readiness report;
- three Notebook 36 supervisor-facing reports;
- 18 thesis figures;
- six publication figures;
- eight compact tables and report indexes;
- four model cards;
- 35 upstream run manifests;
- 25 evaluation-configuration snapshots;
- two environment declaration files;
- the Streamlit entry point and application helper;
- key findings, open questions, and feedback agenda;
- the Notebook 36 reproducibility snapshot.

## Headline evidence

- **50 paintings**
- **525 registered cases**
- **410 restoration cases**
- **1,785 approved candidates**
- **11 quality anchors**
- **165 repeated-seed uncertainty groups**
- **23,964 indexed visual records**
- **104 indexed reports**
- **10 bounded SDXL feasibility cases**

## Model conclusion

- **LaMa** is the strongest general benchmark baseline and leads 10 of 11 quality anchors.
- **OpenCV Telea** is the fastest deterministic baseline.
- **Stable Diffusion** provides prompt-conditioned and repeated-seed evidence but requires closer case-level review.
- **SDXL** remains a ten-case feasibility study rather than a fourth full benchmark.

## Important boundaries

- Visual plausibility is not historical correctness or restoration trustworthiness.
- Controlled synthetic damage does not establish real-world conservation generality.
- Repeated-seed variability is not calibrated confidence.
- Computational flags are not expert ground truth.
- No universal combined quality or trustworthiness score is reported.
- No result constitutes conservation approval.

## Reports

- [Supervisor summary](reports/supervisor_summary.md)
- [Final evaluation](reports/final_evaluation.html)
- [LaMa model report](reports/models/lama.html)
- [OpenCV Telea model report](reports/models/opencv_telea.html)
- [Stable Diffusion model report](reports/models/stable_diffusion_inpainting.html)
- [SDXL model report](reports/models/sdxl_inpainting.html)
- [Deployment readiness](reports/deployment_readiness.md)
- [Reproducibility appendix](reports/reproducibility_appendix.md)
- [Limitations and deviations](reports/limitations_and_deviations.md)

## Meeting material

- [Key findings](data/key_findings.json)
- [Open questions](data/open_questions.md)
- [Feedback agenda](data/feedback_agenda.md)

## Environment

- `environment/requirements.txt` is the dashboard environment.
- `environment/requirements_experiments.txt` is the notebook and experiment environment.
- Python 3.11 is recommended for a fresh environment.
- Python 3.11 and 3.12 are accepted by the project contract.

## Local dashboard

The included application files do not contain the complete Notebook 34 dashboard asset collection. Run the dashboard from the complete repository checkout:

```text
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Notebook 35 validated all eight pages for local demonstration. No completed public deployment URL is recorded.

## Material indexed but not bundled

To keep the package compact, it does not duplicate:

- the complete restoration-image collection;
- raw or processed paintings;
- full difference-map and uncertainty-map collections;
- 30 case reports and 50 painting reports;
- 30 selected-case grids;
- the complete Notebook 34 dashboard visual collection;
- model weights or caches;
- the full notebook repository.

These remain discoverable through the bundled indexes, manifests, and provenance records.

## Integrity

The external Notebook 36 package manifest records:

- each package-relative path;
- byte size;
- SHA-256 checksum;
- total file and byte counts;
- the package-tree checksum.

The package was assembled without restoration inference or scientific metric recomputation.
