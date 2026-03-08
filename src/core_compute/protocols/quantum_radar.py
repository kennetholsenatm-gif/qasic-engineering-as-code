"""
Continuous-variable quantum radar (toy): TMSV + lossy thermal beam splitter.

Matches the whitepaper's TMSV description: generate two-mode squeezed vacuum (idler + signal),
pass the signal through a lossy channel (beam splitter with transmittance eta, thermal bath N_B),
then compute mutual information or SNR of the (idler, return) state.

Uses state/cv_state.py (GaussianState, covariance V) and state/cv_gates.py (symplectic S).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core_compute.state.cv_state import GaussianState, vacuum_covariance, thermal_covariance
from src.core_compute.state.cv_gates import two_mode_squeezing, beam_splitter, tmsv_covariance


def tmsv_through_loss(
    eta: float,
    n_b: float,
    r: float,
) -> GaussianState:
    """
    (Idler, return) state after TMSV and lossy beam splitter.

    - TMSV on modes 0 (idler) and 1 (signal) with squeezing r.
    - Mode 2 is thermal bath with mean photon number n_b.
    - Beam splitter on modes 1 and 2 with transmittance eta (signal survives with prob eta).
    - Return the reduced state on modes 0 (idler) and 1 (return).

    So: V_init = block_diag(V_TMSV_4x4, (n_b+1/2)*I2). Then S = I2 ⊕ BS(eta). V' = S V S^T. Reduce to [0,1].
    """
    if not 0 <= eta <= 1 or n_b < 0 or r < 0:
        raise ValueError("eta in [0,1], n_b >= 0, r >= 0")
    V_tmsv = tmsv_covariance(r)
    V_therm = thermal_covariance(n_b)
    V_full = np.zeros((6, 6), dtype=np.float64)
    V_full[:4, :4] = V_tmsv
    V_full[4:, 4:] = V_therm
    state = GaussianState(V_full, n_modes=3, check_physical=True)
    S_bs = beam_splitter(eta)
    # Embed: identity on mode 0, BS on modes 1,2
    S_full = np.eye(6, dtype=np.float64)
    S_full[2:4, 2:4] = S_bs[:2, :2]
    S_full[2:4, 4:6] = S_bs[:2, 2:4]
    S_full[4:6, 2:4] = S_bs[2:4, :2]
    S_full[4:6, 4:6] = S_bs[2:4, 2:4]
    V_out = S_full @ V_full @ S_full.T
    # Reduce to modes 0 and 1
    V_red = V_out[:4, :4].copy()
    d_red = np.zeros(4, dtype=np.float64)
    return GaussianState(V_red, d_red, n_modes=2, check_physical=False)


def state_H0_target_absent(r: float, n_b: float) -> GaussianState:
    """
    (Idler, return) when target is absent: signal fully lost, return is thermal n_b.
    Idler is the reduced state of TMSV (thermal with variance cosh(2r)/2 per quadrature).
    """
    a = np.cosh(2.0 * r) / 2.0
    V_idler = a * np.eye(2, dtype=np.float64)
    V_return = thermal_covariance(n_b)
    V = np.zeros((4, 4), dtype=np.float64)
    V[:2, :2] = V_idler
    V[2:, 2:] = V_return
    return GaussianState(V, n_modes=2, check_physical=False)


def mutual_information(state: GaussianState) -> float:
    """Mutual information I(A;B) = S(V_A) + S(V_B) - S(V_AB) for a 2-mode Gaussian state."""
    if state.n_modes != 2:
        raise ValueError("mutual_information requires 2-mode state")
    s_ab = state.von_neumann_entropy()
    s_a = state.reduced([0]).von_neumann_entropy()
    s_b = state.reduced([1]).von_neumann_entropy()
    return float(s_a + s_b - s_ab)


def return_mode_variance(state: GaussianState) -> float:
    """Variance (in q or p, equal for our states) of the return mode (mode 1). For SNR, lower noise = better."""
    red = state.reduced([1])
    return float(red.V[0, 0])  # Var(q) = V[0,0]


def snr_homodyne_simple(V_return: float) -> float:
    """Simple SNR proxy: 1 / (2 * variance) (vacuum variance = 1/2, so SNR_vac = 1). Not signal power over noise."""
    return 1.0 / (2.0 * max(V_return, 1e-12))


def run_quantum_radar(
    eta: float = 0.01,
    n_b: float = 100.0,
    r: float = 0.5,
) -> dict:
    """
    Run the toy CV quantum radar: TMSV through lossy thermal channel.
    Returns (idler, return) covariance metrics for H1 (target present) and H0 (target absent).
    """
    state_H1 = tmsv_through_loss(eta, n_b, r)
    state_H0 = state_H0_target_absent(r, n_b)
    I_H1 = mutual_information(state_H1)
    I_H0 = mutual_information(state_H0)
    var_H1 = return_mode_variance(state_H1)
    var_H0 = return_mode_variance(state_H0)
    return {
        "eta": eta,
        "n_b": n_b,
        "r": r,
        "I_H1": I_H1,
        "I_H0": I_H0,
        "mutual_info_H1": I_H1,
        "mutual_info_H0": I_H0,
        "return_variance_H1": var_H1,
        "return_variance_H0": var_H0,
        "snr_proxy_H1": snr_homodyne_simple(var_H1),
        "snr_proxy_H0": snr_homodyne_simple(var_H0),
    }


def sweep_parameter(
    param: str,
    min_val: float,
    max_val: float,
    steps: int,
    eta: float,
    n_b: float,
    r: float,
) -> list[dict]:
    """Sweep one parameter (eta, n_b, or r) over [min_val, max_val]; others fixed. Returns list of run_quantum_radar outputs."""
    values = np.linspace(min_val, max_val, steps).tolist()
    results = []
    for v in values:
        kw = {"eta": eta, "n_b": n_b, "r": r}
        kw[param] = v
        results.append(run_quantum_radar(**kw))
    return results


def optimize_parameter(
    param: str,
    low: float,
    high: float,
    steps: int,
    eta: float,
    n_b: float,
    r: float,
    maximize: str,
) -> tuple[float, dict]:
    """
    Grid search over param in [low, high] to maximize mutual_info_H1 or snr_proxy_H1.
    Returns (best_value, best_result_dict).
    """
    values = np.linspace(low, high, steps)
    best_val = None
    best_metric = -np.inf
    best_result = None
    key = "mutual_info_H1" if maximize == "mutual_info" else "snr_proxy_H1"
    for v in values:
        v = float(v)
        kw = {"eta": eta, "n_b": n_b, "r": r}
        kw[param] = v
        res = run_quantum_radar(**kw)
        m = res[key]
        if m > best_metric:
            best_metric = m
            best_val = v
            best_result = res
    return best_val, best_result


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Toy CV quantum radar: TMSV + lossy thermal BS")
    p.add_argument("--eta", type=float, default=0.01, help="Transmittance (signal survival)")
    p.add_argument("--n_b", type=float, default=100.0, help="Thermal bath mean photon number")
    p.add_argument("--r", type=float, default=0.5, help="TMSV squeezing strength")
    # Sweep
    p.add_argument("--sweep", choices=["eta", "n_b", "r"], default=None, help="Sweep this parameter")
    p.add_argument("--min", type=float, default=None, dest="sweep_min", help="Sweep min (default: 0.01 for eta, 0.1 for n_b, 0.1 for r)")
    p.add_argument("--max", type=float, default=None, dest="sweep_max", help="Sweep max (default: 0.5 for eta, 50 for n_b, 1.5 for r)")
    p.add_argument("--steps", type=int, default=21, help="Sweep / optimization grid steps")
    p.add_argument("-o", "--output", type=str, default=None, help="Write sweep table to CSV")
    # Optimize
    p.add_argument("--optimize", choices=["eta", "n_b", "r"], default=None, help="Optimize this parameter (grid search)")
    p.add_argument("--optimize-min", type=float, default=None, help="Optimization lower bound")
    p.add_argument("--optimize-max", type=float, default=None, help="Optimization upper bound")
    p.add_argument("--maximize", choices=["mutual_info", "snr"], default="mutual_info", help="Metric to maximize (mutual_info_H1 or snr_proxy_H1)")
    args = p.parse_args()

    if args.sweep:
        param = args.sweep
        defaults = {"eta": (0.01, 0.5), "n_b": (0.1, 50.0), "r": (0.1, 1.5)}
        lo, hi = defaults[param]
        min_val = args.sweep_min if args.sweep_min is not None else lo
        max_val = args.sweep_max if args.sweep_max is not None else hi
        results = sweep_parameter(param, min_val, max_val, args.steps, args.eta, args.n_b, args.r)
        # Table
        print("CV Quantum Radar (toy) — sweep {}".format(param))
        print("{:>12} {:>14} {:>14} {:>14} {:>12} {:>12}".format(
            param, "I_H1", "I_H0", "Var_H1", "Var_H0", "SNR_H1"))
        print("-" * 78)
        for row in results:
            print("{:>12.6g} {:>14.6f} {:>14.6f} {:>14.6f} {:>12.6f} {:>12.6f}".format(
                row[param], row["mutual_info_H1"], row["mutual_info_H0"],
                row["return_variance_H1"], row["return_variance_H0"], row["snr_proxy_H1"]))
        if args.output:
            with open(args.output, "w") as f:
                f.write("{},mutual_info_H1,mutual_info_H0,return_variance_H1,return_variance_H0,snr_proxy_H1\n".format(param))
                for row in results:
                    f.write("{},{},{},{},{},{}\n".format(
                        row[param], row["mutual_info_H1"], row["mutual_info_H0"],
                        row["return_variance_H1"], row["return_variance_H0"], row["snr_proxy_H1"]))
            print("Wrote {}".format(args.output))
        return

    if args.optimize:
        param = args.optimize
        defaults = {"eta": (0.01, 0.99), "n_b": (0.0, 100.0), "r": (0.05, 2.0)}
        lo, hi = defaults[param]
        low = args.optimize_min if args.optimize_min is not None else lo
        high = args.optimize_max if args.optimize_max is not None else hi
        best_val, best_result = optimize_parameter(
            param, low, high, args.steps, args.eta, args.n_b, args.r, args.maximize
        )
        key = "mutual_info_H1" if args.maximize == "mutual_info" else "snr_proxy_H1"
        print("CV Quantum Radar (toy) — optimize {} (maximize {})".format(param, key))
        print("  Fixed: eta = {}, n_b = {}, r = {}".format(
            best_result["eta"], best_result["n_b"], best_result["r"]))
        print("  Best {} = {:.6g}  =>  {} = {:.6f}".format(param, best_val, key, best_result[key]))
        print("  H1: I(idler;return) = {:.6f}, return Var = {:.6f}, SNR proxy = {:.6f}".format(
            best_result["mutual_info_H1"], best_result["return_variance_H1"], best_result["snr_proxy_H1"]))
        print("  H0: I(idler;return) = {:.6f}, return Var = {:.6f}, SNR proxy = {:.6f}".format(
            best_result["mutual_info_H0"], best_result["return_variance_H0"], best_result["snr_proxy_H0"]))
        return

    # Single run
    out = run_quantum_radar(eta=args.eta, n_b=args.n_b, r=args.r)
    print("CV Quantum Radar (toy)")
    print("  eta =", out["eta"], ", n_b =", out["n_b"], ", r =", out["r"])
    print("  H1 (target present): I(idler;return) = {:.6f}, return Var = {:.6f}, SNR proxy = {:.6f}".format(
        out["mutual_info_H1"], out["return_variance_H1"], out["snr_proxy_H1"]))
    print("  H0 (target absent):  I(idler;return) = {:.6f}, return Var = {:.6f}, SNR proxy = {:.6f}".format(
        out["mutual_info_H0"], out["return_variance_H0"], out["snr_proxy_H0"]))


if __name__ == "__main__":
    main()
