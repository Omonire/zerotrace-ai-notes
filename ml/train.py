"""Train and persist the note classifier.

Usage::

    python -m ml.train                 # seed/bundled dataset
    python -m ml.train --notes         # train on the app's notes table
    python -m ml.train --data file.json

The trained pipeline is saved to ``ml/model.joblib`` with metadata, and can
be loaded at runtime by :mod:`ml.predict`. If the dataset is too small to
cross-validate each fold contains every class, falls back to train/test split.
"""

import argparse
import datetime
import os
import time

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from ml.dataset import CATEGORIES, SEED_EXAMPLES, examples_from_notes, load_dataset

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")


def build_pipeline():
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
        )),
        ("clf", LinearSVC(C=1.0, class_weight="balanced", dual="auto")),
    ])


def train(examples, model_path=MODEL_PATH):
    if len(examples) < 40:
        raise ValueError(
            "Need at least 40 examples to train, got %d. Add more labeled data." % len(examples)
        )
    if not isinstance(examples, list):
        texts, labels = list(zip(*examples))
    else:
        texts, labels = zip(*examples)

    by_label = {}
    for text, label in zip(texts, labels):
        by_label.setdefault(label, []).append(text)

    missing = [c for c in CATEGORIES if c not in by_label]
    if missing:
        print("WARNING: no examples for categories: %s" % ", ".join(missing))

    pipeline = build_pipeline()

    min_class = min(len(v) for v in by_label.values())
    scores = None
    if min_class >= 2:
        try:
            scores = cross_val_score(pipeline, texts, labels, cv=5, scoring="accuracy")
        except ValueError:
            scores = None
            print("CV failed; falling back to a single held-out split.")

    if scores is not None:
        print("5-fold CV accuracy: %.3f +/- %.3f" % (scores.mean(), scores.std()))
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.25, stratify=labels, random_state=42
        )
        pipeline.fit(X_train, y_train)
        acc = pipeline.score(X_test, y_test)
        print("held-out accuracy (fewer samples): %.3f" % acc)

    pipeline.fit(texts, labels)

    metadata = {
        "categories": CATEGORIES,
        "size": len(examples),
        "trained_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "pipeline": "TfidfVectorizer + LinearSVC",
        "accuracy": float(scores.mean()) if scores is not None else float(acc),
    }

    import joblib
    joblib.dump({"pipeline": pipeline, "metadata": metadata}, model_path)
    print("saved", model_path, "| %d examples" % len(examples))
    return pipeline, metadata


def main():
    parser = argparse.ArgumentParser(description="Train the note classifier")
    parser.add_argument("--data", help="path to a JSON dataset [{text, category}]")
    parser.add_argument("--notes", action="store_true", help="train from the app's notes table")
    args = parser.parse_args()

    if args.data:
        examples = load_dataset(args.data)
    elif args.notes:
        from database import init_db, get_db
        init_db()
        examples = examples_from_notes(get_db())
    else:
        examples = SEED_EXAMPLES

    if not examples:
        raise SystemExit("No training examples found")

    start = time.time()
    pipeline, metadata = train(examples)
    print("total time: %.2fs" % (time.time() - start))
    pipeline.predict(["classify a fresh meeting note about a client call"])
    print("sample prediction ok")


if __name__ == "__main__":
    main()