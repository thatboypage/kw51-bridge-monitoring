"""Does the conclusion depend on the unpublished assumptions? Repeat the before/after fit with the arch rise
fixed at 15, 19 and 23 m, and with the alternative diagonal layout, and record the inferred change in
diagonal stiffness and added mass, and how well each variant reproduces the measured changes."""
import sys, json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
sys.path.insert(0, 'src')
from fe_model import modes
from fe_update import pair, F_BEFORE, targets_change

CH = targets_change()


def run(h, layout):
    def p(q):
        m, gf, kap = q
        return dict(h=h, mass_per_m=m, girder_factor=gf, kappa=kap, layout=layout)

    def lb(q):
        m, gf, kap = q
        if not (6000 < m < 10000 and 0.5 < gf < 15 and 0.02 < kap <= 1.0):
            return 1e3
        f, _, s, _ = modes(n=14, **p(q))
        P = pair(f, s)
        return sum(((P[k][0] - F_BEFORE[k]) / F_BEFORE[k]) ** 2 for k in P) + 0.05 * sum(1 - P[k][1] for k in P)

    r = min((minimize(lb, s0, method='Nelder-Mead', options=dict(maxiter=400)) for s0 in [(7800, 4, 0.3), (8500, 6, 0.7)]),
            key=lambda r: r.fun)
    f0, _, s0, _ = modes(n=14, **p(r.x)); P0 = pair(f0, s0)

    def change(kap1, madd):
        f1, _, s1, _ = modes(n=14, **dict(p(r.x), kappa=kap1, added_mass=madd)); P1 = pair(f1, s1)
        return {k: 100 * (P1[k][0] / P0[k][0] - 1) for k in P0}

    def la(q):
        if not (0.02 < q[0] <= 1.5 and 0 <= q[1] < 60000):
            return 1e3
        c = change(*q)
        return sum((c[k] - CH[k]) ** 2 for k in CH)

    ra = min((minimize(la, s, method='Nelder-Mead', options=dict(maxiter=300)) for s in [(r.x[2] * 1.08, 8000), (r.x[2] * 1.03, 2000)]),
             key=lambda r: r.fun)
    return dict(arch_rise_m=h, layout=layout, kappa_before=r.x[2], kappa_after=ra.x[0],
                diag_stiffness_increase_pct=100 * (ra.x[0] / r.x[2] - 1), added_mass_t_per_side=ra.x[1] / 1000,
                fit_rms_pct_points=float(np.sqrt(ra.fun / len(CH))),
                before_freq_mean_abs_err_pct=float(np.mean([abs(P0[k][0] / F_BEFORE[k] - 1) * 100 for k in P0])),
                min_mac=float(min(P0[k][1] for k in P0)))


def main():
    rows = [run(h, 'warren') for h in (15, 19, 23)] + [run(23, 'inverted')]
    S = pd.DataFrame(rows)
    S.to_csv('results/fe_sensitivity.csv', index=False)
    print(S.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
