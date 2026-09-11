import numpy as np
import pandas as pd
from scipy.optimize import minimize


def fit_strengths(pool: pd.DataFrame, log: pd.DataFrame) -> pd.DataFrame:
    uris = pool["film_uri"].tolist()
    idx = {u: i for i, u in enumerate(uris)}
    n = len(uris)

    prior_mean = pool["prior_mean"].to_numpy()
    prior_sd = pool["prior_sd"].to_numpy()

    valid = log[log["film_a"].isin(idx) & log["film_b"].isin(idx)]
    a_idx = np.array([idx[u] for u in valid["film_a"]], dtype=int)
    b_idx = np.array([idx[u] for u in valid["film_b"]], dtype=int)
    a_won = (valid["winner"] == valid["film_a"]).to_numpy()

    def neg_log_posterior(s):
        diff = s[a_idx] - s[b_idx]
        ll = np.sum(np.where(a_won, -np.logaddexp(0, -diff), -np.logaddexp(0, diff)))
        prior = -0.5 * np.sum(((s - prior_mean) / prior_sd) ** 2)
        return -(ll + prior)

    result = minimize(neg_log_posterior, prior_mean.copy(), method="L-BFGS-B")

    counts = np.bincount(np.concatenate([a_idx, b_idx]), minlength=n)
    posterior_sd = prior_sd / np.sqrt(1 + counts)

    return pd.DataFrame({
        "film_uri": uris,
        "strength": result.x,
        "posterior_sd": posterior_sd,
        "n_comparisons": counts,
    })