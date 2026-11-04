#!/usr/bin/env python3
"""Huspris-ECM enligt Riksbankens bostadsutredning (2011) / Riksgälden (Bjellerup & Majtorp 2019).

Långsikt (dynamisk OLS, ±4 leads/lags av Δ förklarande):
    hp*_t = α + β_y·di_t − β_r·ir_t − γ·D_LTV
    hp = ln(FASTPI småhus / KPIF), di = ln(real disp. inkomst, 4 kv), ir = real ränta efter skatt
    ir = 0,7·(hushållens snittränta MFI, utestående) − KPIF-inflation (å/å)
    D_LTV = 1 fr.o.m. 2010K4 (bolånetaket)
Kortsikt (general-to-specific från 4 laggar, behåll p<0,05):
    Δhp_t = c + λ·(hp − hp*)_{t-1} + Σ a_i Δhp_{t-i} + Σ b_i Δir_{t-i} + Σ d_i Δdi_{t-i}
Jämförelse Riksgälden 1985–2018: β_y = 1,37, β_r = 0,06, γ = 0,07, λ ≈ −0,06."""
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import coint

warnings.filterwarnings("ignore")
BAS = Path(__file__).resolve().parent
D, G = BAS / "data", BAS / "grafer"
les = lambda n: pd.read_csv(D / n, index_col=0, parse_dates=True)
Q = lambda s: s.resample("QE").mean()

kpif = Q(les("kpif.csv")["kpif"])
d = pd.DataFrame({
    "hp": np.log(les("fastpi_smahus.csv")["riket"] / kpif),
    "di": np.log(les("disponibel_inkomst.csv")["disp_real"].rolling(4).sum()),
    "i_nom": Q(les("hushall_ranta_utest_lang.csv")["hush_utest_mfi"]),
    "pi": np.log(kpif).diff(4) * 100,
}).sort_index()
hp_raw = d["hp"].dropna()
d["hp"] = hp_raw - STL(hp_raw, period=4, robust=True).fit().seasonal     # säsongrensning (Riksgälden: SA-data)
d["ir"] = 0.7 * d["i_nom"] - d["pi"]                  # bakåtblickande inflation (Riksgäldens definition)
d["ir_mal"] = 0.7 * d["i_nom"] - 2.0                  # förankrade förväntningar = inflationsmålet
d["D_LTV"] = (d.index >= "2010-10-01").astype(float)
d["D_AMORT"] = (d.index >= "2016-04-01").astype(float)       # amorteringskrav 1 (skärpt 2018K1)
d = d.loc["1996":].dropna(subset=["hp", "di", "ir"])
R = {}


def dols(d, X, K=4):
    Z = d[X].copy()
    for x in [c for c in X if not c.startswith("D_")]:
        for k in range(-K, K + 1):
            Z[f"d{x}_{k}"] = d[x].diff().shift(k)
    df = pd.concat([d["hp"], Z], axis=1).dropna()
    m = sm.OLS(df["hp"], sm.add_constant(df.drop(columns="hp"))).fit(cov_type="HAC", cov_kwds={"maxlags": 8})
    return m, df


res = {}
spec = {"A_riksgalden_t.o.m._2019": (["di", "ir", "D_LTV"], "2019-12-31"),
        "B_riksgalden_hela_urvalet": (["di", "ir", "D_LTV"], None),
        "C_inflationsmal_hela_urvalet": (["di", "ir_mal", "D_LTV"], None)}
for namn, (X, slut) in spec.items():
    dd = d.loc[:slut] if slut else d
    m, df = dols(dd, X)
    lr = {k: {"b": round(float(m.params[k]), 3), "t": round(float(m.tvalues[k]), 2)} for k in ["const"] + X}
    hpstar = m.params["const"] + sum(m.params[x] * d[x] for x in X)
    gap = d["hp"] - hpstar
    eg = coint(dd["hp"], dd[[x for x in X if not x.startswith("D_")]].dropna().reindex(dd.index), trend="c")[1] if False else \
        coint(*(lambda z: (z["hp"], z[[x for x in X if not x.startswith("D_")]]))(dd[["hp"] + X].dropna()))[1]
    res[namn] = {"period": f"{df.index.min():%Y-%m}–{df.index.max():%Y-%m}", "n": int(m.nobs), "langsikt": lr,
                 "engle_granger_p": round(float(eg), 3), "gap_senast_pct": round(float(gap.dropna().iloc[-1] * 100), 1),
                 "gap_kvartal": gap.dropna().index[-1].strftime("%Y-%m"), "_gap": gap}
R["langsikt"] = {k: {kk: vv for kk, vv in v.items() if kk != "_gap"} for k, v in res.items()}

# Kortsikt: general-to-specific
HUVUD = "C_inflationsmal_hela_urvalet"
gap = res[HUVUD]["_gap"]
cand = {"ecm_l1": gap.shift(1)}
for i in range(1, 5):
    cand[f"dhp_l{i}"] = d["hp"].diff().shift(i)
    cand[f"dir_l{i}"] = d["ir_mal"].diff().shift(i)
    cand[f"ddi_l{i}"] = d["di"].diff().shift(i)
X = pd.DataFrame(cand)
while True:
    df = pd.concat([d["hp"].diff().rename("dhp"), X], axis=1).dropna()
    m = sm.OLS(df["dhp"], sm.add_constant(df.drop(columns="dhp"))).fit()
    p = m.pvalues.drop(["const", "ecm_l1"])
    if p.empty or p.max() < 0.05:
        break
    X = X.drop(columns=p.idxmax())
from statsmodels.stats.diagnostic import acorr_breusch_godfrey
R["kortsikt"] = {"langsiktsvariant": HUVUD, "period": f"{df.index.min():%Y-%m}–{df.index.max():%Y-%m}", "n": int(m.nobs), "r2_adj": round(m.rsquared_adj, 2),
                 "koef": {k: {"b": round(float(v), 4), "t": round(float(m.tvalues[k]), 2)} for k, v in m.params.items()},
                 "breusch_godfrey_p": round(float(acorr_breusch_godfrey(m, nlags=4)[1]), 3),
                 "andel_korrigerad_inom_1ar": round(1 - (1 + float(m.params["ecm_l1"])) ** 4, 2)}
R["jamforelse_riksgalden_2019"] = {"beta_y": 1.37, "beta_r": 0.06, "LTV": -0.07, "lambda": -0.06, "period": "1985K4–2018K3"}

fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
hpstar = d["hp"] - gap
ax[0].plot(d.index, d["hp"], label="Reala småhuspriser (ln)"); ax[0].plot(hpstar.index, hpstar, label="Skattat jämviktspris")
ax[0].legend(fontsize=8); ax[0].grid(alpha=.3); ax[0].set_title("Huspris-ECM à la Riksbanken (2011) / Riksgälden (2019)")
ax[1].bar(gap.index, gap * 100, width=60, color=np.where(gap > 0, "#c0504d", "#4f81bd"))
ax[1].set_ylabel("% över(+)/under(−) jämvikt"); ax[1].grid(alpha=.3)
fig.tight_layout(); fig.savefig(G / "6_huspris_ecm.png", dpi=130)
(D / "prismodell_resultat.json").write_text(json.dumps(R, ensure_ascii=False, indent=1))
print(json.dumps(R, ensure_ascii=False, indent=1))
