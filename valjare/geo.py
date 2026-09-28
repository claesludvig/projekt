#!/usr/bin/env python3
"""Väljardatabasen: nyckel mellan valdistrikt 2026 och DeSO 2025.

Läser råfilerna i data/geo_ra (hämtade av hamta.py --steg geo), lägger dem i
SWEREF 99 TM och räknar överlappande yta. Resultatet, data/geo/
valdistrikt_deso.csv, är litet och ligger i git så att bygg_db.py kan köras
utan geodata.

Antagande: befolkningen är jämnt fördelad inom varje DeSO-område. Ett distrikt
som täcker 40 % av ett DeSO:s yta antas ha 40 % av dess invånare. Det är
grovt där DeSO-områden spänner över både tätort och glesbygd."""

import re
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RA = BASE_DIR / "data" / "geo_ra"
UT = BASE_DIR / "data" / "geo"


def _las(namn: str):
    import geopandas as gpd
    f = RA / f"{namn}.las"
    if not f.exists():
        return None
    gdf = gpd.read_file(f.read_text(encoding="utf-8").strip())
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(3006)


def _kodkolumn(gdf, monster: str) -> str | None:
    """Kolumnen där flest värden matchar mönstret."""
    bast, andel = None, 0.0
    for c in gdf.columns:
        if c == "geometry":
            continue
        v = gdf[c].astype(str)
        a = v.str.fullmatch(monster).mean()
        if a > andel:
            bast, andel = c, a
    return bast if andel > 0.9 else None


def main():
    deso = _las("deso_2025")
    vd = _las("valdistrikt_2026")
    if deso is None or vd is None:
        print("Geodata saknas; hoppar över (befintlig nyckel i data/geo behålls).")
        return 0
    dk = _kodkolumn(deso, r"\d{4}[A-C]\d{4}")
    # Valdistriktskod: kommunkod (4) + löpnummer, ibland med prefix/nollor
    vk = "Valdistriktskod" if "Valdistriktskod" in vd.columns else _kodkolumn(vd, r"\d{6,10}")
    print(f"DeSO-kod: {dk}, valdistriktskod: {vk}")
    if dk is None or vk is None:
        print("Hittar inte kodkolumner:", list(deso.columns), list(vd.columns))
        return 1
    namnkol = "Valdistriktsnamn" if "Valdistriktsnamn" in vd.columns else \
        next((c for c in vd.columns if re.search(r"(?i)namn|name", c)), None)
    deso = deso[[dk, "geometry"]].rename(columns={dk: "deso"})
    deso["deso_yta"] = deso.area
    vd = vd[[vk] + ([namnkol] if namnkol else []) + ["geometry"]].rename(
        columns={vk: "valdistrikt", **({namnkol: "namn"} if namnkol else {})})
    vd["valdistrikt"] = vd["valdistrikt"].astype(str)
    vd = vd.dissolve(by="valdistrikt", as_index=False) if vd.valdistrikt.duplicated().any() else vd
    vd["distrikt_yta"] = vd.area
    import geopandas as gpd
    ov = gpd.overlay(vd[["valdistrikt", "distrikt_yta", "geometry"]],
                     deso[["deso", "deso_yta", "geometry"]], how="intersection", keep_geom_type=True)
    ov["yta"] = ov.area
    ov = ov[ov.yta > 1]  # bort med kantbrus under 1 m²
    ov["andel_av_deso"] = ov.yta / ov.deso_yta
    ov["andel_av_distrikt"] = ov.yta / ov.distrikt_yta
    UT.mkdir(parents=True, exist_ok=True)
    ov[["valdistrikt", "deso", "andel_av_deso", "andel_av_distrikt"]].round(5) \
        .sort_values(["valdistrikt", "deso"]).to_csv(UT / "valdistrikt_deso.csv", index=False)
    info = vd.drop(columns="geometry").copy()
    c = vd.to_crs(4326).geometry.representative_point()
    info["lon"], info["lat"] = c.x.round(5), c.y.round(5)
    info["yta_km2"] = (vd.distrikt_yta / 1e6).round(3)
    info.drop(columns="distrikt_yta").to_csv(UT / "valdistrikt_2026.csv", index=False)
    tackning = ov.groupby("valdistrikt").andel_av_distrikt.sum()
    print(f"{len(vd)} valdistrikt, {len(deso)} DeSO, {len(ov)} överlapp; "
          f"median täckning {tackning.median():.3f}, andel distrikt <0,9: {(tackning < .9).mean():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
