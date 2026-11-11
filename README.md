# Separating temperature from structural change on a real railway bridge (KW51)

**Result:** on 15 months of measured data from the KW51 steel railway bridge in Leuven, Belgium, a temperature model learned only from the pre-retrofit period removes most of the seasonal swing in the bridge's natural frequencies. With temperature removed, the effect of the 2019 strengthening works becomes measurable at a fixed temperature: **+2.11% for mode 6 and +1.56% for mode 13, and −0.29% to −0.75% for modes 3, 5 and 9** (95% intervals within ±0.01–0.08 percentage points). On a simple alarm chart, the compensation **roughly halves the alarm band** for modes 6, 9 and 13. For mode 13 it turns a chart that **never flags** the post-retrofit change into one that flags **98% of post-retrofit days**. A finite element model of the arch, girder and diagonals then shows what the strengthening did structurally: the pattern of changes across the vertical modes matches **7–8% stiffer diagonal connections plus 6–13 t of added steel per side**, and that conclusion holds under every tested variant of the unpublished geometry.

Plain-English write-up: [The alarm that never rang: separating temperature from real change on a railway bridge](https://medium.com/@richardolanite/the-alarm-that-never-rang-separating-temperature-from-real-change-on-a-railway-bridge-d7d7e2989daa) (Medium).

Data: K. Maes and G. Lombaert, *Monitoring railway bridge KW51 before, during, and after retrofitting*, ASCE Journal of Bridge Engineering 26(3), 2021, [doi:10.1061/(ASCE)BE.1943-5592.0001668](https://ascelibrary.com/doi/10.1061/%28ASCE%29BE.1943-5592.0001668); dataset [doi:10.5281/zenodo.3745914](https://zenodo.org/record/3745914). This repository uses only the `trackedmodes` file (natural frequencies and environmental data, hourly). The data are not redistributed here; see *Reproduce*.

## The problem

KW51 is a steel bowstring arch railway bridge on the line between Leuven and Brussels. KU Leuven monitored it from October 2018 to January 2020. During monitoring, damage was found at the connections between the diagonals and the deck and arches, and the bridge was strengthened (works from **15 May 2019**; the "after" period starts **27 September 2019**).

A change in stiffness shows up as a change in natural frequency, which is the basis of vibration-based structural health monitoring. But temperature moves the frequencies too: steel softens as it warms, and when the bridge freezes, the frequencies jump. These environmental swings can be as large as the changes caused by damage or repair. Before anyone can say what a repair did, or whether damage is developing, temperature has to be separated out.

## Approach

1. **Data.** Hourly natural frequencies of 14 tracked modes and 11 environmental channels. I use the five modes tracked at least 80% of the time in every period (modes 3, 5, 6, 9 and 13, from 1.9 to 6.3 Hz), and the steel temperature measured on the deck (`tBD31A`).
2. **A model of normal behaviour, learned before the retrofit only.** For each mode: frequency = a + b·T + c·max(0, T₀ − T). The first two terms are the usual linear softening with temperature. The third captures the extra stiffening below a knot T₀ (freezing). The model and T₀ were chosen by **blocked cross-validation on the pre-retrofit months** (each whole month held out in turn), so nothing after the retrofit influenced the choice. The freezing term was selected for all five modes (T₀ = 1–1.5 °C) and cut the cross-validated error by up to a third (mode 13: 0.038 → 0.026 Hz).
3. **Residuals.** Residual = measured − predicted frequency. Pre-retrofit residuals are cross-validated; during and after the retrofit, the model fitted on the full pre-retrofit period is applied unchanged.
4. **Alarm chart.** Daily mean residuals, with limits at ±3 standard deviations of the pre-retrofit days, compared with the same chart on the raw frequencies.
5. **Retrofit effect.** The mean post-retrofit residual is the change in frequency at the same temperature. Its 95% interval comes from a weekly block bootstrap, because consecutive hours are correlated. It is compared with the naive before/after difference, which ignores temperature.

## Results

![Temperature behaviour](figures/fig2_temperature.png)

**Temperature.** Above about 1 °C, frequencies fall slowly as the steel warms (mode 13: −0.06% per °C). Below it, they rise sharply: in the January 2019 cold spell, mode 13 rose by about 4%. After the retrofit, the whole temperature curve shifts.

![Alarm chart, mode 13](figures/fig1_control_chart_mode13.png)

**Alarm charts** (226 pre-retrofit days with data):

| Mode | Alarm band, raw (Hz) | Alarm band, compensated (Hz) | False-alarm days before, raw → compensated | First alarm after works began, raw → compensated | Post-retrofit days flagged, raw → compensated |
|---|---|---|---|---|---|
| 3 | ±0.020 | ±0.016 | 4 → 4 | 28 May → 24 May | 2% → 5% |
| 5 | ±0.015 | ±0.012 | 3 → 0 | 27 May → 15 May | 5% → 12% |
| 6 | ±0.020 | ±0.010 | 7 → 3 | 28 Jun → 2 Jun | 98% → 98% |
| 9 | ±0.011 | ±0.005 | 6 → 3 | 17 May → 15 May | 98% → 98% |
| 13 | ±0.117 | ±0.065 | 7 → 4 | never → 22 Jun | 0% → 98% |

![Retrofit effect](figures/fig3_retrofit_effect.png)

**Retrofit effect at the same temperature:**

| Mode | Frequency before (Hz) | Temperature-adjusted change | 95% interval | Naive before/after difference |
|---|---|---|---|---|
| 3 | 1.892 | −0.47% | −0.55 to −0.40% | −0.52% |
| 5 | 2.580 | −0.29% | −0.32 to −0.26% | −0.32% |
| 6 | 2.925 | **+2.11%** | +2.10 to +2.13% | +2.05% |
| 9 | 4.109 | −0.75% | −0.75 to −0.74% | −0.77% |
| 13 | 6.327 | **+1.56%** | +1.51 to +1.61% | +1.43% |

**Why adjust, if the naive numbers look similar?** Over the full periods, the average temperatures before and after the retrofit happened to be close (8.1 and 9.1 °C), so the naive comparison is only slightly off. It goes wrong as soon as the comparison windows fall in different seasons. Comparing the winter before (Dec–Feb, 5.8 °C) with the six weeks after the works (12.9 °C), the naive estimate for mode 13 drops to +1.10%, while the adjusted estimate stays at +1.64%. Across three different comparison windows, the adjusted mode 13 effect stays within +1.56 to +1.68%; the naive one ranges from +1.10 to +1.65% (`results/window_sensitivity.csv`).

## What the results mean

- **Temperature compensation is what makes monitoring usable.** On raw frequencies, normal winter behaviour sets the alarm limits so wide that real changes can pass unnoticed, as mode 13 shows. Learning normal behaviour first, then watching what is left over, roughly halves the alarm band and makes the retrofit stand out.
- **The retrofit changed different modes in different directions.** Two modes stiffened by 1.6–2.1%, and three lost 0.3–0.75%. Strengthening both stiffens connections and adds steel, and each mode is sensitive to these in different proportions. The analysis measures the net change in each mode; the finite element model below tests what caused it.
- **Removing a confounder gives an effect estimate that does not depend on when you look.** The temperature-adjusted effect is stable across comparison windows; the naive one is not. This is a simple case of estimating an intervention's effect in the presence of a confounding variable.

## What the strengthening changed structurally: a finite element model

The frequency changes have a clear pattern across all five global vertical modes. The first symmetric mode (mode 5) dropped by 0.29%; every higher vertical mode rose by 1.5–2.1% (modes 6, 10, 12 and 13; modes 10 and 12 are before/after means, since they were tracked too rarely to adjust for temperature). The works strengthened the connections of the diagonals to the deck and the arches (dataset description). To test whether that explains the pattern, I built an in-plane finite element model of one side of the bridge (`src/fe_model.py`): a parabolic box arch, the T-girder carrying the deck, ballast and track mass, and 16 inclined diagonals.

- **Geometry and sections** are taken from the published description (arXiv:2408.03002): 115 m long, box arch 0.86 × 1.30 m (t = 45 mm), box diagonals 0.345 × 0.35 m (t = 16 mm), T-girder 1.235 m deep, steel E = 210 GPa.
- **Not published openly, so tuned or assumed:** the arch rise, the diagonal layout, the girder's effective bending stiffness (deck plate included), the mass per metre (kept within 6–10 t/m per side, from the section sizes), and the diagonals' effective axial stiffness, which stands for how stiff their connections are.
- **Mode identification:** the dataset includes measured mode shapes at three deck sections (after the works only). Each measured vertical mode is paired with the model mode that matches its shape (MAC 0.96–1.00).

![Model and mode shapes](figures/fig4_fe_model_modes.png)

Before the works, the model reproduces the five vertical frequencies to within 6–18% (mean 11%), comparable to a published 3-D Abaqus model of this bridge (93% average accuracy). Keeping that model fixed, I then fitted just two parameters to the five measured changes: the change in diagonal stiffness, and steel mass added at the 16 connections.

![Retrofit effect, model vs measured](figures/fig5_fe_retrofit.png)

| Mode | Measured change | Model: stiffer diagonals + added steel | Model: stiffer diagonals only |
|---|---|---|---|
| 5 (1st symmetric) | −0.29% | −0.27% | +0.22% |
| 6 (1st antisymmetric) | +2.11% | +2.22% | +2.22% |
| 10 | +2.00% | +2.22% | +2.16% |
| 12 | +2.07% | +1.73% | +1.72% |
| 13 | +1.56% | +1.48% | +1.48% |

- **Stiffer diagonal connections explain the rise of the higher modes.** These modes bend the arch and girder against each other, which loads the diagonals; the first symmetric mode moves arch and girder together and barely uses them.
- **Only added steel explains the drop in mode 5.** Stiffness alone raises it (+0.22%); mass alone cannot raise the others.
- **The inference holds when the unknowns change.** Refitting with the arch rise fixed at 15, 19 and 23 m and with the opposite diagonal layout always gives a **7–8% increase in diagonal stiffness** (6.8–8.0%) and **6–13 t of added steel per side**, with the measured changes reproduced to within 0.2–0.3 percentage points (`results/fe_sensitivity.csv`).
- **What the model cannot tell:** how stiff the connections were in absolute terms (the fitted value ranges from 0.53 to 0.98 of a rigid connection across variants), or exactly which connections were strengthened. The lateral and torsional modes (3 and 9) need a 3-D model and are not covered.

## Limitations (found, not hidden)

- **Freezing is only partly captured.** A single knot cannot follow the cold spell of January 2019, when the bridge stayed stiff for several days as the temperature rose again (possibly because frozen components lag behind the steel temperature). The remaining spike causes most of the 3–4 false-alarm days on the compensated chart. A model with memory (for example, a lagged or hysteretic freezing term) is the natural next step.
- **Summer temperatures during the works (up to 38 °C) exceed the pre-retrofit range (up to 26 °C),** so residuals during the works partly rely on extrapolation. The retrofit effect is measured on the after period (0.6–22.7 °C), which is inside the training range.
- **The confidence intervals cover measurement noise, not model error.** For the noisier modes 3 and 5, the adjusted estimate moves by up to 0.18 percentage points between comparison windows, more than the bootstrap interval suggests.
- **One temperature sensor and five modes.** Other environmental channels (humidity, solar radiation, wind) and the other nine modes were not used.
- **Not a new result for this bridge.** KW51 is an established benchmark, and temperature effects and retrofit detection on it have been studied by its authors and others. This project reproduces that kind of analysis independently and adds the temperature-adjusted, per-mode effect sizes with uncertainty.

## Reproduce

1. Download `trackedmodes.zip` from [Zenodo record 3745914](https://zenodo.org/record/3745914) (about 13 MB; the other files are raw recordings and are not needed) and place `trackedmodes.mat` in `data/`.
2. Run from the repository root (a few seconds):

```
pip install numpy scipy pandas matplotlib
python src/analysis.py        # temperature models, residuals, retrofit effect, window sensitivity
python src/control_chart.py   # raw vs compensated alarm charts
python src/figures.py
python src/fe_update.py       # finite element model: fit before, then the strengthening (about 10 min)
python src/fe_sensitivity.py  # same fit under other arch rises and diagonal layout (about 20 min)
python src/fe_figures.py
```

| File | Purpose |
|---|---|
| `src/load.py` | Reads `trackedmodes.mat`, converts timestamps, labels the before / during / after periods |
| `src/analysis.py` | Model choice by blocked cross-validation, residuals, retrofit effect with block bootstrap |
| `src/control_chart.py` | Daily alarm charts on raw frequencies and residuals |
| `src/figures.py` | Figures 1–3 |
| `src/fe_model.py` | In-plane finite element model (frame and truss elements, modal analysis) |
| `src/fe_update.py`, `src/fe_sensitivity.py` | Model updating before and after strengthening; sensitivity to unpublished geometry |
| `src/fe_figures.py` | Figures 4–5 |

## Author

Richard Olanite · Berm Engineering and Consulting Ltd · [github.com/thatboypage](https://github.com/thatboypage)
