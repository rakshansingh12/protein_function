"""
Step 4 of the pipeline: train several models, compare them fairly, and save
whichever one actually performs best.

The guiding rule of this script: NOTHING IS ASSUMED. The original project used
Random Forest by default. Here, four algorithms plus several ensembles compete
on measured cross-validation performance, and the winner is whatever the numbers
say it is.

Three design decisions worth understanding, because they are the ones an
examiner is most likely to probe.

1. LEAKAGE CONTROL
   Every model lives inside a scikit-learn Pipeline whose first step is a
   StandardScaler. When cross_validate splits the training data, the scaler is
   refitted on each fold's training portion only. If we had scaled the whole
   dataset up front, every fold's validation set would have contributed to the
   mean and standard deviation used to transform it, quietly inflating scores.
   The test set is not touched until the final evaluation at the end.

2. SELECT ON CROSS-VALIDATION, REPORT ON TEST
   The winner is chosen using cross-validation scores computed on the training
   set. The held-out test set is scored once, afterwards, for every model. If we
   had picked the winner by test score, we would have fitted our choice to the
   test set and the headline number would be optimistic.

3. THE SIZE BASELINE
   Class means showed enzymes averaging ~64 kDa against ~52 kDa for
   non-enzymes. That raises a fair objection: maybe the classifier is just a
   size detector. So we first train a deliberately minimal model on molecular
   weight and sequence length ALONE. If the 29-feature models clearly beat it,
   the remaining 27 features are doing real work. If they barely beat it, that
   is an honest finding and it gets reported.

Run:  python training/train.py
      python training/train.py --learning-curve   (adds a data-sufficiency check)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedGroupKFold,
    StratifiedKFold,
    cross_validate,
    learning_curve,
    train_test_split,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

sys.path.insert(0, str(config.PROJECT_ROOT / "backend"))
from app.ml.feature_engineering import (  # noqa: E402
    COMPARISON_PROPERTIES,
    FEATURE_NAMES,
)

# Fraction of data held out and never seen during training or model selection.
TEST_SIZE = 0.2

# Metrics collected for every model, in report order.
SCORING = {
    "accuracy": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "roc_auc": "roc_auc",
}

# Selection priority. ROC-AUC first because it measures ranking quality across
# all thresholds rather than performance at the arbitrary 0.5 cutoff, and it is
# insensitive to class balance. F1 second because it forces precision and recall
# to both be respectable.
SELECTION_ORDER = ["roc_auc", "f1", "recall", "accuracy"]

# If two models' ROC-AUC differ by less than this, treat them as tied and prefer
# the simpler one. 0.005 is roughly the noise floor across CV folds at this
# dataset size.
TIE_THRESHOLD = 0.005

# An ensemble must beat the best individual model by more than this to be
# adopted. Without a margin we would sometimes pick an ensemble on pure fold
# noise, and then have to defend a more complex model that is not actually
# better.
ENSEMBLE_MIN_GAIN = 0.002

# Complexity ranking used only to break near-ties. Lower is simpler.
COMPLEXITY = {
    "Logistic Regression": 1,
    "Random Forest": 2,
    "Extra Trees": 2,
    "Neural Network (MLP)": 3,
}


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------
def build_candidates(seed):
    """
    Return {display_name: (pipeline, param_grid)}.

    Every model is wrapped in a Pipeline with a StandardScaler. Logistic
    Regression and the MLP genuinely need scaling (both are sensitive to feature
    magnitude, and our features range from ~0.05 amino acid fractions to ~64000
    Dalton molecular weights). Tree models do not need it, but including the
    scaler for them too keeps all four pipelines structurally identical, which
    makes the comparison easier to reason about and costs nothing.

    Grids are deliberately tiny. A huge search would take hours and would not
    change the conclusion; the point of this project is the comparison, not
    squeezing out a final decimal place.
    """
    candidates = {}

    # --- Linear baseline ---------------------------------------------------
    candidates["Logistic Regression"] = (
        Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000, random_state=seed)),
        ]),
        {"model__C": [0.1, 1.0, 10.0]},
    )

    # --- Random Forest -----------------------------------------------------
    candidates["Random Forest"] = (
        Pipeline([
            ("scaler", StandardScaler()),
            ("model", RandomForestClassifier(
                n_estimators=300, random_state=seed,
                class_weight="balanced", n_jobs=-1,
            )),
        ]),
        {
            "model__n_estimators": [200, 300],
            "model__max_depth": [None, 20],
            "model__min_samples_split": [2, 5],
        },
    )

    # --- Extra Trees -------------------------------------------------------
    # Not just "another random forest": Extra Trees picks split thresholds at
    # random rather than searching for the best one. That adds bias but cuts
    # variance, and on noisy features it sometimes wins outright. It is treated
    # as an independent candidate.
    candidates["Extra Trees"] = (
        Pipeline([
            ("scaler", StandardScaler()),
            ("model", ExtraTreesClassifier(
                n_estimators=300, random_state=seed,
                class_weight="balanced", n_jobs=-1,
            )),
        ]),
        {
            "model__n_estimators": [200, 300],
            "model__max_depth": [None, 20],
            "model__min_samples_split": [2, 5],
        },
    )

    # --- Neural network ----------------------------------------------------
    # (64, 32) is ~4,000 parameters against ~7,500 training samples. That is
    # thin, so the grid includes a smaller (32, 16) network. If the dataset is
    # too small for the larger architecture, cross-validation will say so by
    # preferring the smaller one. early_stopping and the L2 alpha term both
    # reduce effective capacity further.
    candidates["Neural Network (MLP)"] = (
        Pipeline([
            ("scaler", StandardScaler()),
            ("model", MLPClassifier(
                hidden_layer_sizes=(64, 32), activation="relu", solver="adam",
                max_iter=500, random_state=seed, early_stopping=True,
            )),
        ]),
        {
            "model__hidden_layer_sizes": [(32, 16), (64, 32)],
            "model__alpha": [1e-4, 1e-3],
        },
    )

    return candidates


def build_size_baseline(seed):
    """
    The deliberately dumb control: logistic regression on molecular weight and
    sequence length only.

    This exists to answer one specific question an examiner will ask given the
    12 kDa class gap: "is your model just detecting protein size?" The gap
    between this baseline and the full models is the honest measure of what the
    other 27 features contribute.
    """
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=2000, random_state=seed)),
    ])


def load_cluster_groups(df):
    """
    Return an array giving each protein's sequence-cluster id, aligned with df,
    or None if clustering has not been run.

    Proteins in the same cluster share at least config.CLUSTER_MIN_SEQ_ID
    sequence identity. They are treated as one family for splitting purposes.
    """
    if not config.CLUSTERS_CSV.exists():
        return None

    clusters = pd.read_csv(config.CLUSTERS_CSV)
    mapping = dict(zip(clusters["accession"], clusters["cluster_id"]))
    groups = df["accession"].map(mapping)

    missing = int(groups.isna().sum())
    if missing:
        # A protein absent from the cluster file gets its own singleton group,
        # which is the safe choice: it can never be split away from itself.
        print(f"  ! {missing} proteins missing from clusters.csv; "
              f"treating each as its own cluster.")
        groups = groups.fillna(df["accession"])

    return groups.astype(str).values


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------
def cross_validate_model(model, X_train, y_train, cv):
    """Mean cross-validated score for each metric in SCORING."""
    results = cross_validate(
        model, X_train, y_train, cv=cv, scoring=SCORING, n_jobs=-1
    )
    return {name: float(results[f"test_{name}"].mean()) for name in SCORING}


def evaluate_on_test(model, X_test, y_test):
    """
    Fit-free evaluation on the held-out test set.

    The model must already be fitted on the full training set. Called once per
    model, after selection is complete.
    """
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    return {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
    }


def print_comparison_table(rows, title):
    """Print the model comparison table."""
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)
    header = (
        f"{'Model':<32}{'Accuracy':>10}{'Precision':>11}"
        f"{'Recall':>9}{'F1':>9}{'ROC-AUC':>10}"
    )
    print(header)
    print("-" * 88)
    for name, scores in rows:
        print(
            f"{name:<32}{scores['accuracy']:>10.4f}{scores['precision']:>11.4f}"
            f"{scores['recall']:>9.4f}{scores['f1']:>9.4f}{scores['roc_auc']:>10.4f}"
        )
    print("-" * 88)


def select_best(cv_scores):
    """
    Pick the winner from cross-validation scores.

    Sorts by SELECTION_ORDER (ROC-AUC, then F1, then recall, then accuracy).
    Then applies the tie-break: if any simpler model is within TIE_THRESHOLD of
    the top ROC-AUC, that simpler model wins instead. A 0.001 ROC-AUC advantage
    is not worth a harder-to-explain model.
    """
    ranked = sorted(
        cv_scores.items(),
        key=lambda item: tuple(-item[1][m] for m in SELECTION_ORDER),
    )
    best_name, best_scores = ranked[0]

    for name, scores in ranked[1:]:
        close_enough = best_scores["roc_auc"] - scores["roc_auc"] <= TIE_THRESHOLD
        simpler = COMPLEXITY.get(name, 99) < COMPLEXITY.get(best_name, 99)
        if close_enough and simpler:
            print(
                f"\n  Tie-break: {name} is within {TIE_THRESHOLD} ROC-AUC of "
                f"{best_name}\n  and is simpler, so it is preferred."
            )
            best_name, best_scores = name, scores

    return best_name, best_scores


def run_learning_curve(model, X_train, y_train, cv):
    """
    Does more data help?

    Trains on increasing fractions of the training set and reports CV ROC-AUC.
    If the curve has flattened by the full dataset, collecting more proteins
    would not improve results, and we can say so with evidence rather than
    opinion. If it is still climbing, more data would help.
    """
    print("\n" + "=" * 88)
    print("LEARNING CURVE — is the dataset large enough?")
    print("=" * 88)

    fractions = np.array([0.1, 0.25, 0.5, 0.75, 1.0])
    sizes, train_scores, val_scores = learning_curve(
        model, X_train, y_train, cv=cv, scoring="roc_auc",
        train_sizes=fractions, n_jobs=-1,
    )

    print(f"{'Train size':>12}{'Train ROC-AUC':>16}{'CV ROC-AUC':>14}")
    print("-" * 42)
    for size, train_row, val_row in zip(sizes, train_scores, val_scores):
        print(f"{int(size):>12}{train_row.mean():>16.4f}{val_row.mean():>14.4f}")

    gain = val_scores[-1].mean() - val_scores[-2].mean()
    print("-" * 42)
    print(f"Gain over the final 25% of data: {gain:+.4f}")
    if abs(gain) < 0.005:
        print("The curve has flattened: more data is unlikely to help much.")
    else:
        print("The curve is still rising: more data would probably help.")

    return {
        "train_sizes": [int(s) for s in sizes],
        "cv_roc_auc": [float(v.mean()) for v in val_scores],
        "final_gain": float(gain),
    }


def compute_class_stats(df_train):
    """
    Precompute per-class mean and standard deviation for the dashboard.

    Computed on the TRAINING split only. The test set stays untouched, and the
    dashboard shown to users reflects only data the model was allowed to see.
    """
    stats = {}
    for label_value, label_name in config.LABEL_NAMES.items():
        subset = df_train[df_train["label"] == label_value]
        stats[label_name] = {
            prop: {
                "mean": float(subset[prop].mean()),
                "std": float(subset[prop].std()),
            }
            for prop in COMPARISON_PROPERTIES
        }
        stats[label_name]["count"] = int(len(subset))
    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Train and compare models.")
    parser.add_argument(
        "--learning-curve", action="store_true",
        help="Also run a learning curve on the selected model (slower).",
    )
    args = parser.parse_args()

    if not config.FEATURES_CSV.exists():
        print(f"Features not found: {config.FEATURES_CSV}")
        print("Run: python training/feature_engineering.py")
        sys.exit(1)

    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    seed = config.RANDOM_SEED

    df = pd.read_csv(config.FEATURES_CSV)
    X = df[FEATURE_NAMES].values
    y = df["label"].values

    print("=" * 88)
    print("MODEL TRAINING AND COMPARISON")
    print("=" * 88)
    print(f"Samples          : {len(df)}")
    print(f"Features         : {len(FEATURE_NAMES)}")
    print(f"Class balance    : {dict(pd.Series(y).value_counts())}")

    # --- Split ---------------------------------------------------------
    # Two modes.
    #
    # HOMOLOGY-AWARE (used when data/processed/clusters.csv exists):
    #   Proteins are grouped into families by sequence identity (MMseqs2,
    #   see cluster_sequences.py). Whole families go to either train or test,
    #   never both. Without this, a kinase in the training set and its 80%
    #   identical paralog in the test set would let the model "recognise the
    #   family" instead of learning general enzyme properties, inflating the
    #   test score. The same grouping is applied inside cross-validation.
    #
    # RANDOM (fallback when no cluster file exists):
    #   Plain stratified split. Only exact duplicates were removed upstream,
    #   so homologs can straddle the split and scores are optimistic.
    groups = load_cluster_groups(df)

    if groups is not None:
        split_mode = "homology_aware"
        # Take one of five stratified group folds as the ~20% test set.
        outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        idx_train, idx_test = next(outer.split(X, y, groups))
        X_train, X_test = X[idx_train], X[idx_test]
        y_train, y_test = y[idx_train], y[idx_test]
        groups_train = groups[idx_train]

        # Precompute the CV folds as a list of (train, validation) index pairs.
        # scikit-learn accepts such a list anywhere it accepts cv=..., so
        # GridSearchCV, cross_validate and learning_curve all respect the
        # family grouping without any further changes.
        inner = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        cv = list(inner.split(X_train, y_train, groups_train))

        shared = set(groups[idx_train]) & set(groups[idx_test])
        print(f"Split mode       : HOMOLOGY-AWARE "
              f"({len(set(groups))} sequence clusters)")
        print(f"Clusters shared between train and test: {len(shared)}")
        print(f"Cross-validation : StratifiedGroupKFold(n_splits=5)")
    else:
        split_mode = "random"
        X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
            X, y, np.arange(len(df)),
            test_size=TEST_SIZE, stratify=y, random_state=seed,
        )
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        print("Split mode       : RANDOM (no clusters.csv found)")
        print("  ! Homologous proteins may appear in both train and test, so")
        print("  ! scores are likely optimistic. Run cluster_sequences.py first.")
        print(f"Cross-validation : StratifiedKFold(n_splits=5, shuffle=True)")

    print(f"Train / Test     : {len(X_train)} / {len(X_test)}")

    cv_scores = {}
    fitted_models = {}

    # --- Size baseline first ----------------------------------------------
    print("\n" + "-" * 88)
    print("SIZE BASELINE (molecular weight + sequence length only)")
    print("-" * 88)
    size_indices = [
        FEATURE_NAMES.index("molecular_weight"),
        FEATURE_NAMES.index("sequence_length"),
    ]
    baseline = build_size_baseline(seed)
    baseline_cv = cross_validate_model(
        baseline, X_train[:, size_indices], y_train, cv
    )
    baseline.fit(X_train[:, size_indices], y_train)
    baseline_test = evaluate_on_test(baseline, X_test[:, size_indices], y_test)
    print(f"  CV ROC-AUC   : {baseline_cv['roc_auc']:.4f}")
    print(f"  Test ROC-AUC : {baseline_test['roc_auc']:.4f}")
    print("  This is the number the 29-feature models must clearly beat.")

    # --- Tune and cross-validate each candidate ---------------------------
    candidates = build_candidates(seed)
    best_params = {}

    for name, (pipeline, grid) in candidates.items():
        print("\n" + "-" * 88)
        print(f"{name}  —  tuning {len(grid)} hyperparameter(s)")
        print("-" * 88)

        # Tune on ROC-AUC, the primary selection metric.
        search = GridSearchCV(
            pipeline, grid, scoring="roc_auc", cv=cv, n_jobs=-1
        )
        search.fit(X_train, y_train)
        tuned = search.best_estimator_
        best_params[name] = {k: str(v) for k, v in search.best_params_.items()}
        print(f"  Best params  : {search.best_params_}")

        # Re-score the tuned model across all five metrics.
        cv_scores[name] = cross_validate_model(tuned, X_train, y_train, cv)
        fitted_models[name] = tuned
        print(f"  CV ROC-AUC   : {cv_scores[name]['roc_auc']:.4f}  "
              f"F1: {cv_scores[name]['f1']:.4f}")

    print_comparison_table(
        list(cv_scores.items()), "CROSS-VALIDATION RESULTS (training set)"
    )

    best_individual, best_individual_scores = select_best(cv_scores)
    print(f"\nBest individual model: {best_individual} "
          f"(CV ROC-AUC {best_individual_scores['roc_auc']:.4f})")

    # --- Ensemble experiments ---------------------------------------------
    # We do not simply throw all four models into one ensemble. We test several
    # sensible combinations and adopt one only if it measurably wins.
    print("\n" + "=" * 88)
    print("ENSEMBLE EXPERIMENTS")
    print("=" * 88)

    combinations = {
        "Ensemble (RF + ET)": ["Random Forest", "Extra Trees"],
        "Ensemble (ET + MLP)": ["Extra Trees", "Neural Network (MLP)"],
        "Ensemble (RF + MLP)": ["Random Forest", "Neural Network (MLP)"],
        "Ensemble (RF + ET + MLP)": [
            "Random Forest", "Extra Trees", "Neural Network (MLP)",
        ],
        "Ensemble (all four)": list(candidates.keys()),
    }

    ensemble_scores = {}
    for ensemble_name, members in combinations.items():
        # Soft voting averages predicted probabilities, so it needs models that
        # produce calibrated-ish probabilities. All four do.
        voting = VotingClassifier(
            estimators=[(m, fitted_models[m]) for m in members],
            voting="soft", n_jobs=-1,
        )
        scores = cross_validate_model(voting, X_train, y_train, cv)
        ensemble_scores[ensemble_name] = scores
        fitted_models[ensemble_name] = voting
        print(f"  {ensemble_name:<30} CV ROC-AUC {scores['roc_auc']:.4f}  "
              f"F1 {scores['f1']:.4f}")

    print_comparison_table(
        list(ensemble_scores.items()), "ENSEMBLE CROSS-VALIDATION RESULTS"
    )

    # --- Final decision ----------------------------------------------------
    best_ensemble, best_ensemble_scores = select_best(ensemble_scores)
    gain = best_ensemble_scores["roc_auc"] - best_individual_scores["roc_auc"]

    print("\n" + "=" * 88)
    print("FINAL MODEL SELECTION")
    print("=" * 88)
    print(f"Primary metric        : ROC-AUC (secondary: F1)")
    print(f"Best individual       : {best_individual}  "
          f"({best_individual_scores['roc_auc']:.4f})")
    print(f"Best ensemble         : {best_ensemble}  "
          f"({best_ensemble_scores['roc_auc']:.4f})")
    print(f"Ensemble gain         : {gain:+.4f}  "
          f"(must exceed {ENSEMBLE_MIN_GAIN} to be adopted)")

    if gain > ENSEMBLE_MIN_GAIN:
        final_name = best_ensemble
        ensemble_selected = True
        ensemble_members = combinations[best_ensemble]
        print(f"\nDecision: ADOPT ENSEMBLE — it improves ROC-AUC by {gain:.4f}.")
    else:
        final_name = best_individual
        ensemble_selected = False
        ensemble_members = None
        print(f"\nDecision: KEEP INDIVIDUAL MODEL — the ensemble does not "
              f"improve\nperformance by a meaningful margin, so the simpler "
              f"model is used.")

    final_model = fitted_models[final_name]

    # --- Test set: touched once, now -------------------------------------
    # cross_validate clones its estimator internally, so the VotingClassifiers
    # were scored but never actually fitted. GridSearchCV does refit its winner,
    # which is why only the ensembles were affected. Fit everything explicitly
    # on the full training set before scoring the test set.
    all_cv = {**cv_scores, **ensemble_scores}
    for model in fitted_models.values():
        model.fit(X_train, y_train)

    test_scores = {
        name: evaluate_on_test(model, X_test, y_test)
        for name, model in fitted_models.items()
    }
    final_model = fitted_models[final_name]

    print_comparison_table(
        [(n, test_scores[n]) for n in all_cv],
        "HELD-OUT TEST SET RESULTS (evaluated once, after selection)",
    )

    final_test = test_scores[final_name]
    tn, fp, fn, tp = np.array(final_test["confusion_matrix"]).ravel()
    print(f"\nFinal model: {final_name}")
    print(f"  Test ROC-AUC : {final_test['roc_auc']:.4f}")
    print(f"  Test F1      : {final_test['f1']:.4f}")
    print(f"\n  Confusion matrix")
    print(f"                    predicted non-enzyme   predicted enzyme")
    print(f"    non-enzyme  {tn:>18}{fp:>19}")
    print(f"    enzyme      {fn:>18}{tp:>19}")

    # --- The question that matters: is it just size? ----------------------
    lift = final_test["roc_auc"] - baseline_test["roc_auc"]
    print("\n" + "=" * 88)
    print("IS THE MODEL JUST DETECTING PROTEIN SIZE?")
    print("=" * 88)
    print(f"  Size-only baseline (MW + length) : {baseline_test['roc_auc']:.4f}")
    print(f"  Full 29-feature model            : {final_test['roc_auc']:.4f}")
    print(f"  Lift from the other 27 features  : {lift:+.4f}")
    if lift < 0.03:
        print("\n  Interpretation: the lift is small. Most of the signal comes")
        print("  from protein size. Report this honestly as a limitation.")
    else:
        print("\n  Interpretation: the remaining 27 features contribute")
        print("  substantially. The model is not merely a size detector.")

    curve_results = None
    if args.learning_curve:
        curve_results = run_learning_curve(final_model, X_train, y_train, cv)

    # --- Artefacts ---------------------------------------------------------
    # A standalone scaler fitted on the training set. The models already carry
    # their own scaler inside their pipelines; this separate one exists purely
    # so the similar-protein search computes Euclidean distances in the same
    # standardised space the classifier reasons in. Without it, molecular
    # weight (~64000) would completely dominate amino acid fractions (~0.05).
    scaler = StandardScaler().fit(X_train)

    joblib.dump(final_model, config.MODELS_DIR / "final_model.joblib")
    joblib.dump(scaler, config.MODELS_DIR / "scaler.joblib")
    joblib.dump(
        {
            "accessions": df.iloc[idx_train]["accession"].tolist(),
            "labels": y_train.tolist(),
            "features_scaled": scaler.transform(X_train),
            "feature_names": FEATURE_NAMES,
        },
        config.MODELS_DIR / "training_features.joblib",
    )

    df_train = df.iloc[idx_train]

    # Per-protein predictions on the held-out test set. Used downstream by
    # validate_kegg.py to ask whether the model's "false positives" are really
    # errors, or under-annotated enzymes that the labels missed.
    test_df = df.iloc[idx_test][["accession", "label", "evidence_class"]].copy()
    test_df["predicted_label"] = final_model.predict(X_test)
    test_df["enzyme_probability"] = final_model.predict_proba(X_test)[:, 1]
    test_df.to_csv(config.TEST_PREDICTIONS_CSV, index=False)
    with open(config.MODELS_DIR / "class_stats.json", "w") as handle:
        json.dump(compute_class_stats(df_train), handle, indent=2)

    model_results = {
        "best_model": final_name,
        "split_mode": split_mode,
        "selection_metric": "roc_auc",
        "secondary_metric": "f1",
        "selection_rule": (
            "Ranked by cross-validated ROC-AUC, then F1, recall, accuracy. "
            "A simpler model within "
            f"{TIE_THRESHOLD} ROC-AUC of the leader is preferred. An ensemble "
            f"is adopted only if it exceeds the best individual model by more "
            f"than {ENSEMBLE_MIN_GAIN} ROC-AUC."
        ),
        "ensemble_selected": ensemble_selected,
        "ensemble_composition": ensemble_members,
        "ensemble_gain": float(gain),
        "size_baseline": {
            "description": "Logistic regression on molecular weight and sequence length only",
            "cv": baseline_cv,
            "test": baseline_test,
            "lift_of_full_model": float(lift),
        },
        "models": {
            name: {
                "cross_validation": all_cv[name],
                "test": test_scores[name],
                "best_params": best_params.get(name),
            }
            for name in all_cv
        },
    }
    if curve_results:
        model_results["learning_curve"] = curve_results

    with open(config.MODELS_DIR / "model_results.json", "w") as handle:
        json.dump(model_results, handle, indent=2)

    metadata = {
        "feature_names": FEATURE_NAMES,
        "feature_count": len(FEATURE_NAMES),
        "training_dataset_size": int(len(df)),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "class_counts": {
            config.LABEL_NAMES[k]: int(v)
            for k, v in pd.Series(y).value_counts().items()
        },
        "selected_model": final_name,
        "model_type": type(final_model).__name__,
        "ensemble_selected": ensemble_selected,
        "training_date": datetime.now().isoformat(timespec="seconds"),
        "random_seed": seed,
        "split_mode": split_mode,
        "min_sequence_length": config.MIN_SEQUENCE_LENGTH,
        "max_sequence_length": config.MAX_SEQUENCE_LENGTH,
    }
    with open(config.MODELS_DIR / "metadata.json", "w") as handle:
        json.dump(metadata, handle, indent=2)

    print("\n" + "=" * 88)
    print("SAVED ARTEFACTS")
    print("=" * 88)
    for filename in [
        "final_model.joblib", "scaler.joblib", "training_features.joblib",
        "class_stats.json", "model_results.json", "metadata.json",
    ]:
        print(f"  models/{filename}")
    print(f"  {config.TEST_PREDICTIONS_CSV.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()