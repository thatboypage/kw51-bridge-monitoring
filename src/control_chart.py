"""Daily control charts: raw frequency versus temperature-compensated residual.

Limits for both charts come from the BEFORE period only (mean +/- 3 standard deviations of daily values;
for the compensated chart, of the cross-validated residuals). Reported per mode:
  - false alarms: days outside the limits in the before period (the bridge was in service, unrepaired);
  - first alarm after the retrofit works began.
"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'src')
from load import load, RETROFIT_START
from analysis import MODES

F, E, P = load()
R = pd.read_csv('results/daily_residuals.csv', index_col=0, parse_dates=True)
period_d = P.resample('D').first()
rows = {}
for c in MODES:
    raw = F[c].resample('D').mean(); res = R[c]
    b = period_d == 'before'
    out = {}
    for name, s in [('raw', raw), ('compensated', res)]:
        mu, sd = s[b].mean(), s[b].std()
        out_lim = (s - mu).abs() > 3 * sd
        fa = int(out_lim[b].sum())
        post = out_lim[(s.index >= RETROFIT_START)]
        first = post[post].index.min()
        out[name] = dict(limit_hz=float(3 * sd), false_alarm_days_before=fa, days_before=int(b.sum()),
                         first_alarm_after_works_start=None if pd.isna(first) else str(first.date()),
                         share_after_days_flagged=float(out_lim[period_d == 'after'].mean()))
    rows[c] = out
json.dump(rows, open('results/control_chart.json', 'w'), indent=1)
for c, o in rows.items():
    print(c, {k: (v['limit_hz'] and round(v['limit_hz'], 4), v['false_alarm_days_before'], v['first_alarm_after_works_start'],
                  round(v['share_after_days_flagged'], 2)) for k, v in o.items()})
