"""Fatigue assessment of the KW51 diagonals from measured train-passage strains.

Data: strain gauges sgDI20ALB, sgDI20ALL, sgDI23ALB, sgDI23ALL on diagonals 20 and 23 (side A), recorded
during train passages. In the published data they are active only before the strengthening works
(early May 2019 here); earlier months can be added by placing more traindata folders in data/traindata/.

Method (nominal-stress approach, EN 1993-1-9):
  1. stress = E * strain, E = 210 GPa
  2. rainflow counting of each passage (ASTM E1049 three-point method)
  3. S-N curve of a detail category dsC (stress range at 2 million cycles):
       N = 2e6 (dsC/ds)^3            for ds >= dsD = 0.737 dsC   (constant-amplitude fatigue limit)
       N = 5e6 (dsD/ds)^5            for dsL <= ds < dsD
       no damage                     for ds <  dsL = 0.549 dsD   (cut-off limit)
  4. Miner's rule: damage D = sum(n_i / N_i); failure expected at D = 1.
The gauges sit on the diagonal members, not at the weld toes of the connections, so the measured stress
is a nominal member stress. The local stress at a welded connection can be several times higher; the
analysis therefore also asks how large a stress-concentration factor would make the measured loading
damaging within the bridge's life.
"""
import sys, glob, json
import numpy as np
import pandas as pd
import scipy.io as sio

E = 210e9
GAUGES = ['sgDI20ALB', 'sgDI20ALL', 'sgDI23ALB', 'sgDI23ALL']


def rainflow(x):
    """ASTM E1049 rainflow counting. Returns arrays of ranges and counts (0.5 or 1)."""
    x = np.asarray(x, float)
    # turning points
    d = np.diff(x)
    keep = np.r_[True, d[1:] * d[:-1] < 0, True] if len(d) > 1 else np.array([True, True])
    tp = x[np.r_[0, np.where(keep[1:-1])[0] + 1, len(x) - 1]] if len(x) > 2 else x
    stack, ranges, counts = [], [], []
    for p in tp:
        stack.append(p)
        while len(stack) >= 3:
            X = abs(stack[-1] - stack[-2]); Y = abs(stack[-2] - stack[-3])
            if X < Y:
                break
            if len(stack) == 3:
                ranges.append(Y); counts.append(0.5); stack.pop(0)
            else:
                ranges.append(Y); counts.append(1.0)
                last = stack.pop(); stack.pop(); stack.pop(); stack.append(last)
    for a, b in zip(stack[:-1], stack[1:]):
        ranges.append(abs(b - a)); counts.append(0.5)
    return np.array(ranges), np.array(counts)


def damage(ranges_MPa, counts, dsC):
    dsD, dsL = 0.737 * dsC, 0.737 * dsC * 0.549
    r, n = np.asarray(ranges_MPa), np.asarray(counts)
    N = np.full(r.shape, np.inf)
    hi = r >= dsD; mid = (r >= dsL) & ~hi
    N[hi] = 2e6 * (dsC / r[hi]) ** 3
    N[mid] = 5e6 * (dsD / r[mid]) ** 5
    return float(np.sum(n / N))


LIFETIME_PASSAGES = (1e6, 2e6, 4e6)   # e.g. 2 million = about 110 trains a day for 50 years


def mean_damage(rf, cat, scf=1.0):
    return float(np.mean([damage(r * scf, n, cat) for r, n in rf]))


def scf_for(rf, target, cat):
    """Bisection for the stress-concentration factor that makes the mean damage per passage equal target."""
    lo, hi = 1.0, 30.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mean_damage(rf, cat, mid) < target else (lo, mid)
    return (lo + hi) / 2


def load_passages(pattern='data/traindata/*/*.mat'):
    rows = []
    for f in sorted(glob.glob(pattern)):
        sg = sio.loadmat(f, squeeze_me=True, struct_as_record=False)['predat_sg']
        labels = list(sg.labels)
        if not all(g in labels and not np.all(np.isnan(sg.tdata[:, labels.index(g)])) for g in GAUGES):
            continue
        rows.append(dict(file=f.split('/')[-1], fs=float(sg.fs),
                         stress={g: E * (sg.tdata[:, labels.index(g)] - np.nanmedian(sg.tdata[:300, labels.index(g)])) / 1e6
                                 for g in GAUGES}))
    return rows


def main():
    P = load_passages()
    print(len(P), 'passages with diagonal strain data')
    recs, allr = [], {g: ([], []) for g in GAUGES}
    for p in P:
        for g in GAUGES:
            s = p['stress'][g]
            s = s[~np.isnan(s)]
            r, n = rainflow(s)
            allr[g][0].extend(r); allr[g][1].extend(n)
            recs.append(dict(file=p['file'], gauge=g, max_range_MPa=float(r.max()) if r.size else 0.0,
                             cycles_over_5MPa=float(n[r > 5].sum()),
                             **{f'D_cat{c}': damage(r, n, c) for c in (36, 50, 71, 90)}))
    R = pd.DataFrame(recs)
    R.to_csv('results/fatigue_passages.csv', index=False)
    summ = {}
    for g in GAUGES:
        r, n = np.array(allr[g][0]), np.array(allr[g][1])
        d = R[R.gauge == g]
        summ[g] = dict(passages=int(len(d)), max_range_MPa=float(d.max_range_MPa.max()),
                       median_max_range_MPa=float(d.max_range_MPa.median()),
                       mean_damage_per_passage={c: float(d[f'D_cat{c}'].mean()) for c in (36, 50, 71, 90)})
        # stress-concentration factor at which the average measured passage, repeated over a given number of
        # lifetime passages, would reach Miner damage D = 1 (traffic volume is not published, so it is a parameter)
        rf = [rainflow(p['stress'][g][~np.isnan(p['stress'][g])]) for p in P]
        summ[g]['scf_for_D1'] = {f'{int(nt / 1e6)}M_passages_cat{cat}': scf_for(rf, 1 / nt, cat)
                                 for nt in LIFETIME_PASSAGES for cat in (71, 90)}
    json.dump(summ, open('results/fatigue_summary.json', 'w'), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
