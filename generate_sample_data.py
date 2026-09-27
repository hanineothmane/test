"""Génère un fichier Excel d'exemple pour le dashboard de migration du référentiel article.

Feuilles produites :
    - Source            : référentiel article de l'ancien système
    - Cible             : référentiel article dans le nouveau système (après migration)
    - Groupes_Attributs : correspondance groupe d'attributs -> champ
    - Suivi_Mensuel     : suivi mensuel de la migration par domaine

Usage : python generate_sample_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
OUT = Path(__file__).parent / "data" / "migration_data_exemple.xlsx"

DOMAINES = ["Alimentaire", "DPH", "Frais", "Textile", "Bazar"]

GROUPES = {
    "Données générales": ["libelle", "marque", "famille", "sous_famille", "statut_article"],
    "Logistique": ["unite_mesure", "pcb", "poids_net", "poids_brut", "longueur", "largeur", "hauteur"],
    "Prix & Fiscalité": ["prix_achat", "prix_vente", "taux_tva", "devise"],
    "Fournisseur": ["code_fournisseur", "ref_fournisseur", "pays_origine"],
    "Codification": ["ean", "code_douane"],
}

MARQUES = ["Marque Repère", "Nestlé", "Danone", "L'Oréal", "Tefal", "Tex", "Bic", "Lu"]
FAMILLES = {
    "Alimentaire": ["Épicerie salée", "Épicerie sucrée", "Boissons"],
    "DPH": ["Hygiène", "Beauté", "Entretien"],
    "Frais": ["Crèmerie", "Charcuterie", "Fruits & légumes"],
    "Textile": ["Homme", "Femme", "Enfant"],
    "Bazar": ["Cuisine", "Bricolage", "Papeterie"],
}
PAYS = ["FR", "ES", "IT", "DE", "CN", "MA", "PT"]


def build_source(n: int = 1500) -> pd.DataFrame:
    rows = []
    for i in range(n):
        dom = RNG.choice(DOMAINES, p=[0.3, 0.2, 0.2, 0.15, 0.15])
        fam = RNG.choice(FAMILLES[dom])
        prix_achat = round(float(RNG.uniform(0.5, 60)), 2)
        poids = round(float(RNG.uniform(0.05, 5)), 3)
        rows.append({
            "code_article": f"ART{100000 + i}",
            "domaine": dom,
            "libelle": f"{fam} article {i}",
            "marque": RNG.choice(MARQUES),
            "famille": fam,
            "sous_famille": f"{fam} - SF{RNG.integers(1, 5)}",
            "statut_article": RNG.choice(["Actif", "Actif", "Actif", "Bloqué", "Fin de vie"]),
            "unite_mesure": RNG.choice(["PCE", "KG", "L"]),
            "pcb": int(RNG.choice([1, 6, 12, 24])),
            "poids_net": poids,
            "poids_brut": round(poids * 1.08, 3),
            "longueur": int(RNG.integers(5, 60)),
            "largeur": int(RNG.integers(5, 40)),
            "hauteur": int(RNG.integers(2, 40)),
            "prix_achat": prix_achat,
            "prix_vente": round(prix_achat * float(RNG.uniform(1.2, 1.8)), 2),
            "taux_tva": float(RNG.choice([5.5, 10.0, 20.0])),
            "devise": "EUR",
            "code_fournisseur": f"F{RNG.integers(1000, 1100)}",
            "ref_fournisseur": f"REF-{RNG.integers(10000, 99999)}",
            "pays_origine": RNG.choice(PAYS),
            "ean": str(3000000000000 + int(RNG.integers(0, 999999999))),
            "code_douane": str(int(RNG.integers(10000000, 99999999))),
        })
    return pd.DataFrame(rows)


# Probabilité d'écart par groupe et par domaine, pour obtenir des profils contrastés
TAUX_ECART_GROUPE = {
    "Données générales": 0.02,
    "Logistique": 0.06,
    "Prix & Fiscalité": 0.035,
    "Fournisseur": 0.025,
    "Codification": 0.01,
}
MULT_DOMAINE = {"Alimentaire": 0.7, "DPH": 1.0, "Frais": 1.8, "Textile": 1.3, "Bazar": 0.9}


def alter(champ: str, val):
    """Produit une valeur cible erronée plausible."""
    r = RNG.random()
    if r < 0.15:
        return None  # valeur vide en cible
    if isinstance(val, (int, np.integer)):
        return int(val) + int(RNG.choice([-2, -1, 1, 2, 10]))
    if isinstance(val, (float, np.floating)):
        if champ == "taux_tva":
            return float(RNG.choice([t for t in [5.5, 10.0, 20.0] if t != val]))
        return round(float(val) * float(RNG.choice([0.9, 1.1, 1000, 0.001])), 3)
    if champ == "unite_mesure":
        return RNG.choice([u for u in ["PCE", "KG", "L", "UN"] if u != val])
    if champ in ("libelle", "famille", "sous_famille"):
        return str(val).upper() if r < 0.6 else str(val)[:12]
    if champ == "devise":
        return "USD"
    return f"{val}_X"


def build_cible(src: pd.DataFrame) -> pd.DataFrame:
    cible = src.copy().astype(object)
    # ~4 % d'articles non migrés
    non_migres = RNG.random(len(cible)) < 0.04
    cible = cible[~non_migres].reset_index(drop=True)
    for g, champs in GROUPES.items():
        for champ in champs:
            p = TAUX_ECART_GROUPE[g] * cible["domaine"].map(MULT_DOMAINE).astype(float)
            mask = RNG.random(len(cible)) < p
            for idx in np.where(mask)[0]:
                cible.at[idx, champ] = alter(champ, cible.at[idx, champ])
    return cible


def build_suivi(src: pd.DataFrame, cible: pd.DataFrame) -> pd.DataFrame:
    mois = pd.date_range("2026-03-01", "2026-09-01", freq="MS")
    rows = []
    for dom in DOMAINES:
        total = int((src["domaine"] == dom).sum())
        migres_fin = int((cible["domaine"] == dom).sum())
        for k, m in enumerate(mois):
            prog = (k + 1) / len(mois)
            migres = int(migres_fin * prog ** 0.8)
            ecarts = int(migres * MULT_DOMAINE[dom] * 0.25 * (1.4 - 0.6 * prog))
            rows.append({
                "mois": m,
                "domaine": dom,
                "articles_a_migrer": total,
                "articles_migres": migres,
                "articles_prevus": int(total * min(1.0, prog * 1.05)),
                "articles_en_ecart": ecarts,
            })
    return pd.DataFrame(rows)


def main():
    src = build_source()
    cible = build_cible(src)
    groupes = pd.DataFrame(
        [{"groupe_attributs": g, "champ": c} for g, cs in GROUPES.items() for c in cs]
    )
    suivi = build_suivi(src, cible)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT, engine="openpyxl") as xw:
        src.to_excel(xw, sheet_name="Source", index=False)
        cible.to_excel(xw, sheet_name="Cible", index=False)
        groupes.to_excel(xw, sheet_name="Groupes_Attributs", index=False)
        suivi.to_excel(xw, sheet_name="Suivi_Mensuel", index=False)
    print(f"Fichier généré : {OUT}")


if __name__ == "__main__":
    main()
