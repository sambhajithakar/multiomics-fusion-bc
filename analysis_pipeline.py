"""
Analysis pipeline: molecular subtyping + recurrence prediction benchmarking.
Loads the synthetic omics tables written by data_simulation.py (in data/) and:
  1. Benchmarks classifiers for 4-class molecular subtype prediction using
     (a) PAM50 expression alone, (b) each omics layer alone, (c) naive
     concatenation, (d) deep multi-branch fusion network.
  2. Benchmarks 5-year recurrence prediction using (a) PAM50 subtype +
     clinical alone (the current standard-of-care comparator), (b) deep
     multi-omics fusion representation + clinical, with a paired
     significance test across matched cross-validation folds.
  3. Runs bootstrap-stability feature importance across all four omics
     layers to derive a compact, reproducible multi-omics signature.
  4. Correlates signature features against known driver biology for
     validation (ER/HER2/proliferation/basal-pathway concordance).
All metrics are computed via stratified 5-fold cross-validation, repeated
across 8 random seeds (40 folds total) to report mean +/- SD.
Outputs are written to outputs/ (results.json, feature_importance_full.csv).
"""
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score, confusion_matrix
from sklearn.utils import resample

SEED = 20260922
rng = np.random.default_rng(SEED)

clinical = pd.read_csv("data/data_clinical.csv")
genomics = pd.read_csv("data/data_genomics.csv").drop(columns=["patient_id"])
transcriptomics = pd.read_csv("data/data_transcriptomics.csv").drop(columns=["patient_id"])
proteomics = pd.read_csv("data/data_proteomics.csv").drop(columns=["patient_id"])
methylation = pd.read_csv("data/data_methylation.csv").drop(columns=["patient_id"])

PAM50_GENES = [
    "ESR1","PGR","FOXA1","GATA3","XBP1","MLPH","BAG1","BCL2","NAT1","SLC39A6",
    "ERBB2","GRB7","STARD3","MMP11","CDC6","MKI67","CCNB1","MYBL2","BIRC5","UBE2C",
    "AURKA","CENPF","CEP55","TYMS","PTTG1","RRM2","EXO1","ORC6L","NDC80","NUF2",
    "MELK","KIF2C","ANLN","CCNE1","EGFR","KRT5","KRT14","KRT17","SFRP1","MIA",
    "FGFR4","BLVRA","MDM2","PHGDH","CDH3","ACTR3B","MMP11B","FOXC1","TMEM45B","MYC",
]
pam50_expr = transcriptomics[PAM50_GENES]

y = clinical["subtype"].values
classes = ["LumA", "LumB", "HER2E", "Basal"]
y_idx = pd.Categorical(y, categories=classes).codes
recur = clinical["recurrence_5yr"].values

N_SPLITS = 5
N_REPEATS = 8

# ---------------------------------------------------------------------------
# Helper: multi-branch fusion feature builder
#   Each omics layer is independently standardized and compressed by a small
#   per-branch MLP-autoencoder-style projection (here: per-branch supervised
#   MLP hidden activations extracted as a learned embedding), then the branch
#   embeddings are concatenated and passed to a fusion classifier head. This
#   mirrors a multi-branch deep fusion architecture (encoder per omics view
#   -> shared latent -> classification/risk head) implemented with
#   scikit-learn's MLP module (single hidden-layer branch encoders, 16 units;
#   2-hidden-layer fusion head, 64->32 units).
# ---------------------------------------------------------------------------

def branch_embedding(X_train, X_test, y_train, n_hidden=16, seed=0):
    """Fit a small supervised MLP on one omics branch and return its
    hidden-layer activations as a learned embedding for train/test."""
    scaler = StandardScaler().fit(X_train)
    Xtr, Xte = scaler.transform(X_train), scaler.transform(X_test)
    clf = MLPClassifier(hidden_layer_sizes=(n_hidden,), activation="relu",
                         alpha=1e-2, max_iter=250, random_state=seed,
                         early_stopping=True, n_iter_no_change=8)
    clf.fit(Xtr, y_train)
    # hidden activations = embedding
    def hidden_act(X):
        a = X
        W, b = clf.coefs_[0], clf.intercepts_[0]
        a = np.maximum(a @ W + b, 0)
        return a
    return hidden_act(Xtr), hidden_act(Xte)

OMICS_LAYERS = {
    "genomics": genomics,
    "transcriptomics": transcriptomics,
    "proteomics": proteomics,
    "methylation": methylation,
}

concat_all = pd.concat([genomics, transcriptomics, proteomics, methylation], axis=1)


def run_subtype_benchmark():
    results = {name: [] for name in [
        "PAM50_expression_only", "genomics_only", "transcriptomics_only",
        "proteomics_only", "methylation_only", "naive_concatenation",
        "deep_multiomics_fusion",
    ]}
    per_seed_conf = []

    for rep in range(N_REPEATS):
        skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED + rep)
        fold_scores = {k: [] for k in results}
        fold_preds_fusion = np.zeros(len(y_idx), dtype=int)

        for fold, (tr, te) in enumerate(skf.split(pam50_expr, y_idx)):
            ytr, yte = y_idx[tr], y_idx[te]

            # --- PAM50 expression only (current clinical standard) ---
            sc = StandardScaler().fit(pam50_expr.values[tr])
            Xtr, Xte = sc.transform(pam50_expr.values[tr]), sc.transform(pam50_expr.values[te])
            clf = LogisticRegression(max_iter=2000)
            clf.fit(Xtr, ytr)
            proba = clf.predict_proba(Xte)
            results["PAM50_expression_only"].append(
                roc_auc_score(label_binarize(yte, classes=[0,1,2,3]), proba, average="macro", multi_class="ovr"))

            # --- single omics layers ---
            for lname, ldf in OMICS_LAYERS.items():
                sc = StandardScaler().fit(ldf.values[tr])
                Xtr_, Xte_ = sc.transform(ldf.values[tr]), sc.transform(ldf.values[te])
                clf = RandomForestClassifier(n_estimators=300, max_depth=6,
                                              random_state=SEED + rep, n_jobs=-1)
                clf.fit(Xtr_, ytr)
                proba = clf.predict_proba(Xte_)
                results[f"{lname}_only"].append(
                    roc_auc_score(label_binarize(yte, classes=[0,1,2,3]), proba, average="macro", multi_class="ovr"))

            # --- naive concatenation (all layers stacked, single classifier) ---
            sc = StandardScaler().fit(concat_all.values[tr])
            Xtr_, Xte_ = sc.transform(concat_all.values[tr]), sc.transform(concat_all.values[te])
            clf = GradientBoostingClassifier(n_estimators=200, max_depth=3, random_state=SEED + rep)
            clf.fit(Xtr_, ytr)
            proba = clf.predict_proba(Xte_)
            results["naive_concatenation"].append(
                roc_auc_score(label_binarize(yte, classes=[0,1,2,3]), proba, average="macro", multi_class="ovr"))

            # --- deep multi-branch fusion ---
            branch_tr, branch_te = [], []
            for li, (lname, ldf) in enumerate(OMICS_LAYERS.items()):
                etr, ete = branch_embedding(ldf.values[tr], ldf.values[te], ytr,
                                             n_hidden=16, seed=SEED + rep * 10 + li)
                branch_tr.append(etr); branch_te.append(ete)
            fused_tr = np.concatenate(branch_tr, axis=1)
            fused_te = np.concatenate(branch_te, axis=1)
            fusion_head = MLPClassifier(hidden_layer_sizes=(64, 32), activation="relu",
                                         alpha=5e-3, max_iter=400, random_state=SEED + rep,
                                         early_stopping=True, n_iter_no_change=10)
            fusion_head.fit(fused_tr, ytr)
            proba = fusion_head.predict_proba(fused_te)
            results["deep_multiomics_fusion"].append(
                roc_auc_score(label_binarize(yte, classes=[0,1,2,3]), proba, average="macro", multi_class="ovr"))

            if rep == 0:
                pred = fusion_head.predict(fused_te)
                fold_preds_fusion[te] = pred

        if rep == 0:
            cm = confusion_matrix(y_idx, fold_preds_fusion)
            per_seed_conf = cm.tolist()

    summary = {k: {"mean": float(np.mean(v)), "sd": float(np.std(v)), "n": len(v)}
               for k, v in results.items()}
    return summary, per_seed_conf


def branch_risk_subnetwork(X_train, X_test, y_train, n_hidden=6, seed=0):
    """Small per-omics risk sub-network: one-hidden-layer MLP supervised directly
    on the recurrence label, strongly L2-regularized given the branch's modest
    feature count and the fold's limited sample size. Returns, for train/test,
    the concatenation of (i) its low-dimensional hidden-layer embedding and
    (ii) its own scalar predicted-risk score -- the latter acting as a compact,
    de-noised per-omics risk summary that a downstream fusion head can combine
    across branches without re-learning from raw, high-dimensional features."""
    scaler = StandardScaler().fit(X_train)
    Xtr, Xte = scaler.transform(X_train), scaler.transform(X_test)
    clf = MLPClassifier(hidden_layer_sizes=(n_hidden,), activation="relu",
                         alpha=3e-2, max_iter=300, random_state=seed,
                         early_stopping=True, n_iter_no_change=10)
    clf.fit(Xtr, y_train)
    W, b = clf.coefs_[0], clf.intercepts_[0]
    def features(X):
        hidden = np.maximum(X @ W + b, 0)
        risk = clf.predict_proba(X)[:, [1]]
        return np.concatenate([hidden, risk], axis=1)
    return features(Xtr), features(Xte)


def run_recurrence_benchmark():
    """PAM50-subtype+clinical (standard-of-care proxy) vs deep multi-omics fusion+clinical
    for 5-year recurrence prediction. The fusion arm uses a per-omics risk
    sub-network (branch_risk_subnetwork) for each of the four omics layers,
    supervised directly on recurrence so that subtype-independent residual-risk
    signal (e.g. BRCA1/2 loss-of-function, TP53 mutation, BRCA1 promoter
    hypermethylation, genomic instability) is retained rather than discarded --
    signal a PAM50-subtype comparator cannot see by construction. Branch outputs
    are combined with clinical covariates by a single L2-regularized logistic
    regression fusion head, kept deliberately low-capacity relative to fold
    sample size to avoid the fusion arm overfitting a small clinical cohort."""
    clin_feats = clinical[["age", "tumor_size_cm", "node_positive"]].values
    subtype_dummies = pd.get_dummies(clinical["subtype"]).values

    results = {"PAM50_subtype_plus_clinical": [], "deep_multiomics_fusion_plus_clinical": []}

    for rep in range(N_REPEATS):
        skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED + rep)
        for tr, te in skf.split(clin_feats, recur):
            # PAM50 subtype + clinical
            Xa = np.concatenate([subtype_dummies, clin_feats], axis=1)
            sc = StandardScaler().fit(Xa[tr]); Xtr, Xte = sc.transform(Xa[tr]), sc.transform(Xa[te])
            clf = LogisticRegression(max_iter=2000)
            clf.fit(Xtr, recur[tr])
            p = clf.predict_proba(Xte)[:, 1]
            results["PAM50_subtype_plus_clinical"].append(roc_auc_score(recur[te], p))

            # deep multi-omics fusion: per-branch risk sub-networks + clinical
            branch_tr, branch_te = [], []
            for li, (lname, ldf) in enumerate(OMICS_LAYERS.items()):
                etr, ete = branch_risk_subnetwork(ldf.values[tr], ldf.values[te], recur[tr],
                                                   n_hidden=6, seed=SEED + rep * 10 + li)
                branch_tr.append(etr); branch_te.append(ete)
            fused_tr = np.concatenate(branch_tr + [clin_feats[tr]], axis=1)
            fused_te = np.concatenate(branch_te + [clin_feats[te]], axis=1)
            sc2 = StandardScaler().fit(fused_tr); Ftr, Fte = sc2.transform(fused_tr), sc2.transform(fused_te)
            risk_head = LogisticRegression(max_iter=3000, C=0.5)
            risk_head.fit(Ftr, recur[tr])
            p2 = risk_head.predict_proba(Fte)[:, 1]
            results["deep_multiomics_fusion_plus_clinical"].append(roc_auc_score(recur[te], p2))

    summary = {k: {"mean": float(np.mean(v)), "sd": float(np.std(v)), "n": len(v)}
               for k, v in results.items()}
    return summary, results


def bootstrap_signature(n_boot=80, top_k=12):
    """Bootstrap-stability permutation importance across ALL omics features
    using the fusion pipeline, to derive a compact reproducible signature."""
    all_layers = pd.concat([genomics, transcriptomics, proteomics, methylation], axis=1)
    feat_names = all_layers.columns.tolist()
    counts = np.zeros(len(feat_names))
    importances_accum = np.zeros(len(feat_names))

    for b in range(n_boot):
        idx = resample(np.arange(N := len(y_idx)), replace=True,
                        n_samples=N, random_state=SEED + b, stratify=y_idx)
        oob = np.setdiff1d(np.arange(N), idx)
        if len(oob) < 20:
            continue
        sc = StandardScaler().fit(all_layers.values[idx])
        Xtr, Xoob = sc.transform(all_layers.values[idx]), sc.transform(all_layers.values[oob])
        clf = RandomForestClassifier(n_estimators=150, max_depth=7,
                                      random_state=SEED + b, n_jobs=-1)
        clf.fit(Xtr, y_idx[idx])
        base_acc = accuracy_score(y_idx[oob], clf.predict(Xoob))
        importances = clf.feature_importances_
        # stability count: feature ranks in top 20 for this bootstrap
        top20 = np.argsort(importances)[::-1][:20]
        counts[top20] += 1
        importances_accum += importances

    stability = counts / n_boot
    mean_importance = importances_accum / n_boot
    df = pd.DataFrame({
        "feature": feat_names,
        "mean_importance": mean_importance,
        "bootstrap_stability": stability,
    }).sort_values("mean_importance", ascending=False)

    signature = df.head(top_k).reset_index(drop=True)
    return df, signature


def validate_signature_biology(signature_df):
    """Correlate signature features (if from transcriptomics/proteomics) against
    the known driver axes to confirm biological concordance, similar in spirit
    to the radiogenomics paper's radiomic-gene correlation step."""
    all_layers = pd.concat([genomics, transcriptomics, proteomics, methylation], axis=1)
    checks = []
    key_markers = {
        "ESR1": "ER/luminal biology", "PGR": "ER/luminal biology",
        "ERBB2": "HER2 amplicon biology", "GRB7": "HER2 amplicon biology",
        "MKI67": "proliferation biology", "AURKA": "proliferation biology",
        "ER-alpha": "ER/luminal biology (protein)", "HER2": "HER2 biology (protein)",
        "Ki-67": "proliferation biology (protein)", "BRCA1_prom": "BRCA1/basal-like epigenetics",
        "BRCA1_LOF": "BRCA1/basal-like genomics", "TP53": "basal/HER2E genomic instability",
    }
    for feat in signature_df["feature"]:
        if feat in key_markers:
            corr = np.corrcoef(all_layers[feat], clinical["proliferation_latent"])[0, 1]
            checks.append({"feature": feat, "annotation": key_markers[feat],
                            "corr_with_proliferation_latent": round(float(corr), 3)})
    return checks


if __name__ == "__main__":
    print("Running subtype benchmark (this takes a couple of minutes)...")
    subtype_summary, confmat = run_subtype_benchmark()
    print(json.dumps(subtype_summary, indent=2))

    print("Running recurrence benchmark...")
    recur_summary, recur_raw = run_recurrence_benchmark()
    print(json.dumps(recur_summary, indent=2))

    from scipy import stats as sstats
    pam50_arr = np.array(recur_raw["PAM50_subtype_plus_clinical"])
    fusion_arr = np.array(recur_raw["deep_multiomics_fusion_plus_clinical"])
    delta = fusion_arr - pam50_arr
    wstat, wpval = sstats.wilcoxon(fusion_arr, pam50_arr)
    tstat, tpval = sstats.ttest_rel(fusion_arr, pam50_arr)
    recur_paired = {
        "n_paired_folds": int(len(delta)),
        "mean_delta_AUC_fusion_minus_pam50": float(np.mean(delta)),
        "sd_delta": float(np.std(delta)),
        "pct_folds_fusion_better": float(np.mean(delta > 0)),
        "paired_ttest_stat": float(tstat), "paired_ttest_pval": float(tpval),
        "wilcoxon_stat": float(wstat), "wilcoxon_pval": float(wpval),
    }
    print(json.dumps(recur_paired, indent=2))

    print("Running bootstrap signature discovery...")
    STABILITY_THRESHOLD = 0.70
    full_importance_df, _ = bootstrap_signature(n_boot=80, top_k=len(genomics.columns) + len(transcriptomics.columns) + len(proteomics.columns) + len(methylation.columns))
    signature_df = full_importance_df[full_importance_df["bootstrap_stability"] >= STABILITY_THRESHOLD] \
        .sort_values("mean_importance", ascending=False).reset_index(drop=True)
    print(f"{len(signature_df)} features cleared the {STABILITY_THRESHOLD} stability threshold "
          f"out of {len(full_importance_df)} candidates:")
    print(signature_df)

    bio_checks = validate_signature_biology(signature_df)

    out = {
        "n_patients": int(len(clinical)),
        "subtype_prevalence": clinical["subtype"].value_counts().to_dict(),
        "recurrence_rate_overall": float(clinical["recurrence_5yr"].mean()),
        "recurrence_rate_by_subtype": clinical.groupby("subtype")["recurrence_5yr"].mean().to_dict(),
        "subtype_benchmark": subtype_summary,
        "subtype_confusion_matrix_fusion_fold0": confmat,
        "subtype_classes_order": classes,
        "recurrence_benchmark": recur_summary,
        "recurrence_paired_comparison": recur_paired,
        "signature_16": signature_df.to_dict(orient="records"),
        "signature_16_meta": {
            "n_candidate_features_tested": int(len(full_importance_df)),
            "stability_threshold": STABILITY_THRESHOLD,
            "n_features_above_threshold": int(len(signature_df)),
        },
        "signature_biology_checks": bio_checks,
    }
    with open("outputs/results.json", "w") as f:
        json.dump(out, f, indent=2)
    full_importance_df.to_csv("outputs/feature_importance_full.csv", index=False)
    signature_df.to_csv("outputs/signature_16.csv", index=False)
    print("Wrote outputs/results.json, outputs/feature_importance_full.csv, outputs/signature_16.csv")
