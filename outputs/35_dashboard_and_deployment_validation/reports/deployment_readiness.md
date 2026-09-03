# Dashboard Deployment-Readiness Report

**Notebook:** `35_dashboard_and_deployment_validation.ipynb`  
**Application:** `streamlit_app.py`  
**Validated package:** `outputs/34_final_streamlit_dashboard_assets/`  
**Assessment:** `conditionally_ready_for_local_demonstration`  
**Runtime tested:** Streamlit `1.59.0`  
**Deployment pin:** Streamlit `1.56.0`

## 1. Decision

The dashboard is **ready for local supervisor demonstration** in the tested environment.

It is **not yet recorded as a reproducible public deployment**. The application passed all eight runtime page tests, but 4 installed package versions differ from the declared deployment pins and no public deployment URL is recorded.

### What this means

- The dashboard can be used locally to inspect the validated thesis evidence.
- The application does not create restorations or recompute scientific metrics.
- Representative examples support orientation; the complete indexed evidence remains filterable.
- Public-deployment completion should be claimed only after dependency reconciliation and an external deployment check.

## 2. Readiness matrix

| Component | Status | Evidence | Conclusion | Next Action |
| --- | --- | --- | --- | --- |
| Notebook 34 evidence package | ready | 76 package checks passed; 19 physical files validated | The application has a complete, fixed presentation package. | None |
| Indexed evidence access | ready | 1,785 candidates; 50 paintings; 23,964 visual records; 104 reports | Representative defaults do not prevent complete indexed inspection. | None |
| Scientific boundaries | ready | No inference, metric recomputation, combined score, or unsupported claim | The dashboard remains an inspection and decision-support layer. | None |
| Approved UI traceability | ready | 72 of 72 page/aspect mappings passed | The implemented application retains the approved museum-research design. | None |
| Eight-page runtime | ready | 8 pages passed in 13.28s | The current local environment is suitable for supervisor demonstration. | None for local use |
| Portable reports | ready | 104 of 104 reports are self-contained | Downloaded reports retain their required content without repository-relative images. | None |
| Dependency-pin alignment | action_required | 4 package versions differ | The tested environment works, but exact deployment reproducibility is not yet locked. | Recreate the environment from requirements.txt |
| External deployment | not_deployed | No public URL is recorded | Local readiness must not be described as completed public deployment. | Deploy externally, then record the platform and URL |

## 3. Runtime evidence

All eight principal pages rendered without an uncaught exception or visible application error.

| Display Name | Runtime Seconds | Exception Count | Visible Error Count | Passed |
| --- | --- | --- | --- | --- |
| Overview | 4.126 | 0 | 0 | True |
| Study Design | 2.633 | 0 | 0 | True |
| Metric Framework | 0.405 | 0 | 0 | True |
| Model Performance | 0.830 | 0 | 0 | True |
| Robustness & Uncertainty | 0.972 | 0 | 0 | True |
| Trustworthiness & XAI | 2.196 | 0 | 0 | True |
| Case Explorer | 1.762 | 0 | 0 | True |
| Reports & Reproducibility | 0.360 | 0 | 0 | True |

**Runtime conclusion:** the application completed all page transitions in 13.284 seconds. The slowest page was **Overview** at 4.126 seconds. This is suitable for local presentation and interactive inspection.

## 4. Evidence available through the dashboard

- **50 paintings**
- **410 restoration cases**
- **1,785 approved candidates**
- **23,964 indexed visual records**
- **104 self-contained reports**
- **130 canonical repeated-seed uncertainty groups**
- **35 damage-size uncertainty groups**
- **10 bounded SDXL candidates**

The Case Explorer exposes original, damaged, mask, restored, and diagnostic evidence. The Trustworthiness & XAI page also exposes the complete visual catalogue, including supporting prompt-ablation maps that remain separate from the approved candidate index.

## 5. Scientific interpretation limits

- Visual plausibility is not historical correctness, authenticity, conservation approval, or restoration trustworthiness.
- Metrics remain separate by family and region; the application does not create a universal combined score.
- Repeated-seed variation is empirical diffusion uncertainty, not calibrated confidence.
- Mask and degradation sensitivity are robustness evidence, not generative uncertainty.
- Computational flags support review; they are not expert ground truth.
- Retrieval results provide context and do not prove restoration correctness.
- SDXL is a ten-case feasibility study, not a fourth complete benchmark.

**Scientific conclusion:** the dashboard is suitable for evidence inspection and communication. It is not an experiment runner, restoration tool, or conservation decision system.

## 6. Dependency reconciliation

- **pillow:** tested with `9.5.0`; deployment pin is `12.3.0`.
- **plotly:** tested with `6.8.0`; deployment pin is `6.9.0`.
- **pyarrow:** tested with `24.0.0`; deployment pin is `20.0.0`.
- **streamlit:** tested with `1.59.0`; deployment pin is `1.56.0`.

The current environment passed the complete runtime smoke test despite these differences. Exact deployment reproducibility still requires installing the versions declared in `requirements.txt` and repeating the eight-page smoke test.

## 7. External deployment state

No public deployment URL is recorded. The validated result is local application readiness, not completed external deployment.

Before claiming completed external deployment:

1. Create a clean environment from `requirements.txt`.
2. Run `python -m streamlit run streamlit_app.py`.
3. Verify all eight pages and representative downloads.
4. Confirm that repository-indexed assets are available on the deployment host.
5. Record the deployment platform and public URL in the Notebook 35 configuration.
6. Rerun Notebook 35 and persist a new readiness report.

## 8. Local launch

From the repository root:

```text
python -m streamlit run streamlit_app.py
```

The application reads only the fixed Notebook 34 dashboard package. It must not be redirected to legacy global output folders.

## 9. Final conclusion

Local demonstration: ready.
Scientific presentation boundary: passed.
Complete indexed access: passed.

Exact dependency alignment: action required.
External deployment: not deployed.

The current validated outcome is therefore conditional local readiness, not completed public deployment.
