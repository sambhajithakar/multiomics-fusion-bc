# Deep Multi-Branch Fusion of Genomic, Transcriptomic, Proteomic and Methylation Data for Breast Cancer Subtyping and Recurrence Risk Prediction: A Schema-Matched Synthetic Benchmark

Code and synthetic data accompanying:

> Thakar S.B., Thakar P.S., Sangle A., Na D. "Deep Multi-Omics Fusion for Breast Cancer Molecular
> Subtyping and Recurrence Risk Prediction: A Schema-Matched Synthetic Proof-of-Concept."
> Submitted to *Artificial Intelligence in Medicine*.

This repository is a **synthetic, schema-matched proof-of-concept**, not an analysis of real
patient data. A cohort of 520 simulated patients is generated with genomics, transcriptomics,
proteomics and methylation features that share checkable, literature-consistent biological
structure (Section 2.2 of the manuscript), and a deep multi-branch fusion architecture is
benchmarked against PAM50-expression-only and single-omics baselines for (a) four-class molecular
subtype classification and (b) five-year recurrence risk prediction.

## Repository layout

```
data_simulation.py     Generates the synthetic multi-omics cohort -> data/
analysis_pipeline.py   Runs all benchmarks + bootstrap signature analysis -> outputs/
make_figures.py        Builds Figure 1 and correlation/p-value tables -> figures/, outputs/
build.js                docx build script for the manuscript -> manuscript/manuscript.docx
cover_letter.js         docx build script for the cover letter -> manuscript/cover_letter.docx
reviewer_list.js        docx build script for the suggested-reviewers list -> manuscript/reviewer_list.docx

data/                   Synthetic cohort CSVs (generated, not hand-edited)
outputs/                results.json, feature_importance_full.csv, signature_16.csv,
                         signature_marker_correlations.csv, signature_marker_pvals.csv
figures/                fig1_multiomics.png
manuscript/             manuscript.docx/.pdf, cover_letter.docx/.pdf, reviewer_list.docx/.pdf
```

## Reproducing the results

Requires Python 3.10+ and Node.js 18+.

```bash
pip install -r requirements.txt

python data_simulation.py      # writes data/*.csv (fixed seed -> deterministic)
python analysis_pipeline.py    # ~12-15 min on a single core; writes outputs/*.json, *.csv
python make_figures.py         # writes figures/fig1_multiomics.png, outputs/signature_marker_*.csv

npm install                          # installs docx (see package.json), one-time
node build.js                        # writes manuscript/manuscript.docx
node cover_letter.js                 # writes manuscript/cover_letter.docx
node reviewer_list.js                # writes manuscript/reviewer_list.docx
```

`analysis_pipeline.py` is the slow step: it runs 5-fold cross-validation repeated across 8 random
seeds (40 folds) for both the subtype and recurrence benchmarks, plus an 80-resample bootstrap
stability analysis over 187 candidate multi-omics features.

To also produce PDFs from the generated `.docx` files (used for the versions distributed with the
submission), any DOCX-to-PDF tool works, e.g. LibreOffice headless:

```bash
soffice --headless --convert-to pdf manuscript/manuscript.docx --outdir manuscript/
```

## What this is and isn't

- **Is:** a mechanical validation that the fusion architecture behaves as intended on a cohort
  whose ground truth is fully known and checkable by construction.
- **Isn't:** an analysis of real TCGA-BRCA or METABRIC data, and the recurrence-prediction
  comparison should not be read as evidence for or against a genuine multi-omics advantage in real
  cohorts (see Discussion, Section 4, and Limitations, Section 4.1, of the manuscript).

The random seed is fixed (`RNG_SEED = 20260922` in `data_simulation.py`), so every number and
table in the manuscript is exactly reproducible from this code.

## License

Code is provided for reproducibility of the accompanying manuscript. See `LICENSE` (MIT) for
reuse terms; the synthetic data carry no patient information and may be freely reused.
