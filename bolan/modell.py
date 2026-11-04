#!/usr/bin/env python3
"""Liten strukturmodell för bolån -> bostadspriser -> byggande -> konsumtion.

Kvartalsdata 2006–2026. Fyra beteendeekvationer + en identitet:

 (1) Genomslag   r = s·r_rörl + (1−s)·r_bunden   (identitet; s = andel rörliga bolån)
                 Δr_rörl = θ_v·Δi ;  Δr_ny_bunden = θ_f·Δi ;  Δr_bunden = μ·(r_ny_bunden − r_bunden)_{t-1}
 (2) Priser      långsikt  p* = α + β_y·y − β_h·h − β_r·r       (inverterad efterfrågan, Poterba)
                 kortsikt  Δp_t = λ·(p−p*)_{t-1} + φ·Δp_{t-1} + κ·Δr_{t-1} + ε
                 p = ln(småhuspris/KPIF), y = ln(real disp. inkomst), h = ln(bostadsbestånd)
                 Huvudvariant: p* = α + y − β_r·r (pris/inkomst beror på räntan); fri variant redovisas.
 (3) Utbud       ln S_t = a + η·ln q_{t-2} + ζ·r_{t-2} + trend      (Tobins q)
                 S = påbörjade lgh (4 kv), q = småhuspris / byggkostnad
 (4) Konsumtion  Δ4 c_t = a + b·Δ4 y_t + γ·Δ4 B_{t-1} + δ·Δ4 p_{t-2}
                 B = ränteutgift bolån i % av disp. inkomst (kassaflöde), p = förmögenhet
 (5) Identitet   H_t = H_{t-1} + färdigställda_t ;  färdigställda ≈ ρ·påbörjade_{t-L}

Därefter simuleras +1 pe i styrräntan med andel rörligt 42 % (2022) resp. 78 % (2026)."""
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore")
BAS = Path(__file__).resolve().parent
D, G = BAS / "data", BAS / "grafer"
les = lambda n: pd.read_csv(D / n, index_col=0, parse_dates=True)
BESTAND_2024 = 5_250_000   # ca antal lägenheter 2024-12-31 (SCB:s bostadsbestånd), ankare för kumulerade färdigställda


def ols(y, X, hac=4):
    df = pd.concat([y, X], axis=1, sort=True).dropna()
    m = sm.OLS(df.iloc[:, 0], sm.add_constant(df.iloc[:, 1:])).fit(cov_type="HAC", cov_kwds={"maxlags": hac})
    return m, df


def tab(m, df):
    return {"n": int(m.nobs), "period": f"{df.index.min():%Y-%m}–{df.index.max():%Y-%m}", "r2": round(m.rsquared, 2),
            "koef": {k: {"b": round(float(v), 4), "t": round(float(m.tvalues[k]), 2)} for k, v in m.params.items()}}


# ---------- Data till kvartal ----------
Q = lambda s, f="mean": getattr(s.resample("QE"), f)()
rt = les("bolanerantor.csv"); bl = les("bolan_rantebindning.csv")
kpif = Q(les("kpif.csv")["kpif"]); bki = Q(les("bki.csv")["bki_smahus"])
inc = les("disponibel_inkomst.csv").rolling(4).sum()               # 4 kv summa tar bort säsong
pb = les("paborjade.csv"); kons = les("konsumtion_nr_kvartal.csv")["S14"]
d = pd.DataFrame({
    "i": Q(les("styrranta.csv")["styrranta"]),
    "r": Q(rt["utest_1"]),
    "s": Q(bl["2.1"] / bl["2.0"]),
    "p": np.log(les("fastpi_smahus.csv")["riket"] / kpif * 100),
    "y": np.log(inc["disp_real"]),
    "q": np.log(les("fastpi_smahus.csv")["riket"] / bki),
    "S": np.log((pb["pab_flerbo"] + pb["pab_småhus"]).rolling(4).sum()),
    "pab": pb["pab_flerbo"] + pb["pab_småhus"],
    "fard": pb["fardig_flerbo"] + pb["fardig_småhus"],
    "c": np.log(kons),
}, ).sort_index()
# Bostadsbestånd: kumulerade färdigställda, ankrat 2024K4
cum = d["fard"].cumsum()
d["H"] = BESTAND_2024 + cum - cum.loc["2024-12-31"]
d["h"] = np.log(d["H"])
skuld = Q(bl["2.0"])
d["B"] = skuld * d["r"] / 100 / inc["disp_nom"] * 100               # ränteutgift bolån, % av disp. inkomst
d = d.loc["1996":]
R = {}

# ---------- (1) Genomslag: identitet + två skattade ekvationer ----------
#  r = s·r_rörl + (1−s)·r_bunden                       (identitet, utestående stock)
#  Δr_rörl_t   = θ_v·Δi_t                               (rörliga följer styrräntan direkt)
#  Δr_ny_bund_t = θ_f·Δi_t + θ_f1·Δi_{t-1}              (nya 3–5-årsräntor, terminsstruktur)
#  Δr_bunden_t = μ·(r_ny_bund − r_bunden)_{t-1}         (μ = andel bundna lån som omsätts per kvartal)
d["rv"] = Q(rt["utest_1.1.1"])
d["rfn"] = Q(rt["nya_1.1.2.2.2"])
d["rfs"] = (d["r"] - d["s"] * d["rv"]) / (1 - d["s"])
di = d["i"].diff()
m1v, df1v = ols(d["rv"].diff(), pd.DataFrame({"di": di, "di_l1": di.shift(1)}))
m1f, df1f = ols(d["rfn"].diff(), pd.DataFrame({"di": di, "di_l1": di.shift(1)}))
m1m, df1m = ols(d["rfs"].diff(), pd.DataFrame({"gap_l1": (d["rfn"] - d["rfs"]).shift(1)}))
R["1a_rorlig_stock"] = tab(m1v, df1v); R["1b_ny_bunden_3_5ar"] = tab(m1f, df1f); R["1c_omsattning_bundna"] = tab(m1m, df1m)
mu = float(m1m.params["gap_l1"])
R["1c_omsattning_bundna"]["implicit_snittlop_ar"] = round(1 / mu / 4, 1)
sbar = float(d["s"].mean())

# ---------- (2) Priser: långsiktig relation + felkorrigering ----------
m2f, df2f = ols(d["p"], d[["y", "h", "r"]], hac=8)
R["2a_pris_langsikt_fri"] = tab(m2f, df2f)            # y och h nästan kolineära -> h får fel tecken; används ej
# Huvudvariant: pris/inkomst beror på räntan,  p − y = α − β_r·r   (Engle–Granger)
m2l, df2l = ols(d["p"] - d["y"], d[["r"]], hac=8)
ecm = d["p"] - d["y"] - m2l.predict(sm.add_constant(d[["r"]]))
R["2b_pris_langsikt_p_minus_y"] = tab(m2l, df2l)
from statsmodels.tsa.stattools import coint
cdf = d[["p", "y", "r"]].loc["2005":].dropna()
R["2b_pris_langsikt_p_minus_y"]["engle_granger_p_y_r_pvarde"] = round(float(coint(cdf["p"] - cdf["y"], cdf[["r"]])[1]), 3)
X2 = pd.DataFrame({"ecm_l1": ecm.shift(1), "dp_l1": d["p"].diff().shift(1), "dr_l1": d["r"].diff().shift(1)})
m2s, df2s = ols(d["p"].diff(), X2)
R["2c_pris_ecm"] = tab(m2s, df2s)

# ---------- (3) Utbud: Tobins q ----------
X3 = pd.DataFrame({"q_l2": d["q"].shift(2), "r_l2": d["r"].shift(2), "trend": np.arange(len(d)) / 4})
m3, df3 = ols(d["S"], X3, hac=8)
R["3_utbud_tobins_q"] = tab(m3, df3)

# ---------- (5) Färdigställda ~ påbörjade med fördröjning ----------
f4, p4 = d["fard"].rolling(4).sum(), d["pab"].rolling(4).sum()
best = max(range(2, 11), key=lambda L: f4.corr(p4.shift(L)))
m5, df5 = ols(f4, pd.DataFrame({"pab_lag": p4.shift(best)}))
R["5_fardigstallda"] = tab(m5, df5); R["5_fardigstallda"]["lag_kv"] = best

# ---------- (4) Konsumtion: kassaflöde vs förmögenhet ----------
X4 = pd.DataFrame({"d4y": d["y"].diff(4), "d4B_l1": d["B"].diff(4).shift(1), "d4p_l2": d["p"].diff(4).shift(2)})
y4 = d["c"].diff(4)
covid = (y4.index >= "2020-01-01") & (y4.index <= "2021-12-31")
m4, df4 = ols(y4[~covid], X4[~covid], hac=6)
R["4_konsumtion"] = tab(m4, df4)
R["nulage"] = {"s": round(float(d["s"].dropna().iloc[-1]), 3), "B_pct_av_inkomst": round(float(d["B"].dropna().iloc[-1]), 2),
               "skuld_inkomst_pct": round(float((skuld / inc["disp_nom"]).dropna().iloc[-1] * 100), 0)}

# ---------- Simulering: +1 pe styrränta, permanent ----------
T = 16
skuldkvot = float((skuld / inc["disp_nom"]).dropna().iloc[-1])
P = m2l.params; Ps = m2s.params; P3 = m3.params; P4 = m4.params


def simulera(s):
    L = 13                                          # förhistorik
    n = T + L
    di = np.zeros(n); di[L] = 1.0                   # chock i kvartal 1
    rv = np.zeros(n); rfn = np.zeros(n); rfs = np.zeros(n)
    r = np.zeros(n); p = np.zeros(n); S = np.zeros(n); c = np.zeros(n); B = np.zeros(n)
    for t in range(L, n):
        rv[t] = rv[t - 1] + m1v.params["di"] * di[t] + m1v.params["di_l1"] * di[t - 1]
        rfn[t] = rfn[t - 1] + m1f.params["di"] * di[t] + m1f.params["di_l1"] * di[t - 1]
        rfs[t] = rfs[t - 1] + mu * (rfn[t - 1] - rfs[t - 1])
        r[t] = s * rv[t] + (1 - s) * rfs[t]
        dr = r[t] - r[t - 1]
        gap = p[t - 1] - P["r"] * r[t - 1]           # p − p*, avvikelse från basbana (y, h oförändrade)
        p[t] = p[t - 1] + Ps["ecm_l1"] * gap + Ps["dp_l1"] * (p[t - 1] - p[t - 2]) + Ps["dr_l1"] * (r[t - 1] - r[t - 2])
        q = p                                                                # byggkostnad oförändrad
        S[t] = P3["q_l2"] * q[t - 2] + P3["r_l2"] * r[t - 2]
        B[t] = skuldkvot * r[t]                                              # pe av inkomst
        c[t] = P4["d4B_l1"] * B[t - 1] + P4["d4p_l2"] * p[t - 2]             # nivåavvikelse (Δ4 ≈ nivå efter 4 kv)
    return pd.DataFrame({"bolaneranta_pe": r[L:], "huspris_pct": p[L:] * 100, "paborjade_pct": S[L:] * 100,
                         "rantebelastning_pe": B[L:], "konsumtion_pct": c[L:] * 100}, index=range(1, T + 1))


sim = {s: simulera(s) for s in (0.42, 0.78)}
R["simulering_plus1pe"] = {f"s={s:.2f}": v.loc[[1, 2, 4, 8, 16]].round(2).to_dict(orient="index") for s, v in sim.items()}

fig, ax = plt.subplots(2, 2, figsize=(10, 6.5), sharex=True)
for (kol, rubr), a in zip([("bolaneranta_pe", "Snittränta bolån, pe"), ("huspris_pct", "Reala småhuspriser, %"),
                           ("paborjade_pct", "Påbörjade bostäder, %"), ("konsumtion_pct", "Hushållens konsumtion, %")], ax.flat):
    for s, ls in ((0.42, "--"), (0.78, "-")):
        a.plot(sim[s].index, sim[s][kol], ls=ls, label=f"Andel rörligt {s:.0%}")
    a.axhline(0, color="k", lw=.5); a.set_title(rubr, fontsize=10); a.grid(alpha=.3)
ax[0, 0].legend(fontsize=8); [a.set_xlabel("kvartal efter chock") for a in ax[1]]
fig.suptitle("+1 procentenhet i styrräntan: modellens svar"); fig.tight_layout(); fig.savefig(G / "5_modell_simulering.png", dpi=130)

(D / "modell_resultat.json").write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
