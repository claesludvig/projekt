"""Varje citat i partier_katalog ska finnas ordagrant i partiets program (data/kallor/txt/prog_*.txt)."""

import sys
from pathlib import Path

BAS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BAS))

import partier  # noqa: E402
from partier_katalog import STANDPUNKTER  # noqa: E402


def test_alla_citat_finns_i_programmen():
    t = partier.tabell(BAS / "data" / "kallor")
    saknas = t[t.citat.notna() & t.program_hamtat & t.dokument.isna()]
    assert saknas.empty, "Citat som inte finns i programmet:\n" + "\n".join(
        f"{r.parti} {r.fraga}: {r.citat}" for r in saknas.itertuples())


def test_svaren_ar_giltiga():
    for _, _, fragor in STANDPUNKTER:
        for fid, _, svar in fragor:
            for p, (s, citat) in svar.items():
                assert s in ("ja", "nej", "delvis"), (fid, p, s)
                assert citat and len(citat) > 10, (fid, p)


def test_likhet():
    import pandas as pd
    t = pd.DataFrame([{"fraga": f, "parti": p, "svar": s} for f, p, s in
                      [("a", "S", "ja"), ("a", "M", "ja"), ("b", "S", "ja"), ("b", "M", "nej"), ("c", "S", "ja")]])
    l = partier.likhet(t).set_index(["parti_a", "parti_b"])
    assert l.loc[("S", "M"), "fragor"] == 2 and l.loc[("S", "M"), "andel_lika"] == 50
