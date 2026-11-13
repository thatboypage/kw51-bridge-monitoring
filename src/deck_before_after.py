"""Did the strengthening change the strains in the deck girders under trains?

The diagonal gauges record only before the works (1-7 May 2019); they are blank in October and December 2019.
The deck girder gauges (sgBD...) and the rail gauges (sgRA...) record on both sides of the works.
Raw deck strain ranges depend on the train (weight, length, which track), so each passage's deck strain range
is divided by the strain range of the rail it ran on (sgRAAB for track A, sgRABB for track B), a proxy for the
axle loads. Before: May 2019 up to the start of the works (15 May). After: from 27 September 2019.
"""
import glob
import numpy as np
import pandas as pd
import scipy.io as sio
from scipy.stats import mannwhitneyu

DECK = ['sgBD1011A', 'sgBD1415A', 'sgBD1718A', 'sgBD1718C', 'sgBD2324AB', 'sgBD2324AT', 'sgBD2324C', 'sgBD2728A']


def ranges(pattern='data/traindata/*/*.mat'):
    rows = []
    for f in sorted(glob.glob(pattern)):
        sg = sio.loadmat(f, squeeze_me=True, struct_as_record=False)['predat_sg']
        r = dict(file=f.split('/')[-1])
        for i, l in enumerate(sg.labels):
            x = sg.tdata[:, i]
            if np.all(np.isnan(x)):
                r[l] = np.nan
            else:
                x = x - np.nanmedian(x[:300])
                r[l] = (np.nanmax(x) - np.nanmin(x)) * 1e6        # microstrain
        rows.append(r)
    D = pd.DataFrame(rows)
    D['date'] = pd.to_datetime(D.file.str.extract(r'(\d{8})_')[0])
    D['period'] = np.select([(D.date >= '2019-05-01') & (D.date < '2019-05-15'), D.date >= '2019-09-27'],
                            ['before', 'after'], 'other')
    D['track'] = np.where(D.sgBD2728A > 32, 'B', 'A')         # gauge 27-28 reads ~50 for track B, ~15 for track A
    return D


def main():
    D = ranges()
    out = []
    for t, rail in (('A', 'sgRAAB'), ('B', 'sgRABB')):
        b = D[(D.track == t) & (D.period == 'before')]
        a = D[(D.track == t) & (D.period == 'after')]
        for g in DECK:
            rb, ra = (b[g] / b[rail]).dropna(), (a[g] / a[rail]).dropna()
            out.append(dict(track=t, gauge=g, n_before=len(rb), n_after=len(ra),
                            raw_change_pct=100 * (a[g].median() / b[g].median() - 1),
                            rail_change_pct=100 * (a[rail].median() / b[rail].median() - 1),
                            normalised_change_pct=100 * (ra.median() / rb.median() - 1),
                            p_value=mannwhitneyu(ra, rb).pvalue))
    T = pd.DataFrame(out)
    T.to_csv('results/deck_before_after.csv', index=False)
    print(T.round(3).to_string(index=False))
    print('diagonal gauges active after the works:', int(D[D.period == 'after'].sgDI20ALB.notna().sum()), 'of',
          int((D.period == 'after').sum()), 'passages')


if __name__ == '__main__':
    main()
