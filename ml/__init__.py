"""Local ML model for ZeroTrace AI Notes.

A small scikit-learn pipeline that classifies note text into categories.
No external service required: the model is trained offline and committed
as ``ml/model.joblib``, then loaded lazily at runtime by :mod:`ml.predict`.

    python -m ml.predict  -- classify sample text
    python -m ml.train    -- (re)train the model and persist ml/model.joblib

Submodules: ``dataset`` (training data/loaders), ``train``, ``predict``.
"""