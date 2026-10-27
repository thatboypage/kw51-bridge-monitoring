"""Load the KW51 tracked modal data (Maes & Lombaert, 2021; Zenodo 10.5281/zenodo.3745914)."""
import os, datetime as dt, numpy as np, pandas as pd, scipy.io as sio

PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trackedmodes.mat')
RETROFIT_START = pd.Timestamp('2019-05-15')   # start of strengthening works (Maes & Lombaert)
RETROFIT_END = pd.Timestamp('2019-09-27')     # start of the "after" period


def _datenum(x):
    return dt.datetime.fromordinal(int(x)) + dt.timedelta(days=float(x) % 1) - dt.timedelta(days=366)


def load(path=PATH):
    m = sio.loadmat(path, squeeze_me=True, struct_as_record=False)['modes']
    t = pd.to_datetime([_datenum(x) for x in m.sdn]).round('min')
    F = pd.DataFrame(m.f, index=t, columns=[f'mode{i + 1}' for i in range(m.f.shape[1])])
    E = pd.DataFrame(m.env, index=t, columns=list(m.labels_env))
    period = np.where(t < RETROFIT_START, 'before', np.where(t < RETROFIT_END, 'during', 'after'))
    return F, E, pd.Series(period, index=t, name='period')
