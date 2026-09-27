# Dashboard – Migration du référentiel article

Dashboard Streamlit pour analyser la migration d'un référentiel article : une **Vue Globale**
(KPIs + graphiques cliquables) et une vue **Détail Migration** (champs en écart, valeurs en
différence, comparaison article par article).

## Lancer

```bash
python -m pip install -r requirements.txt
python generate_sample_data.py      # (optionnel) régénère le fichier d'exemple
python -m streamlit run app.py
```

## Interactions

- **Filtres** (barre latérale) : Domaine, Groupe d'attributs, Champ (limité aux champs du groupe
  choisi), Type d'écart. Ils sont partagés par les deux vues.
- **Clic sur un graphique** de la Vue Globale : filtre tout le rapport (un 2ᵉ clic sur la même barre
  retire le filtre). Le clic sur « Top 10 des champs » ouvre directement le détail du champ.
- **Clic sur une carte KPI** (« Voir le détail → ») : ouvre le Détail Migration déjà pré-filtré.
- **Détail** : cliquer une ligne du tableau « Champs en écart » filtre sur ce champ ;
  bouton **🔄 Réinitialiser les filtres** en haut de page (et dans la barre latérale).

## Format du fichier Excel

| Feuille | Colonnes |
|---|---|
| `Source` | `code_article`, `domaine`, puis une colonne par champ |
| `Cible` | mêmes colonnes que `Source` (données après migration) |
| `Groupes_Attributs` | `groupe_attributs`, `champ` |
| `Suivi_Mensuel` *(optionnelle)* | `mois`, `domaine`, `articles_a_migrer`, `articles_migres`, `articles_prevus`, `articles_en_ecart` |

Types d'écart détectés : *Valeur différente*, *Vide en cible*, *Vide en source*, *Article non migré*.
Les nombres sont comparés après normalisation (`12` = `12.0` = `"12"`), les textes après suppression
des espaces en début/fin.
