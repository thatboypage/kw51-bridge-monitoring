import sys, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, 'src')
from fe_model import modes, SENSOR_X, L, N_SEG, build
from fe_update import pair, MEAS_SHAPE, F_BEFORE

BLUE, ORANGE, GRAY, LGRAY, INK, INK2, RED, GREEN = '#2a78d6', '#eb6834', '#8a8984', '#c9c8c2', '#0b0b0b', '#52514e', '#c43c3c', '#3f9b62'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': LGRAY, 'axes.labelcolor': INK2, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
                     'grid.color': '#ecebe7', 'grid.linewidth': 0.8, 'figure.facecolor': '#fcfcfb', 'axes.facecolor': '#fcfcfb'})
U = json.load(open('results/fe_update.json'))
b = U['before']
P = dict(h=b['arch_rise_m'], mass_per_m=b['mass_kg_per_m_per_side'], girder_factor=b['girder_stiffness_factor'], kappa=b['kappa_before'])

# ---- Fig 4: model geometry + matched vertical mode shapes with the three measured points
f, zg, sens, xs = modes(n=14, **P)
pr = pair(f, sens)
fig = plt.figure(figsize=(11, 6.2))
ax0 = fig.add_axes([0.06, 0.66, 0.9, 0.26])
xa = np.linspace(0, L, 400)
ax0.plot(xa, 4 * P['h'] * xa * (L - xa) / L ** 2, color=INK, lw=2)
ax0.plot([0, L], [0, 0], color=INK, lw=3)
pts = [(j * L / 18, (4 * P['h'] * (j * L / 18) * (L - j * L / 18) / L ** 2) if j % 2 == 0 else 0.0) for j in range(1, 18)]
for (x1, z1), (x2, z2) in zip(pts[:-1], pts[1:]):
    ax0.plot([x1, x2], [z1, z2], color=BLUE, lw=1.2)
ax0.plot(SENSOR_X, [0, 0, 0], 'v', color=ORANGE, ms=8, label='deck accelerometers (sections 11, 17, 23)')
ax0.plot([0], [0], '^', color=GRAY, ms=10); ax0.plot([L], [0], 'o', color=GRAY, ms=8)
ax0.set_aspect('equal'); ax0.set_xlim(-3, L + 3); ax0.set_ylim(-4, P['h'] + 3); ax0.axis('off')
ax0.legend(fontsize=8, frameon=False, loc='upper left', bbox_to_anchor=(0.0, 0.05))
ax0.set_title(f"In-plane model of one side: arch (rise {P['h']:.1f} m, tuned), tie girder and 16 diagonals (blue)",
              loc='left', fontsize=10, color=INK)
order = sorted(MEAS_SHAPE, key=lambda k: F_BEFORE[k])
for i, k in enumerate(order):
    ax = fig.add_axes([0.06 + i * 0.185, 0.06, 0.16, 0.40])
    fm, macv, j = pr[k]
    z = zg[:, j]; sc = np.interp(SENSOR_X, xs, z)
    meas = np.array(MEAS_SHAPE[k]); meas = meas * np.sign(meas @ sc) * np.linalg.norm(sc) / np.linalg.norm(meas)
    nz = np.max(np.abs(z))
    ax.plot(xs, z / nz, color=BLUE, lw=1.6)
    ax.plot(SENSOR_X, meas / nz, 'o', color=ORANGE, ms=6)
    ax.axhline(0, color=LGRAY, lw=1); ax.set_ylim(-1.3, 1.3); ax.set_yticks([]); ax.set_xticks([0, 57.5, 115], ['0', '57.5', '115 m'])
    ax.set_title(f'Mode {k}\nmeasured {F_BEFORE[k]:.2f} Hz, model {fm:.2f} Hz\nMAC {macv:.2f}', fontsize=8.5, color=INK)
fig.text(0.06, 0.585, 'Deck vertical mode shapes: model (line) and measured at the three instrumented sections (dots)',
         fontsize=10, color=INK)
plt.savefig('figures/fig4_fe_model_modes.png', dpi=160); plt.close()

# ---- Fig 5: measured vs modelled effect of the strengthening
T = pd.read_csv('results/fe_update.csv')
fig, ax = plt.subplots(figsize=(9, 4.4))
x = np.arange(len(T)); w = 0.26
ax.bar(x - w, T.measured_change_pct, w, color=INK, label='measured')
ax.bar(x, T.model_both_pct, w, color=BLUE,
       label=f"model: diagonals {100 * (U['after']['kappa_after'] / b['kappa_before'] - 1):.0f}% stiffer + {U['after']['added_mass_kg_per_side'] / 1000:.0f} t steel per side")
ax.bar(x + w, T.model_stiffness_only_pct, w, color=LGRAY, label='model: stiffer diagonals only')
ax.axhline(0, color=GRAY, lw=1)
ax.set_xticks(x, [f'Mode {m}' for m in T['mode']]); ax.set_ylabel('Frequency change after strengthening (%)')
ax.grid(axis='x', visible=False); ax.set_ylim(-0.5, 3.1); ax.legend(fontsize=8, frameon=False, loc='upper left')
ax.set_title('Stiffer diagonal connections raise the higher vertical modes; only added steel lowers mode 5',
             loc='left', fontsize=10.5, color=INK)
fig.text(0.01, 0.01, 'Modes 5, 6, 13: temperature-adjusted effects. Modes 10, 12: before/after means (tracked less often).',
         fontsize=7.5, color=INK2)
plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig('figures/fig5_fe_retrofit.png', dpi=160); plt.close()
print('saved')
