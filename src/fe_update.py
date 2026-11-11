"""Model updating of the in-plane KW51 model.

Step 1 (before strengthening): tune arch rise h, distributed mass, girder stiffness factor and diagonal
  stiffness factor kappa_before so the model's vertical modes match the measured pre-strengthening
  frequencies of modes 5, 6, 10, 12 and 13. Model modes are paired with measured ones by MAC on the deck
  vertical mode shape at the three instrumented sections (measured shapes are from after the works, the only
  period with shapes; the strengthening changes frequencies by about 2%, too little to change shape order).
Step 2 (after): keep step 1 fixed and fit only kappa_after and the added steel mass to the measured changes.
  Targets: temperature-adjusted changes for modes 5, 6, 13 (results/retrofit_effect.csv) and before/after
  mean changes for modes 10 and 12 (tracked less often, so not temperature-adjusted).
"""
import sys, json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
sys.path.insert(0, 'src')
from fe_model import modes, mac

MEAS_SHAPE = {5: [0.45, 0.71, 0.54], 6: [-0.67, -0.04, 0.74], 10: [-0.07, 0.99, -0.07],
              12: [-0.61, -0.09, 0.78], 13: [-0.47, 0.67, -0.58]}
F_BEFORE = {5: 2.580, 6: 2.924, 10: 4.301, 12: 5.327, 13: 6.326}
F_AFTER_MEAN = {5: 2.571, 6: 2.985, 10: 4.387, 12: 5.437, 13: 6.418}


def targets_change():
    eff = pd.read_csv('results/retrofit_effect.csv').set_index('mode')
    ch = {5: eff.loc['mode5', 'effect_pct'], 6: eff.loc['mode6', 'effect_pct'], 13: eff.loc['mode13', 'effect_pct']}
    for k in (10, 12):
        ch[k] = 100 * (F_AFTER_MEAN[k] / F_BEFORE[k] - 1)
    return ch


def pair(f, sens):
    """Order-preserving one-to-one pairing: measured modes in frequency order, each matched to the
    best-MAC model mode among the next three not yet used."""
    out, j0 = {}, 0
    for k in sorted(MEAS_SHAPE, key=lambda k: F_BEFORE[k]):
        cand = range(j0, min(j0 + 3, len(f)))
        macs = {j: mac(np.array(MEAS_SHAPE[k]), sens[j]) for j in cand}
        j = max(macs, key=macs.get)
        out[k] = (f[j], macs[j], j)
        j0 = j + 1
    return out


def params(p):
    h, m, gf, kap = p
    return dict(h=h, mass_per_m=m, girder_factor=gf, kappa=kap)


def loss_before(p):
    h, m, gf, kap = p
    if not (10 < h < 23 and 6000 < m < 10000 and 0.5 < gf < 15 and 0.02 < kap <= 1.0):
        return 1e3
    f, _, sens, _ = modes(n=14, **params(p))
    P = pair(f, sens)
    err = sum(((P[k][0] - F_BEFORE[k]) / F_BEFORE[k]) ** 2 for k in P)
    pen = sum((1 - P[k][1]) for k in P)                  # prefer well-matched shapes
    return err + 0.05 * pen


def main():
    rng = np.random.default_rng(0)
    best = None
    for start in [(17, 7800, 4, 0.3), (14, 7000, 2, 0.15), (20, 9000, 8, 0.5)]:
        r = minimize(loss_before, start, method='Nelder-Mead', options=dict(maxiter=700, xatol=1e-4, fatol=1e-10))
        if best is None or r.fun < best.fun:
            best = r
    p0 = best.x
    f, _, sens, _ = modes(n=14, **params(p0))
    P0 = pair(f, sens)
    print('before: h=%.2f m, mass=%.0f kg/m, girder factor=%.2f, kappa_before=%.3f' % tuple(p0))
    for k in P0:
        print('  mode %d: model %.3f Hz vs measured %.3f Hz (MAC %.2f)' % (k, P0[k][0], F_BEFORE[k], P0[k][1]))

    ch = targets_change()

    def model_change(q):
        kap1, madd = q
        f1, _, s1, _ = modes(n=14, **dict(params(p0), kappa=kap1, added_mass=madd))
        P1 = pair(f1, s1)
        return {k: 100 * (P1[k][0] / P0[k][0] - 1) for k in P0}

    def loss_after(q):
        kap1, madd = q
        if not (0.05 < kap1 <= 1.5 and 0 <= madd < 60000):
            return 1e3
        mc = model_change(q)
        return sum((mc[k] - ch[k]) ** 2 for k in ch)

    ra = min((minimize(loss_after, s, method='Nelder-Mead', options=dict(maxiter=600)) for s in
              [(min(1.0, p0[3] * 1.3), 5000), (min(1.0, p0[3] * 1.1), 0), (1.0, 15000)]), key=lambda r: r.fun)
    mc = model_change(ra.x)
    # comparisons: stiffness only, mass only
    r_k = minimize(lambda q: loss_after((q[0], 0.0)), [min(1.0, p0[3] * 1.2)], method='Nelder-Mead')
    r_m = minimize(lambda q: loss_after((p0[3], q[0])), [5000], method='Nelder-Mead')
    mk, mm_ = model_change((r_k.x[0], 0.0)), model_change((p0[3], r_m.x[0]))
    rows = [dict(mode=k, measured_change_pct=ch[k], model_both_pct=mc[k], model_stiffness_only_pct=mk[k],
                 model_mass_only_pct=mm_[k], f_model_before=P0[k][0], f_measured_before=F_BEFORE[k], mac=P0[k][1])
            for k in sorted(ch)]
    T = pd.DataFrame(rows)
    T.to_csv('results/fe_update.csv', index=False)
    print(T.round(3).to_string(index=False))
    rms = lambda col: float(np.sqrt(np.mean((T[col] - T.measured_change_pct) ** 2)))
    out = dict(before=dict(arch_rise_m=p0[0], mass_kg_per_m_per_side=p0[1], girder_stiffness_factor=p0[2], kappa_before=p0[3]),
               after=dict(kappa_after=ra.x[0], added_mass_kg_per_side=ra.x[1]),
               stiffness_only=dict(kappa_after=r_k.x[0]), mass_only=dict(added_mass_kg=r_m.x[0]),
               rms_error_pct_points=dict(both=rms('model_both_pct'), stiffness_only=rms('model_stiffness_only_pct'),
                                         mass_only=rms('model_mass_only_pct')),
               freq_error_before_pct={k: 100 * (P0[k][0] / F_BEFORE[k] - 1) for k in P0})
    json.dump(out, open('results/fe_update.json', 'w'), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == '__main__':
    main()
