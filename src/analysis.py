"""Temperature compensation of KW51 natural frequencies and the effect of the retrofit.

1. Learn each mode's normal temperature behaviour from the BEFORE period only (Oct 2018 - mid May 2019).
   Candidate models are compared by blocked cross-validation (whole months held out), so the choice
   does not depend on the after-retrofit data.
2. Residual = measured - predicted frequency. Daily-mean residuals form a control chart; the alarm limit is
   set from the before-period cross-validated residuals.
3. Retrofit effect per mode = mean residual AFTER retrofit (Sep 2019 - Jan 2020), i.e. the frequency change at
   the same temperature, with a 95% interval from a weekly block bootstrap. It is compared with the naive
   before/after difference that ignores temperature.
"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'src')
from load import load

MODES = ['mode3', 'mode5', 'mode6', 'mode9', 'mode13']   # modes tracked >= 80% of the time in all periods
TEMP = 'tBD31A'                                          # steel temperature measured on the bridge deck
KNOTS = np.arange(-2.0, 6.01, 0.5)


def design(T, kind, knot=None):
    cols = [np.ones_like(T), T]
    if kind == 'hinge':
        cols.append(np.maximum(knot - T, 0.0))           # extra stiffening below the knot (freezing)
    return np.column_stack(cols)


def fit(T, f, kind, knot=None):
    X = design(T, kind, knot)
    beta, *_ = np.linalg.lstsq(X, f, rcond=None)
    return beta


def predict(beta, T, kind, knot=None):
    return design(T, kind, knot) @ beta


def blocked_cv(T, f, month, kind, knot=None):
    res = np.full_like(f, np.nan)
    for mth in np.unique(month):
        tr, te = month != mth, month == mth
        res[te] = f[te] - predict(fit(T[tr], f[tr], kind, knot), T[te], kind, knot)
    return res


def block_bootstrap_mean(x, week, B=4000, seed=0):
    rng = np.random.default_rng(seed)
    weeks = np.unique(week); groups = [x[week == w] for w in weeks]
    stats = []
    for _ in range(B):
        pick = rng.integers(0, len(groups), len(groups))
        stats.append(np.concatenate([groups[i] for i in pick]).mean())
    return np.percentile(stats, [2.5, 97.5])


def main():
    F, E, P = load()
    T_all = E[TEMP]
    out, resid_daily, models = [], {}, {}
    for c in MODES:
        ok = F[c].notna() & T_all.notna()
        b = ok & (P == 'before'); a = ok & (P == 'after')
        Tb, fb = T_all[b].values, F[c][b].values
        month = F.index[b].to_period('M').astype(str).values
        # --- model choice by blocked CV on the before period only
        cand = {('linear', None): blocked_cv(Tb, fb, month, 'linear')}
        for k in KNOTS:
            cand[('hinge', k)] = blocked_cv(Tb, fb, month, 'hinge', k)
        rmse = {key: float(np.sqrt(np.nanmean(r ** 2))) for key, r in cand.items()}
        kind, knot = min(rmse, key=rmse.get)
        beta = fit(Tb, fb, kind, knot)
        models[c] = dict(kind=kind, knot=knot, beta=beta.tolist(), cv_rmse_hz=rmse[(kind, knot)],
                         cv_rmse_linear_hz=rmse[('linear', None)])
        cv_res = cand[(kind, knot)]
        # --- residuals everywhere (before: cross-validated; during/after: model fitted on before)
        r = pd.Series(np.nan, index=F.index)
        r[b] = cv_res
        oth = ok & (P != 'before')
        r[oth] = F[c][oth].values - predict(beta, T_all[oth].values, kind, knot)
        daily = r.resample('D').mean()
        resid_daily[c] = daily
        # --- retrofit effect
        ra = r[a].values; week_a = F.index[a].to_period('W').astype(str).values
        lo, hi = block_bootstrap_mean(ra, week_a)
        rb = cv_res; week_b = F.index[b].to_period('W').astype(str).values
        blo, bhi = block_bootstrap_mean(rb, week_b)
        f0 = float(np.mean(fb))
        naive = float(F[c][a].mean() - F[c][b].mean())
        out.append(dict(mode=c, f_before_hz=f0, model=kind if kind == 'linear' else f'hinge at {knot:g} C',
                        temp_slope_pct_per_C=100 * beta[1] / f0, cv_rmse_hz=rmse[(kind, knot)],
                        cv_rmse_linear_hz=rmse[('linear', None)],
                        effect_hz=float(ra.mean()), effect_ci_lo_hz=float(lo), effect_ci_hi_hz=float(hi),
                        effect_pct=100 * float(ra.mean()) / f0,
                        effect_ci_lo_pct=100 * lo / f0, effect_ci_hi_pct=100 * hi / f0,
                        naive_diff_hz=naive, naive_diff_pct=100 * naive / f0,
                        before_resid_mean_hz=float(rb.mean()), before_resid_ci=[float(blo), float(bhi)]))
    R = pd.DataFrame(out)
    R.to_csv('results/retrofit_effect.csv', index=False)
    pd.DataFrame(resid_daily).to_csv('results/daily_residuals.csv')
    json.dump(models, open('results/temperature_models.json', 'w'), indent=1, default=float)
    # --- sensitivity to the comparison window: naive vs temperature-adjusted
    windows = {'all before vs all after': (P == 'before', P == 'after'),
               '6 weeks before works vs 6 weeks after': ((F.index >= '2019-04-01') & (F.index < '2019-05-15'),
                                                         (F.index >= '2019-09-27') & (F.index < '2019-11-08')),
               'winter (Dec-Feb) vs 6 weeks after': ((F.index >= '2018-12-01') & (F.index < '2019-03-01'),
                                                    (F.index >= '2019-09-27') & (F.index < '2019-11-08'))}
    sens = []
    for c in MODES:
        m = models[c]; f0 = float(F[c][P == 'before'].mean())
        r = F[c] - predict(np.array(m['beta']), T_all.values, m['kind'], m['knot'])
        for name, (wb, wa) in windows.items():
            ok = F[c].notna() & T_all.notna(); wb, wa = wb & ok, wa & ok
            sens.append(dict(mode=c, window=name, temp_before_C=float(T_all[wb].mean()), temp_after_C=float(T_all[wa].mean()),
                             naive_pct=100 * float(F[c][wa].mean() - F[c][wb].mean()) / f0,
                             adjusted_pct=100 * float(r[wa].mean() - r[wb].mean()) / f0))
    S = pd.DataFrame(sens); S.to_csv('results/window_sensitivity.csv', index=False)
    pd.set_option('display.width', 220)
    print(R[['mode', 'f_before_hz', 'model', 'temp_slope_pct_per_C', 'cv_rmse_hz', 'cv_rmse_linear_hz', 'naive_diff_pct',
             'effect_pct', 'effect_ci_lo_pct', 'effect_ci_hi_pct']].round(4).to_string(index=False))
    print(S.pivot(index='mode', columns='window', values=['naive_pct', 'adjusted_pct']).round(2).to_string())


if __name__ == '__main__':
    main()
