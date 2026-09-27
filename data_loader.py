"""Chargement des données et moteur de comparaison Source / Cible."""
from __future__ import annotations

import math

import pandas as pd

CLE = "code_article"
COL_DOMAINE = "domaine"

TYPE_NON_MIGRE = "Article non migré"
TYPE_VALEUR = "Valeur différente"
TYPE_VIDE_CIBLE = "Vide en cible"
TYPE_VIDE_SOURCE = "Vide en source"
TYPES_ECART = [TYPE_VALEUR, TYPE_VIDE_CIBLE, TYPE_VIDE_SOURCE, TYPE_NON_MIGRE]


def load_excel(path_or_buffer) -> dict[str, pd.DataFrame]:
    xls = pd.read_excel(path_or_buffer, sheet_name=None, dtype=object)
    manquantes = {"Source", "Cible", "Groupes_Attributs"} - set(xls)
    if manquantes:
        raise ValueError(f"Feuilles manquantes dans le fichier : {', '.join(sorted(manquantes))}")
    data = {
        "source": xls["Source"],
        "cible": xls["Cible"],
        "groupes": xls["Groupes_Attributs"],
        "suivi": xls.get("Suivi_Mensuel"),
    }
    for k in ("source", "cible"):
        df = data[k]
        df[CLE] = df[CLE].astype(str).str.strip()
        if COL_DOMAINE not in df:
            df[COL_DOMAINE] = "Non renseigné"
    g = data["groupes"]
    g["groupe_attributs"] = g["groupe_attributs"].astype(str).str.strip()
    g["champ"] = g["champ"].astype(str).str.strip()
    if data["suivi"] is not None:
        s = data["suivi"]
        s["mois"] = pd.to_datetime(s["mois"])
        for c in ("articles_a_migrer", "articles_migres", "articles_prevus", "articles_en_ecart"):
            if c in s:
                s[c] = pd.to_numeric(s[c], errors="coerce").fillna(0)
    return data


def _vide(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return isinstance(v, str) and v.strip() == ""


def _normalise(v):
    """Rend comparables des valeurs lues depuis Excel (12 == 12.0 == '12')."""
    if _vide(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        try:
            return round(float(s.replace(",", ".")), 6)
        except ValueError:
            return s
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return str(v).strip()


def _affiche(v) -> str:
    if _vide(v):
        return "∅ (vide)"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def compare(source: pd.DataFrame, cible: pd.DataFrame, groupes: pd.DataFrame) -> pd.DataFrame:
    """Retourne une ligne par (article, champ) avec le statut de comparaison.

    Colonnes : code_article, domaine, groupe_attributs, champ, valeur_source,
    valeur_cible, ecart (bool), type_ecart.
    """
    champs = groupes[groupes["champ"].isin(source.columns)]
    src = source.set_index(CLE)
    cib = cible.drop_duplicates(CLE).set_index(CLE)
    migres = src.index.isin(cib.index)

    frames = []
    for groupe, champ in champs[["groupe_attributs", "champ"]].itertuples(index=False):
        vs = src[champ]
        vc = cib[champ].reindex(src.index) if champ in cib else pd.Series(None, index=src.index)
        ns = vs.map(_normalise)
        nc = vc.map(_normalise)
        type_ecart = pd.Series("", index=src.index, dtype=object)
        diff = ns.ne(nc) & ~(ns.isna() & nc.isna())
        type_ecart[diff] = TYPE_VALEUR
        type_ecart[diff & nc.isna()] = TYPE_VIDE_CIBLE
        type_ecart[diff & ns.isna()] = TYPE_VIDE_SOURCE
        type_ecart[~migres] = TYPE_NON_MIGRE
        frames.append(pd.DataFrame({
            CLE: src.index,
            COL_DOMAINE: src[COL_DOMAINE].values,
            "groupe_attributs": groupe,
            "champ": champ,
            "valeur_source": vs.map(_affiche).values,
            "valeur_cible": vc.map(_affiche).where(migres, "— (non migré)").values,
            "type_ecart": type_ecart.values,
        }))
    res = pd.concat(frames, ignore_index=True)
    res["ecart"] = res["type_ecart"] != ""
    return res
