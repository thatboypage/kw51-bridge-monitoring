"""In-plane finite element model of one side of KW51 (arch + tie girder + inclined diagonals).

Purpose: test whether the measured effect of the 2019 strengthening of the diagonal connections can be
explained by (a) stiffer diagonals and (b) added steel mass, using the vertical modes.

Geometry and sections (published, arXiv:2408.03002, Table 1): 115 m long, 12.4 m wide; box arch
0.86 x 1.30 m, t = 45 mm; box diagonals 0.345 x 0.35 m, t = 16 mm; T-girder 0.6 m wide, 1.235 m deep,
t = 80 mm; steel E = 210 GPa, rho = 7750 kg/m3; 33 cross beams; 32 inclined diagonals (16 per side).
Not published openly, and therefore assumed or tuned (stated in the README):
  - the arch rise h (tuned), a parabolic arch shape, and a Warren (zigzag) diagonal layout;
  - the girder's effective bending stiffness, including the deck plate (tuned through a factor);
  - the distributed mass per side: girder, deck, ballast, track (tuned);
  - the diagonals' effective axial stiffness kappa * EA, which represents connection flexibility (tuned).
Supports: pinned at one girder end, roller at the other. 2-D Euler-Bernoulli frame elements for arch and
girder, axial (truss) elements for the diagonals.
"""
import numpy as np
from scipy.linalg import eigh

E, RHO, L = 210e9, 7750.0, 115.0


def box(b, h, t):
    A = b * h - (b - 2 * t) * (h - 2 * t)
    I = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12
    return A, I


A_ARCH, I_ARCH = box(0.86, 1.30, 0.045)
A_DIAG, _ = box(0.345, 0.35, 0.016)
# T girder: flange 0.6 x 0.08 + web (1.235-0.08) x 0.08
_af, _aw = 0.6 * 0.08, (1.235 - 0.08) * 0.08
_yc = (_af * (1.235 - 0.04) + _aw * (1.235 - 0.08) / 2) / (_af + _aw)
I_GIRDER = (0.6 * 0.08 ** 3 / 12 + _af * (1.235 - 0.04 - _yc) ** 2 +
            0.08 * (1.235 - 0.08) ** 3 / 12 + _aw * ((1.235 - 0.08) / 2 - _yc) ** 2)
A_GIRDER = _af + _aw

N_SEG = 72                     # girder / arch segments
SENSOR_X = np.array([11, 17, 23]) * L / 34   # cross-beam sections 11, 17, 23 of 33 (equal spacing)


def frame_el(x1, z1, x2, z2, EA, EI, m):
    dx, dz = x2 - x1, z2 - z1
    l = np.hypot(dx, dz); c, s = dx / l, dz / l
    k = np.zeros((6, 6))
    a, b1, b2, b3 = EA / l, 12 * EI / l ** 3, 6 * EI / l ** 2, EI / l
    k[np.ix_([0, 3], [0, 3])] = a * np.array([[1, -1], [-1, 1]])
    idx = [1, 2, 4, 5]
    k[np.ix_(idx, idx)] = np.array([[b1, b2, -b1, b2], [b2, 4 * b3, -b2, 2 * b3],
                                    [-b1, -b2, b1, -b2], [b2, 2 * b3, -b2, 4 * b3]])
    mm = np.zeros((6, 6))
    mm[np.ix_([0, 3], [0, 3])] = m * l / 6 * np.array([[2, 1], [1, 2]])
    mm[np.ix_(idx, idx)] = m * l / 420 * np.array([[156, 22 * l, 54, -13 * l], [22 * l, 4 * l * l, 13 * l, -3 * l * l],
                                                  [54, 13 * l, 156, -22 * l], [-13 * l, -3 * l * l, -22 * l, 4 * l * l]])
    T = np.zeros((6, 6))
    R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    T[:3, :3] = R; T[3:, 3:] = R
    return T.T @ k @ T, T.T @ mm @ T


def truss_el(x1, z1, x2, z2, EA, m):
    dx, dz = x2 - x1, z2 - z1
    l = np.hypot(dx, dz); c, s = dx / l, dz / l
    v = np.array([-c, -s, 0, c, s, 0])
    k = EA / l * np.outer(v, v)
    mm = np.zeros((6, 6))
    for i in [0, 1, 3, 4]:
        mm[i, i] = m * l / 2
    return k, mm


def build(h=16.0, mass_per_m=8000.0, girder_factor=3.0, kappa=1.0, added_mass=0.0, layout='warren'):
    """Return K, M, girder node x and girder vertical-DOF indices."""
    xs = np.linspace(0, L, N_SEG + 1)
    nodes = [(x, 0.0) for x in xs]                         # girder nodes 0..N_SEG
    arch_id = {0: 0, N_SEG: N_SEG}
    for i in range(1, N_SEG):
        arch_id[i] = len(nodes)
        nodes.append((xs[i], 4 * h * xs[i] * (L - xs[i]) / L ** 2))
    nd = len(nodes) * 3
    K, M = np.zeros((nd, nd)), np.zeros((nd, nd))

    def add(ke, me, a, b):
        dofs = [3 * a, 3 * a + 1, 3 * a + 2, 3 * b, 3 * b + 1, 3 * b + 2]
        K[np.ix_(dofs, dofs)] += ke; M[np.ix_(dofs, dofs)] += me

    for i in range(N_SEG):                                 # girder: carries deck, ballast, track
        add(*frame_el(*nodes[i], *nodes[i + 1], E * A_GIRDER, girder_factor * E * I_GIRDER, mass_per_m), i, i + 1)
    for i in range(N_SEG):                                 # arch
        a, b = arch_id[i], arch_id[i + 1]
        add(*frame_el(*nodes[a], *nodes[b], E * A_ARCH, E * I_ARCH, RHO * A_ARCH), a, b)
    # diagonals: 16 per side, ends at 17 points j = 1..17 at x = j L / 18, alternating girder / arch
    pts = []
    for j in range(1, 18):
        i = int(round(j * N_SEG / 18))
        on_arch = (j % 2 == 0) if layout == 'warren' else (j % 2 == 1)
        pts.append(arch_id[i] if on_arch else i)
    conn = []
    for a, b in zip(pts[:-1], pts[1:]):
        add(*truss_el(*nodes[a], *nodes[b], kappa * E * A_DIAG, RHO * A_DIAG), a, b)
        conn += [a, b]
    if added_mass:                                         # strengthening plates, lumped at the connections
        per = added_mass / len(conn)
        for n in conn:
            M[3 * n, 3 * n] += per; M[3 * n + 1, 3 * n + 1] += per
    fixed = [0, 1, 3 * N_SEG + 1]                          # pin at x = 0, roller at x = L
    free = np.setdiff1d(np.arange(nd), fixed)
    return K, M, free, xs


def modes(n=12, **kw):
    K, M, free, xs = build(**kw)
    w2, V = eigh(K[np.ix_(free, free)], M[np.ix_(free, free)], subset_by_index=[0, n - 1])
    full = np.zeros((K.shape[0], n)); full[free] = V
    zg = full[1:3 * (N_SEG + 1):3]                         # girder vertical displacement
    f = np.sqrt(np.clip(w2, 0, None)) / (2 * np.pi)
    sensor = np.array([np.interp(SENSOR_X, xs, zg[:, k]) for k in range(n)])
    return f, zg, sensor, xs


def mac(a, b):
    return float(np.abs(a @ b) ** 2 / ((a @ a) * (b @ b)))
