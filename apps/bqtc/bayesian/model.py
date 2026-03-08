"""
Bayesian model for bandwidth prediction: PyMC or scikit-learn (Bayesian Ridge / GP).
Outputs point estimate per (VNI, path) for the QUBO stage.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np


def _fit_predict_sklearn(
    X: np.ndarray,
    y: np.ndarray,
    X_pred: np.ndarray,
    model_type: str = "bayesian_ridge",
) -> np.ndarray:
    """Fit and predict using scikit-learn. Returns predicted y for X_pred."""
    if model_type == "bayesian_ridge":
        from sklearn.linear_model import BayesianRidge
        model = BayesianRidge()
    elif model_type == "gaussian_process":
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel
        kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=1.0)
        model = GaussianProcessRegressor(kernel=kernel, alpha=1e-6)
    else:
        from sklearn.linear_model import BayesianRidge
        model = BayesianRidge()
    model.fit(X, y)
    return model.predict(X_pred)


def _fit_predict_pymc(
    X: np.ndarray,
    y: np.ndarray,
    X_pred: np.ndarray,
) -> np.ndarray:
    """Fit and predict using PyMC (Gaussian Process or hierarchical). Returns posterior mean."""
    try:
        import pymc as pm
    except ImportError:
        raise ImportError("PyMC not installed. Use pip install pymc or set backend to sklearn.")
    # Simple hierarchical normal model as placeholder; can be replaced by GP
    with pm.Model() as model:
        # Coefficients for linear part
        n_features = X.shape[1]
        beta = pm.Normal("beta", mu=0, sigma=1, shape=n_features)
        sigma = pm.HalfNormal("sigma", sigma=1)
        mu = pm.math.dot(X, beta)
        pm.Normal("obs", mu=mu, sigma=sigma, observed=y)
        idata = pm.sample(500, tune=500, progressbar=False, return_inferencedata=True)
    # Predict: mean of posterior predictive at X_pred
    beta_post = idata.posterior["beta"].mean(dim=("chain", "draw")).values
    return np.dot(X_pred, beta_post)


def predict_bandwidth_matrix(
    X_train: np.ndarray,
    y_train: np.ndarray,
    vnis: List[int],
    path_ids: List[str],
    dt: Optional[object] = None,
    backend: str = "sklearn",
    model_type: str = "bayesian_ridge",
) -> np.ndarray:
    """
    Produce expected bandwidth matrix B[vni_idx][path_idx] in bytes/sec.
    Uses current time for prediction; X_train/y_train from build_feature_matrix.
    """
    from .features import time_features
    from datetime import datetime
    dt = dt or datetime.utcnow()
    time_f = time_features(dt)
    rows_x = []
    for vni in vnis:
        for path_id in path_ids:
            vni_idx = vnis.index(vni) / max(len(vnis), 1)
            path_idx = path_ids.index(path_id) / max(len(path_ids), 1)
            x = np.concatenate([time_f, np.array([vni_idx, path_idx])])
            rows_x.append(x)
    X_pred = np.array(rows_x)
    if backend == "pymc":
        y_pred = _fit_predict_pymc(X_train, y_train, X_pred)
    else:
        y_pred = _fit_predict_sklearn(X_train, y_train, X_pred, model_type=model_type)
    # Clip to non-negative
    y_pred = np.maximum(y_pred, 0.0)
    matrix = y_pred.reshape((len(vnis), len(path_ids)))
    return matrix
