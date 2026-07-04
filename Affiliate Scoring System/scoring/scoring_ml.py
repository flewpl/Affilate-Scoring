"""
Anomaly / smart-fraud detection layer.

WHY THIS IS DIFFERENT FROM THE ORIGINAL NOTEBOOK:
The original scoring_ml_model.ipynb trained a RandomForestClassifier on
`profile_name == 'Fraud'` as the label, using clicks/reg_rate/ftd_rate/etc.
as features. But `profile_name` itself was generated directly from those
same metric ranges (see generate_data.py: each profile is just a fixed
clicks/reg_rate/ftd_rate band). So the model was really learning
"which numeric band do these features fall into", which is exactly the
same information already encoded in profile_name. That's why F1 came out
at a perfect 1.000 - it's data leakage, not a working fraud model:
in production, you don't get a 'profile_name=Fraud' label handed to you
in advance, that's the thing you're trying to discover.

This module instead does unsupervised anomaly detection with Isolation
Forest, trained separately per traffic-source profile, using *behavioral
ratios* rather than raw labels:
  - ftd_to_reg ratio extremes
  - ngr_per_ftd extremes (near-zero = players not really playing)
  - retention extremes (near-zero = nobody sticks around)
  - reg_rate extremes
This flags affiliates who are statistical outliers *within their own
channel* - which is a more realistic proxy for "this doesn't look like
normal traffic", without assuming we already know the answer.

A supervised option (RandomForest on a true historical label, e.g. an
'investigated_fraud' column you maintain yourself over time) is also
exposed via `train_supervised_model`, for when real investigated labels
exist - but it deliberately excludes profile_name as a feature, and the
UI surfaces a leakage warning if accuracy looks suspiciously perfect.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "clicks",
    "registrations",
    "reg_rate",
    "ftd_rate",
    "ngr_per_ftd",
    "retention_30d",
]


def run_anomaly_detection(df, contamination=0.07):
    """
    Unsupervised outlier detection, fit separately within each profile_name
    group so a high-volume PPC affiliate is never compared directly against
    a low-volume Streamer affiliate.

    Returns the dataframe with two new columns:
      - anomaly_score: higher = more anomalous (easier to read than raw IF output)
      - is_anomaly: bool flag from Isolation Forest's own decision boundary
    """
    df = df.copy()
    df["anomaly_score"] = np.nan
    df["is_anomaly"] = False

    for profile, group in df.groupby("profile_name"):
        if len(group) < 20:
            # Too few samples in this group for a meaningful model
            continue

        X = group[FEATURES].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            random_state=42,
        )
        raw_pred = model.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal
        raw_score = model.decision_function(X_scaled)  # higher = more normal

        # Flip + rescale so higher = more anomalous, roughly 0-1
        normalized = (raw_score.max() - raw_score) / (raw_score.max() - raw_score.min() + 1e-9)

        df.loc[group.index, "anomaly_score"] = normalized
        df.loc[group.index, "is_anomaly"] = raw_pred == -1

    return df


def train_supervised_model(df, label_col):
    """
    Supervised fraud classifier, for use ONLY when label_col contains a
    real, independently-sourced ground truth (e.g. a column you fill in
    after manual investigation) - NOT something derived from the same
    metrics used as features.

    profile_name is intentionally excluded from features to avoid
    reintroducing the original leakage pattern.
    """
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found in dataset.")

    work = df.dropna(subset=[label_col]).copy()
    if work[label_col].nunique() < 2:
        raise ValueError("Label column needs at least two classes (e.g. 0 and 1) to train on.")

    X = work[FEATURES].fillna(0)
    y = work[label_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    clf = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)

    cv_scores = cross_val_score(clf, X, y, cv=min(5, y.value_counts().min()), scoring="f1_macro")

    importances = pd.Series(clf.feature_importances_, index=FEATURES).sort_values(ascending=False)

    work["ml_prediction"] = clf.predict(X)
    work["ml_fraud_probability"] = clf.predict_proba(X)[:, 1] if len(clf.classes_) == 2 else np.nan

    leakage_warning = cv_scores.mean() > 0.97

    return {
        "model": clf,
        "cv_f1_macro_mean": cv_scores.mean(),
        "cv_f1_macro_std": cv_scores.std(),
        "feature_importances": importances,
        "scored_df": work,
        "leakage_warning": leakage_warning,
    }