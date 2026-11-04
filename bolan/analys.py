#!/usr/bin/env python3
"""Skattningar: räntebindning -> genomslag, bostadspriser, bygglov/påbörjanden
och hushållens konsumtion per COICOP. Skriver data/resultat.json + grafer/."""
import json
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

BAS = Path(__file__).resolve().parent
D = BAS / "data"
G = BAS / "grafer"
G.mkdir(exist_ok=True)
les = lambda n: pd.read_csv(D / n, index_col=0, parse_dates=True)
R = {}


def ols(y, X, hac=4):
    df = pd.concat([y, X], axis=1).dropna()
    m = sm.OLS(df.iloc[:, 0], sm.add_constant(df.iloc[:, 1:])).fit(cov_type="HAC", cov_kwds={"maxlags": hac})
    return m, len(df), df.index.min(), df.index.max()


def kv(m, namn):
    return {"koef": round(float(m.params[namn]), 3), "t": round(float(m.tvalues[namn]), 2)}


# ---------- A. Faktakoll: andelar ----------
hl = les("hushall_lan_rantebindning.csv")
bl = les("bolan_rantebindning.csv")
# SCB-fel: 2025-05..2026-05 har negativa belopp i återstående bindning -> maskas
aterst = [c for c in hl if c.startswith("aterst")]
fel = (hl[aterst] < 0).any(axis=1) | (hl["aterst_2.1"] > hl["aterst_2.0"])
hl.loc[fel, aterst] = np.nan
R["datafel_maskade_manader"] = [d.strftime("%Y-%m") for d in hl.index[fel]]
andel = pd.DataFrame({
    "bolan_urspr_rorlig": bl["2.1"] / bl["2.0"],                       # bolån, ursprunglig <=3 mån
    "hush_aterst_3m": hl["aterst_2.1"] / hl["aterst_2.0"],              # alla hushållslån, återstående <=3 mån
    "hush_aterst_1ar": (hl["aterst_2.1"] + hl["aterst_2.2"]) / hl["aterst_2.0"],
    "hush_urspr_rorlig": hl["urspr_2.1"] / hl["urspr_2.0"],
})
sen = andel.index.max()
R["andelar_senast"] = {"manad": sen.strftime("%Y-%m"), **{k: round(float(v), 3) for k, v in andel.loc[sen].items()}}
R["andelar_min"] = {k: {"varde": round(float(andel[k].min()), 3), "manad": andel[k].idxmin().strftime("%Y-%m")} for k in andel}
R["andelar_max"] = {k: {"varde": round(float(andel[k].max()), 3), "manad": andel[k].idxmax().strftime("%Y-%m")} for k in andel}
R["bolan_stock_mdkr"] = round(float(bl["2.0"].iloc[-1]) / 1000)
R["hushallslan_stock_mdkr"] = round(float(hl["aterst_2.0"].iloc[-1]) / 1000)

fig, ax = plt.subplots(figsize=(9, 4.5))
(andel["bolan_urspr_rorlig"] * 100).plot(ax=ax, label="Bolån: ursprunglig bindning ≤3 mån (rörligt)")
(andel["hush_aterst_3m"] * 100).plot(ax=ax, label="Alla hushållslån: ny ränta inom 3 mån")
(andel["hush_aterst_1ar"] * 100).plot(ax=ax, label="Alla hushållslån: ny ränta inom 1 år")
ax.set_ylabel("% av utestående"); ax.set_title("Andel lån med rörlig/snart omsatt ränta (MFI, SCB)")
ax.grid(alpha=.3); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(G / "1_andelar.png", dpi=130)

# ---------- B. Genomslag styrränta -> snittränta på utestående bolån ----------
rt = les("bolanerantor.csv")
sty = les("styrranta.csv")["styrranta"]
m = pd.concat([rt, sty], axis=1).dropna(subset=["utest_1"])
m["d_utest"] = m["utest_1"].diff()
m["d_nyrorl"] = m["nya_1.1.1"].diff()
X = pd.concat({f"d_sty_l{k}": m["styrranta"].diff().shift(k) for k in range(0, 13)}, axis=1)
mod, n, a, b = ols(m["d_utest"], X, 12)
kum = np.cumsum([mod.params[f"d_sty_l{k}"] for k in range(13)])
R["genomslag_utestaende"] = {"period": f"{a:%Y-%m}–{b:%Y-%m}", "n": n,
                             "kumulativt_efter_3m": round(float(kum[3]), 2),
                             "kumulativt_efter_6m": round(float(kum[6]), 2),
                             "kumulativt_efter_12m": round(float(kum[12]), 2)}
# Under höjningscykeln
h0, h1 = "2022-03-31", "2024-03-31"
R["hojningscykel_2022_2024"] = {
    "styrranta_pp": round(float(m.loc[h1, "styrranta"] - m.loc[h0, "styrranta"]), 2),
    "ny_rorlig_bolaneranta_pp": round(float(m.loc[h1, "nya_1.1.1"] - m.loc[h0, "nya_1.1.1"]), 2),
    "snittranta_utestaende_pp": round(float(m.loc[h1, "utest_1"] - m.loc[h0, "utest_1"]), 2),
}
# Hushållens ränteutgifter på bolån (approx: stock * snittränta)
rant = (bl["2.0"] * rt["utest_1"] / 100 / 1000).dropna()  # mdkr per år
R["rantutgift_bolan_mdkr_ar"] = {"senast": round(float(rant.iloc[-1])), "manad": rant.index[-1].strftime("%Y-%m"),
                                 "topp": round(float(rant.max())), "topp_manad": rant.idxmax().strftime("%Y-%m"),
                                 "2021-12": round(float(rant.loc["2021-12-31"]))}

fig, ax = plt.subplots(figsize=(9, 4.5))
m.loc["2015":, "styrranta"].plot(ax=ax, label="Styrränta")
m.loc["2015":, "nya_1.1.1"].plot(ax=ax, label="Nya bolån, rörlig (≤3 mån)")
m.loc["2015":, "utest_1"].plot(ax=ax, label="Snittränta, alla utestående bolån")
ax2 = ax.twinx(); rant.loc["2015":].plot(ax=ax2, color="grey", ls="--", label="Ränteutgift bolån, mdkr/år (h.a.)")
ax.set_ylabel("%"); ax2.set_ylabel("mdkr/år"); ax.grid(alpha=.3)
h1_, l1_ = ax.get_legend_handles_labels(); h2_, l2_ = ax2.get_legend_handles_labels()
ax.legend(h1_ + h2_, l1_ + l2_, fontsize=8, loc="upper left"); ax.set_title("Snabbt genomslag: stocken följer den rörliga räntan")
fig.tight_layout(); fig.savefig(G / "2_genomslag.png", dpi=130)

# ---------- C. Bostadspriser (kvartal) ----------
fp = les("fastpi_smahus.csv")
q = pd.DataFrame({"p": np.log(fp["riket"])})
rq = rt.resample("QE").mean()
q["r_ny"] = rq["nya_1.1.1"]; q["r_ut"] = rq["utest_1"]
q["andel_rorl"] = andel["bolan_urspr_rorlig"].resample("QE").mean()
q["dp"] = q["p"].diff() * 100
q["dr"] = q["r_ut"].diff()
# ADL: dp_t = a + sum b_k dr_{t-k} + c dp_{t-1}
X = pd.concat({**{f"dr_l{k}": q["dr"].shift(k) for k in range(0, 5)}, "dp_l1": q["dp"].shift(1)}, axis=1)
mod, n, a, b = ols(q["dp"], X)
kort = sum(mod.params[f"dr_l{k}"] for k in range(5))
R["bostadspriser_adl"] = {"period": f"{a:%Y}Q–{b:%Y}Q", "n": n, "r2": round(mod.rsquared, 2),
                          "kumulativ_effekt_4kv_pct_per_pp": round(float(kort), 1),
                          "langsiktig_pct_per_pp": round(float(kort / (1 - mod.params["dp_l1"])), 1),
                          "dp_l1": kv(mod, "dp_l1")}
# Interaktion: slår räntan hårdare när rörlig andel är hög?
q["dr4"] = q["r_ut"].diff(4); q["dp4"] = q["p"].diff(4) * 100
q["andel_c"] = (q["andel_rorl"] - q["andel_rorl"].mean()) * 100
X = pd.concat({"dr4_l1": q["dr4"].shift(1), "andel_c_l1": q["andel_c"].shift(1),
               "dr4xandel_l1": (q["dr4"] * q["andel_c"]).shift(1)}, axis=1)
mod, n, a, b = ols(q["dp4"], X)
R["bostadspriser_interaktion"] = {"n": n, "dr4_l1": kv(mod, "dr4_l1"), "dr4xandel_l1": kv(mod, "dr4xandel_l1"),
                                  "tolkning": "dr4xandel: extra %-effekt per pp ränta per +1 pe högre rörlig andel"}

# ---------- D. Bygglov och påbörjanden ----------
bg = les("bygglov.csv"); pb = les("paborjade.csv")
bo = pd.DataFrame({"bygglov": bg["smahus"] + bg["flerbo"], "pab": pb["pab_flerbo"] + pb["pab_småhus"],
                   "bygglov_flerbo": bg["flerbo"], "pab_flerbo": pb["pab_flerbo"],
                   "bygglov_smahus": bg["smahus"], "pab_smahus": pb["pab_småhus"]})
r4 = bo.rolling(4).sum()                         # rullande 4 kv tar bort säsong
bq = pd.concat([np.log(r4).diff(4) * 100, q[["dp4", "dr4"]]], axis=1).loc["1997":]
# Ledtider: korrelation mellan bygglov(t-k) och påbörjade(t)
R["bygglov_leder_paborjade"] = {f"k{k}": round(float(bq["pab"].corr(bq["bygglov"].shift(k))), 2) for k in range(0, 7)}
res = {}
for y in ["bygglov", "pab"]:
    best = max(range(0, 7), key=lambda k: abs(bq[y].corr(bq["dp4"].shift(k))))
    res[y] = {"korr_prisbastlag": {"lag_kv": best, "r": round(float(bq[y].corr(bq["dp4"].shift(best))), 2)}}
    X = pd.concat({"dp4_l2": bq["dp4"].shift(2), "dr4_l2": bq["dr4"].shift(2)}, axis=1)
    mod, n, a, b = ols(bq[y], X)
    res[y].update({"period": f"{a:%Y}–{b:%Y}", "n": n, "r2": round(mod.rsquared, 2),
                   "pris_1pct": kv(mod, "dp4_l2"), "ranta_1pp": kv(mod, "dr4_l2")})
R["byggande"] = res
R["byggande_senast"] = {"kvartal": bo.index[-1].strftime("%Y-%m"),
                        "pab_4kv": int(r4["pab"].iloc[-1]), "bygglov_4kv": int(r4["bygglov"].iloc[-1]),
                        "pab_4kv_topp": int(r4["pab"].max()), "pab_4kv_topp_kv": r4["pab"].idxmax().strftime("%Y-%m")}

fig, ax = plt.subplots(figsize=(9, 4.5))
(r4[["bygglov", "pab"]] / 1000).loc["2005":].plot(ax=ax)
ax.set_ylabel("tusen lgh, rullande 4 kv"); ax.grid(alpha=.3)
ax2 = ax.twinx(); q["dp4"].loc["2005":].plot(ax=ax2, color="grey", ls="--", label="Småhuspriser, % å/å (h.a.)")
ax2.axhline(0, color="grey", lw=.5)
h1_, l1_ = ax.get_legend_handles_labels(); h2_, l2_ = ax2.get_legend_handles_labels()
ax.legend(h1_ + h2_, ["Bygglov", "Påbörjade"] + l2_, fontsize=8, loc="lower left")
ax.set_title("Bygglov, påbörjanden och småhuspriser"); fig.tight_layout(); fig.savefig(G / "3_byggande.png", dpi=130)

# ---------- E. Konsumtion per COICOP (månad) ----------
km = les("konsumtion_manad_coicop.csv")
namn = {"CP01": "Livsmedel", "CP02": "Alkohol/tobak", "CP03": "Kläder/skor", "CP04": "Boende/el",
        "CP05": "Möbler/hushållsutr.", "CP06": "Hälsa", "CP07": "Transport", "CP08": "Info/komm.",
        "CP09": "Rekreation/kultur", "CP11": "Restaurang/hotell", "CP13": "Personlig vård m.m.",
        "TOTex1012": "Totalt"}
rm = rt["utest_1"]
kons = {}
for c in namn:
    y = np.log(km[c]).diff(12) * 100
    X = pd.concat({"dr12_l3": rm.diff(12).shift(3)}, axis=1)
    df = pd.concat([y, X], axis=1).dropna()
    df = df[(df.index < "2020-03-01") | (df.index > "2022-06-30")]   # bort med pandemin
    mod = sm.OLS(df.iloc[:, 0], sm.add_constant(df.iloc[:, 1:])).fit(cov_type="HAC", cov_kwds={"maxlags": 12})
    toppen = km[c].loc["2021-07":"2022-06"].mean()
    botten = km[c].loc["2023-01":"2024-06"].min()
    kons[namn[c]] = {"beta_pct_per_pp": round(float(mod.params["dr12_l3"]), 2), "t": round(float(mod.tvalues["dr12_l3"]), 2),
                     "fall_topp_till_botten_pct": round(float((botten / toppen - 1) * 100), 1),
                     "senast_vs_2021H2_22H1_pct": round(float((km[c].iloc[-1] / toppen - 1) * 100), 1)}
R["konsumtion_coicop"] = {"manad_senast": km.index[-1].strftime("%Y-%m"), "n_obs": len(df), "per_kategori": kons}

kd = pd.DataFrame(kons).T.sort_values("beta_pct_per_pp")
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh(kd.index, kd["beta_pct_per_pp"], color=["#888" if i == "Totalt" else "#3b6ea8" for i in kd.index])
ax.axvline(0, color="k", lw=.6); ax.grid(alpha=.3, axis="x")
ax.set_xlabel("% förändring i konsumtionsvolym (å/å) per +1 pe i snittbolåneräntan (3 mån fördröjning)")
ax.set_title("Räntekänslighet per konsumtionsändamål, 2019–2026 exkl. pandemin")
fig.tight_layout(); fig.savefig(G / "4_konsumtion_coicop.png", dpi=130)

(D / "resultat.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=str))
print(json.dumps(R, ensure_ascii=False, indent=1, default=str))
