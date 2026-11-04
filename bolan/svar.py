#!/usr/bin/env python3
"""Replikering av Riksbankens SVAR över delperioder (Stockhammar, Strid & Tornese 2022, EK nr 9).

Bayesiansk VAR(4), kvartal. Endogena variabler i Cholesky-ordning:
  KPIF-inflation (å/å), ln konsumtion, ln BNP, ln reala hushållsskulder, ln reala huspriser,
  styrränta, ln real växelkurs (KIX·HICP/KPIF)
=> en penningpolitisk störning får påverka endast växelkursen samma kvartal.
Omvärlden (euroområdet som proxy för KIX): BNP, HICP-inflation, 3-månadersränta, som exogena
variabler (laggar 0–2) => blockexogenitet, inga effekter från Sverige på omvärlden.
Prior: Minnesota/normal-inverse-Wishart via dummyobservationer (Bańbura m.fl. 2010), λ=0,2.
Delperioder: slut 2009K4…2019K4 (expanderande) och start 1997K1…2006K1 (krympande), slut 2019K4.
Mått: max (absolut) effekt på konsumtionen av medianresponsen, styrräntan +1 pe på kvartal 0.
Tillägg: rullande 14-årsfönster t.o.m. 2026K2 med pandemidummies."""
import json
import os
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import invwishart
from statsmodels.tsa.seasonal import STL

warnings.filterwarnings("ignore")
BAS = Path(__file__).resolve().parent
D, G = BAS / "data", BAS / "grafer"
les = lambda n: pd.read_csv(D / n, index_col=0, parse_dates=True)
Q = lambda s: s.resample("QE").mean()
rng = np.random.default_rng(1)
SUF = os.environ.get("SUF", "")
import os
P, H, NDRAW, LAM = int(os.environ.get("P", 4)), 20, int(os.environ.get("NDRAW", 400)), float(os.environ.get("LAM", 0.2))


def sa(s):
    s = s.dropna()
    return s - STL(s, period=4, robust=True).fit().seasonal


# ---------- Data ----------
sv = les("svar_data.csv")
kpif = Q(les("kpif.csv")["kpif"])
fp = les("fastpi_smahus.csv")["riket"]
inc = les("disponibel_inkomst.csv")["disp_nom"].rolling(4).sum()
endog = pd.DataFrame({
    "infl": np.log(kpif).diff(4) * 100,
    "kons": np.log(sv["kons"]) * 100,
    "bnp": np.log(sv["bnp"]) * 100,
    "skuld": np.log(sv["hush_skuld"] / kpif) * 100,
    "huspris": sa(np.log(fp / kpif) * 100),
    "styr": sv["styr"],
    "vxl": np.log(sv["kix"] * sv["ea_hicp"] / kpif) * 100,
})
hicp_sa = sa(np.log(sv["ea_hicp"]) * 100)
exo_bas = pd.DataFrame({"ea_bnp": np.log(sv["ea_bnp"]) * 100, "ea_infl": hicp_sa.diff() * 4, "ea_ranta": sv["ea_ranta"]})
exog = pd.concat({f"{c}_l{k}": exo_bas[c].shift(k) for c in exo_bas for k in range(3)}, axis=1)
skuldkvot = sv["hush_skuld"] / inc * 100
NAMN = list(endog.columns); N = len(NAMN); IR = NAMN.index("styr"); IC = NAMN.index("kons")
alla = pd.concat([endog, exog], axis=1).dropna()


def bvar_irf(start, slut, dummies=None):
    df = alla.loc[start:slut]
    Y_all = df[NAMN].values
    T = len(Y_all) - P
    Y = Y_all[P:]
    X = [np.ones((T, 1))] + [Y_all[P - l:-l] for l in range(1, P + 1)] + [df[exog.columns].values[P:]]
    if dummies is not None:
        X.append(dummies.reindex(df.index).fillna(0).values[P:])
    X = np.hstack(X)
    keep = np.r_[np.ones(1 + N * P, bool), X[:, 1 + N * P:].std(0) > 1e-9]
    X = X[:, keep]                                       # ta bort dummies utan träff i fönstret
    X[:, 1 + N * P:] = (X[:, 1 + N * P:] - X[:, 1 + N * P:].mean(0)) / (X[:, 1 + N * P:].std(0) + 1e-9)  # skala exogena
    K = X.shape[1]
    # sigma från AR(1) per variabel
    sig = np.zeros(N)
    for i in range(N):
        y, x = Y_all[1:, i], np.c_[np.ones(len(Y_all) - 1), Y_all[:-1, i]]
        sig[i] = np.sqrt(np.mean((y - x @ np.linalg.lstsq(x, y, rcond=None)[0]) ** 2))
    # Dummyobservationer: Minnesota (slumpvandring) + kovarians; ingen restriktion på konstant/exogena (diffus)
    Yd, Xd = [], []
    for l in range(1, P + 1):
        yd = np.zeros((N, N)); xd = np.zeros((N, K))
        if l == 1:
            yd = np.diag(sig) / LAM
        for i in range(N):
            xd[i, 1 + (l - 1) * N + i] = sig[i] * l / LAM
        Yd.append(yd); Xd.append(xd)
    Yd.append(np.diag(sig)); Xd.append(np.zeros((N, K)))
    Xd.append(np.zeros((1, K))); Xd[-1][0, 0] = 1e-4; Yd.append(np.zeros((1, N)))
    Ys = np.vstack([Y] + Yd); Xs = np.vstack([X] + Xd)
    XtXi = np.linalg.inv(Xs.T @ Xs)
    B = XtXi @ Xs.T @ Ys
    E = Ys - Xs @ B
    S = E.T @ E; dof = Ys.shape[0] - K
    w, V = np.linalg.eigh((XtXi + XtXi.T) / 2)
    cholX = V * np.sqrt(np.clip(w, 0, None))
    irfs = np.empty((NDRAW, H + 1, N))
    for d in range(NDRAW):
        Sig = invwishart.rvs(df=dof, scale=S, random_state=rng)
        Bd = B + cholX @ rng.standard_normal((K, N)) @ np.linalg.cholesky(Sig).T
        A = [Bd[1 + (l - 1) * N: 1 + l * N].T for l in range(1, P + 1)]
        C = np.linalg.cholesky(Sig)
        imp = C[:, IR] / C[IR, IR]                # +1 pe styrränta på kvartal 0
        resp = np.zeros((H + 1 + P, N)); resp[P] = imp
        for h in range(1, H + 1):
            resp[P + h] = sum(A[l - 1] @ resp[P + h - l] for l in range(1, P + 1))
        irfs[d] = resp[P:]
    med = np.median(irfs, axis=0)
    hmin = int(np.argmin(med[:, IC]))
    lo, hi = np.percentile(irfs[:, hmin, IC], [16, 84])
    return {"start": df.index[P].strftime("%Y-%m"), "slut": df.index[-1].strftime("%Y-%m"), "T": T,
            "max_effekt_kons": float(med[hmin, IC]), "kvartal_max": hmin, "band68": [float(lo), float(hi)],
            "skuldkvot_medel": float(skuldkvot.loc[df.index[P]:df.index[-1]].mean()), "_med": med}


# ---------- Delperioder som Riksbanken ----------
kv = pd.date_range("1996-03-31", "2026-06-30", freq="QE")
slut_exp = [d for d in kv if pd.Timestamp("2009-12-31") <= d <= pd.Timestamp("2019-12-31")]
start_krymp = [d for d in kv if pd.Timestamp("1997-03-31") <= d <= pd.Timestamp("2006-03-31")]
fonster = [(pd.Timestamp("1996-03-31"), s) for s in slut_exp] + \
          [(s - pd.offsets.QuarterEnd(P), pd.Timestamp("2019-12-31")) for s in start_krymp[1:]]
res = [bvar_irf(a, b) for a, b in fonster]
print(f"{len(res)} delperioder skattade")

# ---------- Tillägg: rullande 14 år t.o.m. 2026K2 med pandemidummies ----------
pand = pd.DataFrame(0.0, index=alla.index, columns=[f"d{q}" for q in ["2020Q1", "2020Q2", "2020Q3", "2020Q4", "2021Q1"]])
for c in pand:
    pand.loc[pd.Period(c[1:], freq="Q").end_time.normalize(), c] = 1.0
slut_rull = [d for d in kv if pd.Timestamp("2020-03-31") <= d <= pd.Timestamp("2026-06-30")]
rull = [bvar_irf(s - pd.offsets.QuarterEnd(56 + P - 1), s, pand) for s in slut_rull]

# ---------- Sammanställ ----------
df = pd.DataFrame([{k: v for k, v in r.items() if k != "_med"} for r in res])
lut, kon = np.polyfit(df["skuldkvot_medel"], df["max_effekt_kons"], 1)
full = res[len(slut_exp) - 1]   # 1996/97–2019K4
R = {"lambda": LAM, "P": P, "antal_delperioder": len(res),
     "helt_urval": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in full.items() if k != "_med"},
     "lagst_skuldkvot": df.loc[df["skuldkvot_medel"].idxmin(), ["start", "slut", "skuldkvot_medel", "max_effekt_kons"]].to_dict(),
     "hogst_skuldkvot": df.loc[df["skuldkvot_medel"].idxmax(), ["start", "slut", "skuldkvot_medel", "max_effekt_kons"]].to_dict(),
     "lutning_per_10pe_skuldkvot": round(lut * 10, 3),
     "korrelation": round(float(df["skuldkvot_medel"].corr(df["max_effekt_kons"])), 2),
     "expanderande": {"korr": round(float(df.iloc[:len(slut_exp)]["skuldkvot_medel"].corr(df.iloc[:len(slut_exp)]["max_effekt_kons"])), 2),
                      "lutning_per_10pe": round(float(np.polyfit(df.iloc[:len(slut_exp)]["skuldkvot_medel"], df.iloc[:len(slut_exp)]["max_effekt_kons"], 1)[0] * 10), 3)},
     "krympande": {"korr": round(float(df.iloc[len(slut_exp):]["skuldkvot_medel"].corr(df.iloc[len(slut_exp):]["max_effekt_kons"])), 2),
                   "lutning_per_10pe": round(float(np.polyfit(df.iloc[len(slut_exp):]["skuldkvot_medel"], df.iloc[len(slut_exp):]["max_effekt_kons"], 1)[0] * 10), 3)},
     "rullande_2020_2026": [{"slut": r["slut"], "skuldkvot": round(r["skuldkvot_medel"], 0),
                             "max_effekt": round(r["max_effekt_kons"], 2), "band68": [round(x, 2) for x in r["band68"]]}
                            for r in rull[::4] + [rull[-1]]],
     "jamforelse_riksbanken": {"skuldkvot_spann": "126–170 %", "effekt": "ca −0,5 till −1,2 %", "MAJA": -0.65,
                               "slutsats": "ungefär dubbelt så stor effekt vid 200 % som vid 150 %"}}
for k in ("lagst_skuldkvot", "hogst_skuldkvot"):
    R[k] = {a: (round(b, 2) if isinstance(b, float) else b) for a, b in R[k].items()}
df.to_csv(D / f"svar_delperioder{SUF}.csv", index=False)
(D / f"svar_resultat{SUF}.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))

# ---------- Grafer ----------
fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
a = ax[0]
exp = df.iloc[:len(slut_exp)]; kr = df.iloc[len(slut_exp):]
a.scatter(exp["skuldkvot_medel"], exp["max_effekt_kons"], s=22, c="#3b6ea8", label="Expanderande (slut 2009–2019)")
a.scatter(kr["skuldkvot_medel"], kr["max_effekt_kons"], s=22, c="#e07b39", label="Krympande (start 1997–2006)")
xs = np.linspace(df["skuldkvot_medel"].min(), df["skuldkvot_medel"].max(), 10)
a.plot(xs, kon + lut * xs, "k--", lw=1)
a.axhline(-0.65, color="red", lw=1, ls=":", label="MAJA (Riksbanken): −0,65 %")
a.set_xlabel("Genomsnittlig skuldkvot i delperioden, % av disp. inkomst")
a.set_ylabel("Max effekt på konsumtionen, %")
a.set_title(f"Effekt av +1 pe styrränta vs skuldkvot, 1997–2019 (λ={LAM})"); a.grid(alpha=.3); a.legend(fontsize=7)
a = ax[1]
for r, lab, col in [(full, f"Hela urvalet {full['start'][:4]}–2019", "#3b6ea8"), (rull[-1], f"Rullande {rull[-1]['start'][:4]}–2026", "#c0504d")]:
    a.plot(range(H + 1), r["_med"][:, IC], label=lab, color=col)
a.plot(range(H + 1), full["_med"][:, IR], color="#3b6ea8", ls=":", label="Styrränta (hela urvalet)")
a.axhline(0, color="k", lw=.5); a.grid(alpha=.3); a.legend(fontsize=7)
a.set_xlabel("Kvartal efter räntehöjning"); a.set_ylabel("% resp. pe"); a.set_title("Konsumtionens respons (median)")
fig.tight_layout(); fig.savefig(G / f"7_svar_delperioder{SUF}.png", dpi=130)
