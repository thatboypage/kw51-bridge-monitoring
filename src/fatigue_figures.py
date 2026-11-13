"""Figure 6: measured diagonal stresses during train passages and where they sit on the Eurocode fatigue curves."""
import sys, json, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, 'src')
from fatigue import load_passages, rainflow, GAUGES

BLUE, ORANGE, GRAY, LGRAY, INK, INK2, RED, GREEN = '#2a78d6', '#eb6834', '#8a8984', '#c9c8c2', '#0b0b0b', '#52514e', '#c43c3c', '#3f9b62'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': LGRAY, 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
                     'grid.color': '#ecebe7', 'grid.linewidth': 0.8, 'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb'})
COL = dict(zip(GAUGES, [BLUE, '#7fb0ea', ORANGE, '#f2a985']))

P = load_passages()
R = pd.read_csv('results/fatigue_passages.csv')
S = json.load(open('results/fatigue_summary.json'))
big = R[R.gauge == 'sgDI20ALB'].sort_values('max_range_MPa').iloc[-1].file
p = next(q for q in P if q['file'] == big)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw=dict(width_ratios=[1, 1.15]))
t = np.arange(len(p['stress'][GAUGES[0]])) / p['fs']
for g in GAUGES:
    a1.plot(t, p['stress'][g], color=COL[g], lw=1, label=g.replace('sg', ''))
a1.set_xlabel('Time (s)'); a1.set_ylabel('Stress change (MPa)')
a1.legend(fontsize=8, frameon=False, ncol=2)
stamp = re.search(r'(\d{8})_(\d{6})', big).groups()
a1.set_title(f'Largest recorded passage ({stamp[0][:4]}-{stamp[0][4:6]}-{stamp[0][6:]} {stamp[1][:2]}:{stamp[1][2:4]})\n'
             'one large cycle per train plus small per-carriage cycles', loc='left', fontsize=10, color=INK)

# S-N curves (EN 1993-1-9) and the measured rainflow ranges
N = np.logspace(4, 9, 400)
for cat, c in ((71, GRAY), (90, LGRAY)):
    dD, dL = 0.737 * cat, 0.737 * cat * 0.549
    s = np.where(N <= 5e6, cat * (2e6 / N) ** (1 / 3), np.where(N <= 1e8, dD * (5e6 / N) ** (1 / 5), dL))
    a2.loglog(N, s, color=c, lw=2, label=f'detail category {cat} (cut-off {dL:.0f} MPa)')
r_all = []
for q in P:
    r, n = rainflow(q['stress']['sgDI20ALB'][~np.isnan(q['stress']['sgDI20ALB'])])
    r_all.extend(np.repeat(r[r > 2], np.round(2 * n[r > 2]).astype(int)))   # half cycles counted as two entries
r_all = np.sort(r_all)[::-1]
cum = np.arange(1, len(r_all) + 1) / 2 / len(P) * 2e6   # cycles per 2 million passages
a2.loglog(cum, r_all, color=BLUE, lw=2, label='measured, diagonal 20 (DI20ALB), 2 M passages')
k = S['sgDI20ALB']['scf_for_D1']['2M_passages_cat71']
a2.loglog(cum, r_all * k, color=RED, lw=1.5, ls='--', label=f'same, x{k:.1f} local concentration (D = 1)')
a2.set_xlim(1e4, 1e9); a2.set_ylim(3, 400)
a2.set_xlabel('Number of cycles'); a2.set_ylabel('Stress range (MPa)')
a2.legend(fontsize=8, frameon=False, loc='upper right')
a2.set_title('Nominal stresses stay below the fatigue cut-off', loc='left', fontsize=10, color=INK)
fig.text(0.01, 0.01, 'Gauges on diagonals 20 and 23, 13 passages, 1–7 May 2019 (before the strengthening). Stress = 210 GPa x strain. '
         'Measured curve: exceedance count of rainflow ranges on the most loaded gauge, scaled to 2 million passages.',
         fontsize=7.5, color=INK2)
plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig('figures/fig6_fatigue.png', dpi=160); plt.close()
print('saved')
