import sys, json, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, 'src')
from load import load, RETROFIT_START, RETROFIT_END
from analysis import MODES, TEMP, predict

BLUE, ORANGE, GRAY, LGRAY, INK, INK2, RED = '#2a78d6', '#eb6834', '#8a8984', '#c9c8c2', '#0b0b0b', '#52514e', '#c43c3c'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': LGRAY, 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
                     'grid.color': '#ecebe7', 'grid.linewidth': 0.8, 'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb'})
F, E, P = load()
R = pd.read_csv('results/daily_residuals.csv', index_col=0, parse_dates=True)
M = json.load(open('results/temperature_models.json'))
X = pd.read_csv('results/retrofit_effect.csv')
period_d = P.resample('D').first()


def shade(ax):
    ax.axvspan(RETROFIT_START, RETROFIT_END, color=LGRAY, alpha=0.35, lw=0)
    ax.text(RETROFIT_START + (RETROFIT_END - RETROFIT_START) / 2, 0.97, 'retrofit works', transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=8, color=INK2)


# ---- Fig 1: raw vs compensated daily chart, mode 13
c = 'mode13'
raw = F[c].resample('D').mean(); res = R[c]; b = period_d == 'before'
fig, ax = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True)
for a, s, ttl, unit in [(ax[0], raw, 'Raw daily frequency', 'Hz'),
                        (ax[1], res, 'Temperature-compensated residual (measured − predicted)', 'Hz')]:
    mu, sd = s[b].mean(), s[b].std()
    a.plot(s.index, s, color=BLUE if a is ax[1] else GRAY, lw=1.1)
    a.axhline(mu + 3 * sd, color=RED, lw=1, ls='--'); a.axhline(mu - 3 * sd, color=RED, lw=1, ls='--')
    a.set_ylabel(unit); a.set_title(ttl, loc='left', fontsize=10, color=INK); shade(a)
fig.suptitle('Mode 13 (6.3 Hz): removing temperature makes the retrofit visible', x=0.01, ha='left', fontsize=11, color=INK)
fig.text(0.01, 0.005, 'Dashed: alarm limits (±3 SD of the pre-retrofit daily values). The January spike is freezing weather; on the raw\n'
         'chart it widens the limits so much that the post-retrofit shift is never flagged.', fontsize=7.5, color=INK2)
plt.tight_layout(rect=(0, 0.05, 1, 0.96)); plt.savefig('figures/fig1_control_chart_mode13.png', dpi=160); plt.close()

# ---- Fig 2: frequency vs temperature, before and after, with the before-period model
fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.9))
for a, c in zip(ax, ['mode6', 'mode13']):
    for p, col in [('before', BLUE), ('after', ORANGE)]:
        s = P == p
        a.plot(E[TEMP][s], F[c][s], '.', ms=1.5, color=col, alpha=0.35, label=f'{p} retrofit')
    m = M[c]; Tg = np.linspace(-3, 27, 200)
    a.plot(Tg, predict(np.array(m['beta']), Tg, m['kind'], m['knot']), color=INK, lw=1.4, label='model (fitted before)')
    a.set_xlabel('Steel deck temperature (°C)'); a.set_ylabel('Frequency (Hz)')
    a.set_title(f"Mode {c[4:]}", loc='left', fontsize=10, color=INK)
ax[0].legend(fontsize=8, frameon=False, markerscale=6)
fig.suptitle('Frequencies fall as the steel warms and jump below about 1 °C; the retrofit shifts the whole curve',
             x=0.01, ha='left', fontsize=10.5, color=INK)
plt.tight_layout(rect=(0, 0, 1, 0.93)); plt.savefig('figures/fig2_temperature.png', dpi=160); plt.close()

# ---- Fig 3: retrofit effect per mode
fig, ax = plt.subplots(figsize=(8, 4.4)); y = np.arange(len(X))[::-1]
ax.axvline(0, color=LGRAY, lw=1)
ax.errorbar(X.effect_pct, y, xerr=[X.effect_pct - X.effect_ci_lo_pct, X.effect_ci_hi_pct - X.effect_pct], fmt='o',
            color=BLUE, ecolor=BLUE, capsize=3, label='temperature-adjusted (95% CI)')
ax.plot(X.naive_diff_pct, y, 'x', color=GRAY, ms=7, label='naive before/after difference')
for yi, (e, f0) in enumerate(zip(X.effect_pct, X.f_before_hz)):
    ax.text(e, y[yi] - 0.38, f'{e:+.2f}%', ha='center', fontsize=8.5, color=INK)
ax.set_yticks(y, [f'Mode {m[4:]} ({f:.2f} Hz)' for m, f in zip(X['mode'], X.f_before_hz)])
ax.set_xlabel('Change in natural frequency at the same temperature (%)'); ax.grid(axis='y', visible=False)
ax.set_ylim(-0.7, len(X) - 0.4); ax.set_xlim(-1.0, 2.5)
ax.legend(fontsize=8, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=2)
ax.set_title('What the retrofit changed: +1.6 to +2.1% in two modes, −0.3 to −0.7% in three', loc='left', fontsize=10.5, color=INK)
plt.tight_layout(); plt.savefig('figures/fig3_retrofit_effect.png', dpi=160); plt.close()
print('figures saved')
