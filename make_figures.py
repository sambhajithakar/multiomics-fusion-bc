"""Generate the main figure and supplementary correlation table for the
multi-omics manuscript, reading from the outputs of analysis_pipeline.py."""
import json
import numpy as np
import pandas as pd
from scipy import stats as sstats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def benjamini_hochberg(pvals):
    """Return BH-adjusted p-values for a 1-D array of raw p-values."""
    pvals = np.asarray(pvals)
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    bh = ranked * n / (np.arange(n) + 1)
    bh_sorted = np.minimum.accumulate(bh[::-1])[::-1]
    padj = np.empty(n)
    padj[order] = np.clip(bh_sorted, 0, 1)
    return padj

results = json.load(open("outputs/results.json"))
clinical = pd.read_csv("data/data_clinical.csv")
genomics = pd.read_csv("data/data_genomics.csv")
transcriptomics = pd.read_csv("data/data_transcriptomics.csv")
proteomics = pd.read_csv("data/data_proteomics.csv")
methylation = pd.read_csv("data/data_methylation.csv")
all_layers = genomics.merge(transcriptomics, on="patient_id").merge(
    proteomics, on="patient_id").merge(methylation, on="patient_id")

MARKER_GENES = {"ER/luminal (ESR1)": "ESR1", "HER2 (ERBB2)": "ERBB2",
                 "Proliferation (AURKA)": "AURKA", "Basal (KRT5)": "KRT5"}

sig = pd.DataFrame(results["signature_16"])
sig_features = sig["feature"].tolist()

corr_mat = np.zeros((len(sig_features), len(MARKER_GENES)))
pval_rows = []
for i, feat in enumerate(sig_features):
    for j, (label, gene) in enumerate(MARKER_GENES.items()):
        r, pv = sstats.pearsonr(all_layers[feat], all_layers[gene])
        corr_mat[i, j] = r
        pval_rows.append({"feature": feat, "marker": gene, "r": r, "p": pv})

corr_df = pd.DataFrame(corr_mat, index=sig_features, columns=list(MARKER_GENES.keys()))
corr_df.to_csv("outputs/signature_marker_correlations.csv")
print(corr_df.round(3))

pval_df = pd.DataFrame(pval_rows)
pval_df["p_adj"] = benjamini_hochberg(pval_df["p"].values)
pval_df.to_csv("outputs/signature_marker_pvals.csv", index=False)
n_sig = int((pval_df["p_adj"] < 0.05).sum())
print(f"{n_sig}/{len(pval_df)} feature-marker correlations significant at BH-adjusted p<0.05")

# ---------------- Figure 1 (4-panel) ----------------
fig = plt.figure(figsize=(12.0, 11.5))
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.32)

# Panel A: subtype benchmark bar chart
axA = fig.add_subplot(gs[0, 0])
methods = ["PAM50\nexpression", "Genomics\nonly", "Transcriptomics\nonly",
           "Proteomics\nonly", "Methylation\nonly", "Naive\nconcatenation",
           "Deep\nmulti-omics\nfusion"]
keys = ["PAM50_expression_only", "genomics_only", "transcriptomics_only",
        "proteomics_only", "methylation_only", "naive_concatenation",
        "deep_multiomics_fusion"]
means = [results["subtype_benchmark"][k]["mean"] for k in keys]
sds = [results["subtype_benchmark"][k]["sd"] for k in keys]
colors = ["#4C72B0"]*1 + ["#8C8C8C"]*4 + ["#55A868", "#C44E52"]
axA.bar(range(len(methods)), means, yerr=sds, color=colors, capsize=3, edgecolor="black", linewidth=0.5)
axA.set_xticks(range(len(methods))); axA.set_xticklabels(methods, fontsize=6.8, rotation=28, ha="right")
axA.set_ylabel("Macro-average AUC (OvR)")
axA.set_ylim(0.75, 1.02)
axA.set_title("A. Molecular subtype classification\n(5-fold CV x 8 repeats)", fontsize=10, loc="left")
axA.axhline(1.0, color="grey", linewidth=0.5, linestyle=":")

# Panel B: bootstrap stability of top signature features
axB = fig.add_subplot(gs[0, 1])
sig_sorted = sig.sort_values("mean_importance", ascending=True)
axB.barh(sig_sorted["feature"], sig_sorted["bootstrap_stability"], color="#4C72B0", edgecolor="black", linewidth=0.5)
axB.set_xlabel("Bootstrap stability frequency (80 resamples)")
axB.set_xlim(0, 1.05)
axB.axvline(0.70, color="red", linestyle="--", linewidth=1)
axB.set_title("B. 16-feature robust multi-omics\nsignature stability", fontsize=10, loc="left")
axB.tick_params(axis='y', labelsize=7.5)

# Panel C: recurrence prediction AUC
axC = fig.add_subplot(gs[1, 0])
rkeys = ["PAM50_subtype_plus_clinical", "deep_multiomics_fusion_plus_clinical"]
rlabels = ["PAM50 subtype\n+ clinical", "Deep multi-omics\nfusion + clinical"]
rmeans = [results["recurrence_benchmark"][k]["mean"] for k in rkeys]
rsds = [results["recurrence_benchmark"][k]["sd"] for k in rkeys]
axC.bar(rlabels, rmeans, yerr=rsds, color=["#4C72B0", "#C44E52"], capsize=4, edgecolor="black", linewidth=0.5, width=0.55)
axC.set_ylabel("AUC (5-year recurrence)")
axC.set_ylim(0.6, 0.95)
pc = results["recurrence_paired_comparison"]
axC.set_title(f"C. 5-year recurrence prediction\n(paired ΔAUC = {pc['mean_delta_AUC_fusion_minus_pam50']:+.4f}, "
              f"Wilcoxon p = {pc['wilcoxon_pval']:.2f})", fontsize=9.5, loc="left")

# Panel D: signature-marker correlation heatmap
axD = fig.add_subplot(gs[1, 1])
im = axD.imshow(corr_df.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
axD.set_xticks(range(len(corr_df.columns))); axD.set_xticklabels(corr_df.columns, fontsize=7, rotation=30, ha="right")
axD.set_yticks(range(len(corr_df.index))); axD.set_yticklabels(corr_df.index, fontsize=6.8)
for i in range(corr_df.shape[0]):
    for j in range(corr_df.shape[1]):
        axD.text(j, i, f"{corr_df.values[i,j]:.2f}", ha="center", va="center", fontsize=5.8,
                  color="white" if abs(corr_df.values[i,j]) > 0.55 else "black")
cbar = fig.colorbar(im, ax=axD, fraction=0.046, pad=0.04)
cbar.ax.tick_params(labelsize=7)
axD.set_title("D. Signature feature correlation\nwith canonical markers", fontsize=10, loc="left")

fig.suptitle("Deep Multi-Omics Fusion for Breast Cancer Molecular Subtyping and Recurrence Prediction",
             fontsize=11.5, fontweight="bold", y=0.995)
fig.savefig("figures/fig1_multiomics.png", dpi=300, bbox_inches="tight")
print("Saved figures/fig1_multiomics.png")
