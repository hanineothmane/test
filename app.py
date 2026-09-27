"""Dashboard d'analyse de la migration du référentiel article.

Lancement : python -m streamlit run app.py
"""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_loader import CLE, COL_DOMAINE, TYPES_ECART, compare, load_excel

st.set_page_config(page_title="Migration Référentiel Article", page_icon="📦", layout="wide")

EXEMPLE = Path(__file__).parent / "data" / "migration_data_exemple.xlsx"
PAGES = ["Vue Globale", "Détail Migration"]
FILTRES = ["domaine", "groupe", "champ", "type"]

# Palette (bleu séquentiel + statuts)
BLEU = "#2a78d6"
BLEU_FONCE = "#184f95"
BLEU_PALE = "#b7d3f6"
GRIS = "#8a8984"
BON, ALERTE, CRITIQUE = "#0ca30c", "#eb6834", "#d03b3b"

# --------------------------------------------------------------------------- #
# Style : cartes KPI de taille strictement identique + carte entièrement cliquable
# --------------------------------------------------------------------------- #
st.markdown(
    """
<style>
.kpi-card{
  box-sizing:border-box; height:168px; width:100%;
  display:flex; flex-direction:column; justify-content:space-between;
  padding:14px 16px; border-radius:12px;
  background:#ffffff; border:1px solid #e3e2de; border-left:5px solid var(--accent);
  box-shadow:0 1px 3px rgba(0,0,0,.06); overflow:hidden; transition:all .15s ease;
}
.kpi-label{
  color:#52514e !important; font-size:.80rem; font-weight:600; text-transform:uppercase;
  letter-spacing:.03em; line-height:1.2; height:2.4em; overflow:hidden;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
}
.kpi-value{color:#0b0b0b !important; font-size:1.9rem; font-weight:700; line-height:1.1;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.kpi-sub{color:#6b6a66 !important; font-size:.78rem; height:1.3em; line-height:1.3em;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.kpi-foot{display:flex; align-items:center; gap:8px; height:22px; white-space:nowrap; overflow:hidden;}
.kpi-pill{font-size:.72rem; font-weight:700; padding:2px 8px; border-radius:999px; flex:none;}
.kpi-pill.up{background:#e3f5e3; color:#0a6e0a !important;}
.kpi-pill.down{background:#fbe4e4; color:#a52a2a !important;}
.kpi-pill.flat{background:#efeeea; color:#52514e !important;}
.kpi-cta{margin-left:auto; color:#2a78d6 !important; font-size:.72rem; font-weight:600; flex:none;}

/* Carte cliquable : le bouton Streamlit recouvre toute la carte, de façon invisible */
div[class*="st-key-kpi_"]{position:relative; gap:0 !important;}
div[class*="st-key-kpi_"] .stElementContainer:has(.stButton){
  position:absolute !important; inset:0; z-index:5; margin:0 !important;
}
div[class*="st-key-kpi_"] .stButton, div[class*="st-key-kpi_"] .stButton button{
  width:100% !important; height:100% !important; min-height:100% !important;
}
div[class*="st-key-kpi_"] .stButton button{opacity:0; cursor:pointer;}
div[class*="st-key-kpi_"]:hover .kpi-card{
  box-shadow:0 4px 14px rgba(42,120,214,.25); border-color:#86b6ef; transform:translateY(-1px);
}
.chips{display:flex; flex-wrap:wrap; gap:6px; margin:4px 0 10px 0;}
.chip{background:#e7f0fc; color:#184f95 !important; border:1px solid #b7d3f6; border-radius:999px;
  padding:2px 10px; font-size:.8rem; font-weight:600;}
.hint{color:#6b6a66; font-size:.82rem; margin-top:-6px;}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# État des filtres
# Les valeurs "officielles" vivent dans flt_* (hors widgets) : elles survivent au
# changement de page et peuvent être modifiées à tout moment (clic sur un graphique).
# --------------------------------------------------------------------------- #
ss = st.session_state
for f in FILTRES:
    ss.setdefault(f"flt_{f}", [])
ss.setdefault("nav", PAGES[0])
ss.setdefault("nonce", 0)  # change la clé des graphiques pour effacer leur sélection

if "_goto" in ss:  # navigation demandée depuis un clic de graphique
    ss.nav = ss.pop("_goto")


def reset_filtres():
    for f in FILTRES:
        ss[f"flt_{f}"] = []
    ss.nonce += 1


def appliquer(page: str | None = None, **filtres):
    for f, v in filtres.items():
        ss[f"flt_{f}"] = v
    if page:
        ss.nav = page
    ss.nonce += 1


def _sync(f: str):
    ss[f"flt_{f}"] = ss[f"w_{f}"]


def filtre_widget(conteneur, f: str, label: str, options: list[str]):
    """Multiselect synchronisé avec flt_<f> (les valeurs hors options sont retirées)."""
    valeurs = [v for v in ss[f"flt_{f}"] if v in options]
    ss[f"flt_{f}"] = valeurs
    ss[f"w_{f}"] = valeurs
    conteneur.multiselect(label, options, key=f"w_{f}", placeholder="Tous",
                          on_change=_sync, args=(f,))


# --------------------------------------------------------------------------- #
# Données
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Chargement et comparaison des données…")
def charger(contenu: bytes | None):
    import io

    data = load_excel(io.BytesIO(contenu) if contenu else EXEMPLE)
    comp = compare(data["source"], data["cible"], data["groupes"])
    return data, comp


with st.sidebar:
    st.markdown("## 📦 Migration Référentiel")
    fichier = st.file_uploader("Fichier de migration (.xlsx)", type=["xlsx"])
    try:
        data, comp = charger(fichier.getvalue() if fichier else None)
    except Exception as e:  # noqa: BLE001
        st.error(f"Impossible de lire le fichier : {e}")
        st.stop()
    if not fichier:
        st.caption("Données d'exemple chargées.")

    st.radio("Navigation", PAGES, key="nav")
    st.divider()
    st.markdown("### Filtres")
    groupes_df = data["groupes"]
    filtre_widget(st, "domaine", "Domaine", sorted(comp[COL_DOMAINE].dropna().unique()))
    filtre_widget(st, "groupe", "Groupe d'attributs", list(dict.fromkeys(groupes_df["groupe_attributs"])))
    champs_dispo = groupes_df
    if ss.flt_groupe:
        champs_dispo = groupes_df[groupes_df["groupe_attributs"].isin(ss.flt_groupe)]
    filtre_widget(st, "champ", "Champ", [c for c in champs_dispo["champ"] if c in set(comp["champ"])])
    filtre_widget(st, "type", "Type d'écart", TYPES_ECART)
    st.button("🔄 Réinitialiser les filtres", on_click=reset_filtres, use_container_width=True,
              key="reset_sidebar")


def filtrer(df: pd.DataFrame, sauf: tuple[str, ...] = ()) -> pd.DataFrame:
    """Applique les filtres actifs, sauf ceux listés (pour les graphiques croisés)."""
    colonnes = {"domaine": COL_DOMAINE, "groupe": "groupe_attributs", "champ": "champ"}
    for f, col in colonnes.items():
        if f not in sauf and ss[f"flt_{f}"]:
            df = df[df[col].isin(ss[f"flt_{f}"])]
    return df


def ecarts(df: pd.DataFrame, sauf_type: bool = False) -> pd.DataFrame:
    e = df[df["ecart"]]
    if ss.flt_type and not sauf_type:
        e = e[e["type_ecart"].isin(ss.flt_type)]
    return e


# --------------------------------------------------------------------------- #
# Composants
# --------------------------------------------------------------------------- #
def kpi(col, key: str, label: str, valeur: str, sous_titre: str = "", delta: str | None = None,
        sens: str = "flat", accent: str = BLEU, on_click=None, args=(), kwargs=None,
        cta: str = "Voir le détail →"):
    """Carte KPI de hauteur fixe. Si on_click est fourni, toute la carte est cliquable."""
    pill = f'<span class="kpi-pill {sens}">{html.escape(delta)}</span>' if delta else ""
    cta = f'<span class="kpi-cta">{html.escape(cta)}</span>' if on_click else ""
    carte = f"""
<div class="kpi-card" style="--accent:{accent}">
  <div class="kpi-label">{html.escape(label)}</div>
  <div class="kpi-value">{html.escape(valeur)}</div>
  <div class="kpi-sub" title="{html.escape(sous_titre)}">{html.escape(sous_titre)}</div>
  <div class="kpi-foot">{pill}{cta}</div>
</div>"""
    with col.container(key=f"kpi_{key}" if on_click else None):
        st.markdown(carte, unsafe_allow_html=True)
        if on_click:
            st.button(label, key=f"btn_{key}", on_click=on_click, args=args, kwargs=kwargs or {})


def chips():
    noms = {"domaine": "Domaine", "groupe": "Groupe", "champ": "Champ", "type": "Type"}
    actifs = [f"{noms[f]} : {v}" for f in FILTRES for v in ss[f"flt_{f}"]]
    if actifs:
        st.markdown('<div class="chips">' + "".join(
            f'<span class="chip">{html.escape(a)}</span>' for a in actifs) + "</div>",
            unsafe_allow_html=True)
    else:
        st.markdown('<div class="chips"><span class="chip">Aucun filtre : périmètre complet</span></div>',
                    unsafe_allow_html=True)


def fmt(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ")


def pct(x: float) -> str:
    return f"{x:.1%}".replace(".", ",")


def layout(fig: go.Figure, hauteur: int = 320) -> go.Figure:
    fig.update_layout(height=hauteur, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                      bargap=0.35, clickmode="event+select", dragmode=False,
                      hoverlabel=dict(bgcolor="white", font_color="#0b0b0b"))
    fig.update_xaxes(showgrid=False, fixedrange=True)
    fig.update_yaxes(gridcolor="rgba(128,128,128,.15)", fixedrange=True)
    return fig


def barres(categories, valeurs, selection, horizontal=True, texte=None, survol="%{y}: %{x}"):
    couleurs = [BLEU if not selection else BLEU_FONCE if c in selection else BLEU_PALE for c in categories]
    kw = dict(y=categories, x=valeurs, orientation="h") if horizontal else dict(x=categories, y=valeurs)
    fig = go.Figure(go.Bar(**kw, marker=dict(color=couleurs, cornerradius=4), customdata=categories,
                           text=texte, textposition="outside", cliponaxis=False,
                           hovertemplate=survol + "<extra>Cliquer pour filtrer</extra>"))
    if horizontal:
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


def clic(fig: go.Figure, nom: str, hauteur: int = 320) -> list:
    """Affiche un graphique cliquable et renvoie les catégories cliquées."""
    ev = st.plotly_chart(layout(fig, hauteur), use_container_width=True, on_select="rerun",
                         selection_mode="points", key=f"{nom}_{ss.nonce}",
                         config={"displayModeBar": False})
    pts = (ev or {}).get("selection", {}).get("points", []) if ev else []
    return [p.get("customdata") for p in pts if p.get("customdata") is not None]


def basculer(f: str, valeur, page: str | None = None):
    """Clic sur un graphique : sélectionne la valeur (ou la retire si déjà seule sélectionnée)."""
    courant = ss[f"flt_{f}"]
    ss[f"flt_{f}"] = [] if courant == [valeur] and not page else [valeur]
    ss.nonce += 1
    if page:
        ss["_goto"] = page
    st.rerun()


# --------------------------------------------------------------------------- #
# Vue Globale
# --------------------------------------------------------------------------- #
def vue_globale():
    titre = "Vue Globale"
    if ss.flt_domaine:
        titre += " — " + ", ".join(ss.flt_domaine)
    st.title(titre)
    st.caption("Cliquez sur un graphique pour filtrer tout le rapport ; cliquez sur une carte KPI "
               "pour ouvrir le détail pré-filtré.")
    chips()

    cf = filtrer(comp)
    ec = ecarts(cf)
    art = cf.drop_duplicates(CLE)
    n_art = len(art)
    non_migres = art[art["type_ecart"] == "Article non migré"][CLE].nunique()
    n_migres = n_art - non_migres
    art_ecart = ec[CLE].nunique()
    art_conformes = n_art - cf[cf["ecart"]][CLE].nunique()
    champs_scope = cf["champ"].nunique()
    champs_ecart = ec["champ"].nunique()
    comparaisons = cf[cf["type_ecart"] != "Article non migré"]
    valeurs_ecart = ec[ec["type_ecart"] != "Article non migré"]
    taux_valeurs = 1 - len(valeurs_ecart) / len(comparaisons) if len(comparaisons) else 1

    # Variations M vs M-1 depuis le suivi mensuel (si disponible)
    d_migres = d_ecart = None
    suivi = data["suivi"]
    if suivi is not None and len(suivi):
        s = suivi
        if ss.flt_domaine and "domaine" in s:
            s = s[s["domaine"].isin(ss.flt_domaine)]
        s = s.groupby("mois").sum(numeric_only=True).sort_index()
        if len(s) >= 2:
            d_migres = s["articles_migres"].iloc[-1] - s["articles_migres"].iloc[-2]
            d_ecart = s["articles_en_ecart"].iloc[-1] - s["articles_en_ecart"].iloc[-2]

    def signe(v):
        return f"{'+' if v >= 0 else '−'}{fmt(abs(v))} vs M-1"

    detail = PAGES[1]
    cols = st.columns(6)
    kpi(cols[0], "total", "Articles à migrer", fmt(n_art), "périmètre filtré",
        on_click=appliquer, kwargs=dict(page=detail))
    kpi(cols[1], "migres", "Articles migrés", fmt(n_migres), f"{pct(n_migres / n_art if n_art else 0)} du périmètre",
        delta=signe(d_migres) if d_migres is not None else None,
        sens="up" if (d_migres or 0) > 0 else "flat", accent=BON)
    kpi(cols[2], "non_migres", "Articles non migrés", fmt(non_migres), "absents de la cible",
        accent=CRITIQUE, on_click=appliquer, kwargs=dict(page=detail, type=["Article non migré"]))
    kpi(cols[3], "conformes", "Articles conformes", pct(art_conformes / n_art if n_art else 0),
        f"{fmt(art_conformes)} articles sans écart", accent=BON)
    kpi(cols[4], "ecart", "Articles en écart", fmt(art_ecart), f"{fmt(champs_ecart)} / {champs_scope} champs touchés",
        delta=signe(d_ecart) if d_ecart is not None else None,
        sens="down" if (d_ecart or 0) > 0 else "up", accent=ALERTE,
        on_click=appliquer, kwargs=dict(page=detail))
    kpi(cols[5], "taux", "Conformité des valeurs", pct(taux_valeurs),
        f"{fmt(len(valeurs_ecart))} valeurs en écart", accent=BLEU,
        on_click=appliquer, kwargs=dict(page=detail))

    st.write("")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Articles en écart par groupe d'attributs")
        g = ecarts(filtrer(comp, sauf=("groupe", "champ"))).groupby("groupe_attributs")[CLE].nunique()
        g = g.reindex(list(dict.fromkeys(data["groupes"]["groupe_attributs"])), fill_value=0)
        g = g.sort_values(ascending=False)
        sel = clic(barres(list(g.index), list(g.values), ss.flt_groupe, texte=[fmt(v) for v in g.values],
                          survol="%{y} : %{x} articles"), "ch_groupe")
        if sel:
            basculer("groupe", sel[0])
    with c2:
        st.subheader("Taux d'articles en écart par domaine")
        d = filtrer(comp, sauf=("domaine",))
        tot = d.groupby(COL_DOMAINE)[CLE].nunique()
        err = ecarts(d).groupby(COL_DOMAINE)[CLE].nunique().reindex(tot.index, fill_value=0)
        taux = (err / tot).sort_values(ascending=False)
        sel = clic(barres(list(taux.index), list(taux.values), ss.flt_domaine, horizontal=False,
                          texte=[pct(v) for v in taux.values], survol="%{x} : %{y:.1%}"), "ch_domaine")
        if sel:
            basculer("domaine", sel[0])

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Top 10 des champs en écart")
        st.markdown('<div class="hint">Un clic ouvre le détail du champ.</div>', unsafe_allow_html=True)
        t = ecarts(filtrer(comp, sauf=("champ",))).groupby("champ")[CLE].nunique()
        t = t.sort_values(ascending=False).head(10)
        sel = clic(barres(list(t.index), list(t.values), ss.flt_champ, texte=[fmt(v) for v in t.values],
                          survol="%{y} : %{x} articles"), "ch_champ")
        if sel:
            basculer("champ", sel[0], page=detail)
    with c4:
        st.subheader("Répartition par type d'écart")
        ty = ecarts(cf, sauf_type=True).groupby("type_ecart")[CLE].size()
        ty = ty.reindex(TYPES_ECART, fill_value=0)
        sel = clic(barres(list(ty.index), list(ty.values), ss.flt_type, texte=[fmt(v) for v in ty.values],
                          survol="%{y} : %{x} valeurs"), "ch_type")
        if sel:
            basculer("type", sel[0])

    st.subheader("Carte des écarts : domaine × groupe d'attributs")
    st.markdown('<div class="hint">% d\'articles en écart. Un clic filtre sur le domaine et le groupe.</div>',
                unsafe_allow_html=True)
    m = filtrer(comp, sauf=("domaine", "groupe", "champ"))
    tot = m.groupby([COL_DOMAINE, "groupe_attributs"])[CLE].nunique()
    err = ecarts(m).groupby([COL_DOMAINE, "groupe_attributs"])[CLE].nunique().reindex(tot.index, fill_value=0)
    mat = (err / tot).reset_index(name="taux")
    fig = go.Figure(go.Scatter(
        x=mat["groupe_attributs"], y=mat[COL_DOMAINE], mode="markers+text",
        marker=dict(symbol="square", size=46, color=mat["taux"], cmin=0,
                    colorscale=[[0, "#cde2fb"], [0.5, "#3987e5"], [1, "#0d366b"]],
                    line=dict(width=2, color="white"), showscale=False),
        text=[pct(v) for v in mat["taux"]],
        textfont=dict(color=["#0b0b0b" if v < mat["taux"].max() * 0.45 else "white" for v in mat["taux"]]),
        customdata=list(zip(mat[COL_DOMAINE], mat["groupe_attributs"])),
        hovertemplate="%{y} · %{x} : %{text}<extra>Cliquer pour filtrer</extra>"))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    sel = clic(fig, "ch_matrice", hauteur=80 + 60 * mat[COL_DOMAINE].nunique())
    if sel:
        dom, grp = sel[0]
        ss.flt_domaine, ss.flt_groupe = [dom], [grp]
        ss.nonce += 1
        st.rerun()

    if suivi is not None and len(suivi):
        s = suivi
        if ss.flt_domaine and "domaine" in s:
            s = s[s["domaine"].isin(ss.flt_domaine)]
        s = s.groupby("mois").sum(numeric_only=True).sort_index().reset_index()
        c5, c6 = st.columns(2)
        with c5:
            st.subheader("Avancement de la migration")
            fig = go.Figure()
            if "articles_prevus" in s:
                fig.add_scatter(x=s["mois"], y=s["articles_prevus"], name="Prévu", mode="lines",
                                line=dict(color=GRIS, width=2, dash="dash"))
            fig.add_scatter(x=s["mois"], y=s["articles_migres"], name="Réel", mode="lines+markers",
                            line=dict(color=BLEU, width=2), marker=dict(size=8))
            fig = layout(fig)
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.1), hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        with c6:
            st.subheader("Évolution des articles en écart")
            fig = go.Figure(go.Scatter(x=s["mois"], y=s["articles_en_ecart"], mode="lines+markers",
                                       line=dict(color=ALERTE, width=2), marker=dict(size=8),
                                       name="Articles en écart"))
            fig = layout(fig)
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# --------------------------------------------------------------------------- #
# Détail Migration
# --------------------------------------------------------------------------- #
def vue_detail():
    h1, h2 = st.columns([4, 1], vertical_alignment="center")
    h1.title("Détail Migration")
    h2.button("🔄 Réinitialiser les filtres", on_click=reset_filtres, type="primary",
              use_container_width=True, key="reset_detail")
    chips()

    cf = filtrer(comp)
    ec = ecarts(cf)
    n_art = cf[CLE].nunique()
    art_ecart = ec[CLE].nunique()
    valeurs = ec[ec["type_ecart"] != "Article non migré"]
    comparaisons = cf[cf["type_ecart"] != "Article non migré"]
    taux = 1 - len(valeurs) / len(comparaisons) if len(comparaisons) else 1

    non_migres = cf[cf["type_ecart"] == "Article non migré"][CLE].nunique()
    cols = st.columns(6)
    kpi(cols[0], "d_art", "Articles analysés", fmt(n_art), "selon les filtres")
    kpi(cols[1], "d_ecart", "Articles en écart", fmt(art_ecart), pct(art_ecart / n_art if n_art else 0) +
        " des articles", accent=ALERTE)
    kpi(cols[2], "d_champs", "Champs en écart", f"{ec['champ'].nunique()} / {cf['champ'].nunique()}",
        "champs avec au moins 1 écart", accent=ALERTE)
    kpi(cols[3], "d_val", "Valeurs en différence", fmt(len(valeurs)), "hors articles non migrés",
        accent=CRITIQUE)
    kpi(cols[4], "d_taux", "Conformité des valeurs", pct(taux), f"{fmt(len(comparaisons))} valeurs comparées",
        accent=BON)
    kpi(cols[5], "d_non_migres", "Articles non migrés", fmt(non_migres), "absents de la cible",
        accent=CRITIQUE, on_click=appliquer, kwargs=dict(type=["Article non migré"]), cta="Filtrer →")

    if ec.empty:
        st.success("✅ Aucun écart sur ce périmètre.")
        return

    st.subheader("Champs en écart")
    st.markdown('<div class="hint">Sélectionnez une ligne pour filtrer sur ce champ.</div>',
                unsafe_allow_html=True)
    tot_champ = cf.groupby(["groupe_attributs", "champ"])[CLE].nunique()
    synth = ec.groupby(["groupe_attributs", "champ"]).agg(
        articles_en_ecart=(CLE, "nunique"),
        type_principal=("type_ecart", lambda s: s.value_counts().index[0]),
    )
    synth["taux_ecart"] = synth["articles_en_ecart"] / tot_champ.reindex(synth.index)
    exemples = valeurs.drop_duplicates(["groupe_attributs", "champ"]).set_index(["groupe_attributs", "champ"])
    synth["exemple"] = (exemples["valeur_source"] + "  →  " + exemples["valeur_cible"]).reindex(synth.index)
    synth = synth.sort_values("articles_en_ecart", ascending=False).reset_index()
    ev = st.dataframe(
        synth, hide_index=True, use_container_width=True, on_select="rerun",
        selection_mode="single-row", key=f"tab_champs_{ss.nonce}",
        column_config={
            "groupe_attributs": "Groupe d'attributs", "champ": "Champ",
            "articles_en_ecart": st.column_config.NumberColumn("Articles en écart"),
            "taux_ecart": st.column_config.ProgressColumn("% articles en écart", format="percent",
                                                          min_value=0, max_value=1),
            "type_principal": "Type principal", "exemple": "Exemple (source → cible)",
        })
    rows = ev.selection.rows if ev else []
    if rows:
        basculer("champ", synth.iloc[rows[0]]["champ"])

    st.subheader("Valeurs en différence les plus fréquentes")
    freq = (valeurs.groupby(["champ", "valeur_source", "valeur_cible"]).size()
            .sort_values(ascending=False).head(15).reset_index(name="occurrences"))
    st.dataframe(freq, hide_index=True, use_container_width=True, column_config={
        "champ": "Champ", "valeur_source": "Valeur source", "valeur_cible": "Valeur cible",
        "occurrences": "Occurrences"})

    st.subheader("Liste des écarts")
    recherche = st.text_input("🔎 Rechercher un code article", key="recherche", placeholder="ex. ART100012")
    liste = ec
    if recherche:
        liste = liste[liste[CLE].str.contains(recherche.strip(), case=False, regex=False)]
    liste = liste[[CLE, COL_DOMAINE, "groupe_attributs", "champ", "valeur_source", "valeur_cible", "type_ecart"]]
    st.caption(f"{fmt(len(liste))} lignes")
    st.dataframe(liste, hide_index=True, use_container_width=True, height=380, column_config={
        CLE: "Code article", COL_DOMAINE: "Domaine", "groupe_attributs": "Groupe d'attributs",
        "champ": "Champ", "valeur_source": "Valeur source", "valeur_cible": "Valeur cible",
        "type_ecart": "Type d'écart"})
    st.download_button("⬇️ Exporter les écarts (CSV)", liste.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="ecarts_migration.csv", mime="text/csv")

    st.subheader("Comparaison article par article")
    articles = sorted(liste[CLE].unique())
    if articles:
        choix = st.selectbox("Article", articles, key="article_detail")
        a = cf[cf[CLE] == choix][["groupe_attributs", "champ", "valeur_source", "valeur_cible", "type_ecart"]]
        a = a.assign(statut=a["type_ecart"].map(lambda t: f"❌ {t}" if t else "✅ Conforme"))

        def surligner(row):
            style = "background-color:#fbe4e4; color:#0b0b0b" if row["type_ecart"] else ""
            return [style] * len(row)

        st.dataframe(a.style.apply(surligner, axis=1), hide_index=True, use_container_width=True, column_config={
                         "groupe_attributs": "Groupe d'attributs", "champ": "Champ",
                         "valeur_source": "Valeur source", "valeur_cible": "Valeur cible",
                         "type_ecart": None, "statut": "Statut"})


if ss.nav == PAGES[0]:
    vue_globale()
else:
    vue_detail()
