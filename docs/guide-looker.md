# Guide Looker Studio — brancher les dashboards sur BigQuery

Ce guide te fait construire, pas à pas, 3 visuels publics à partir des tables `marts` déjà présentes dans BigQuery. Aucun calcul à faire dans Looker : les tables sont pré-agrégées.

Prérequis : être connecté à Looker Studio avec le **même compte Google** que celui qui a accès au projet BigQuery `thef1lab`.

---

## Étape 1 · Créer la source de données BigQuery

1. Va sur **[lookerstudio.google.com](https://lookerstudio.google.com)**.
2. Bouton **Create** (en haut à gauche) → **Data source**.
3. Dans la liste des connecteurs, choisis **BigQuery** (connecteur officiel Google).
4. Autorise l'accès si Looker te le demande.
5. Sélectionne en colonnes : **My Projects** → `thef1lab` → dataset `marts` → table `mart_pit_stop_performance`.
6. En haut à droite, clique **Connect**.
7. L'écran des champs s'affiche. Vérifie que `median_stop_seconds`, `avg_stop_seconds` etc. sont bien reconnus comme des nombres (icône `123`). Clique **Create Report** (en haut à droite) → **Add to report**.

> 💡 **Une source = une table.** On répétera l'étape 1 pour chaque table marts. Alternative : dans une même source tu peux utiliser une *Custom Query* (SQL), mais ici nos tables sont déjà prêtes, donc on reste sur le mode simple « une table ».

---

## Étape 2 · Le réglage crucial pour le partage public

Par défaut, Looker interroge BigQuery avec les identifiants de **celui qui regarde** le rapport. Un visiteur anonyme n'a pas accès à ton BigQuery → il verrait une erreur. Il faut basculer sur **tes** identifiants :

1. Dans Looker, ouvre **Resource** (menu du haut) → **Manage added data sources**.
2. Sur ta source, clique **Edit**.
3. En haut, trouve **Data credentials** → passe de *Viewer's credentials* à **Owner's credentials**.
4. Enregistre.

À faire pour **chaque** source de données que tu ajoutes.

> ⚠️ Ça veut dire que les requêtes des visiteurs consomment **ton** quota BigQuery (le free tier 1 To/mois). Vu la taille des marts (quelques Ko à Mo), c'est totalement négligeable.

---

## Étape 3 · Visuel 1 — Performance des arrêts au stand par équipe

Source : `mart_pit_stop_performance`. Type : **graphique à barres**.

1. Menu **Insert** → **Bar chart**. Dessine-le sur la page.
2. Dans le panneau **Setup** à droite :
   - **Dimension** : `team_name`
   - **Metric** : `median_stop_seconds` (retire les autres métriques par défaut)
3. Panneau **Style** → active **Sort** ascendant sur la métrique (l'équipe la plus rapide en haut).
4. Optionnel : ajoute `fastest_stop_seconds` comme 2ᵉ métrique pour comparer médiane vs meilleur arrêt.

Lecture attendue : McLaren / Ferrari en tête (~2,5s), les nouvelles équipes plus lentes.

---

## Étape 4 · Visuel 2 — Évolution du championnat

Source : `mart_driver_standings`. Type : **série temporelle (line chart)**.

1. Ajoute cette table comme **nouvelle source** (répète étapes 1 & 2).
2. Menu **Insert** → **Time series chart**.
3. Dans **Setup** :
   - **Dimension (axe X)** : `race_date`
   - **Breakdown dimension** : `driver_name` (une courbe par pilote)
   - **Metric** : `cumulative_points`
4. Style → limite éventuellement aux 6-8 pilotes de tête (sinon le graphe est chargé) via un **filtre** sur `driver_name`.

Lecture attendue : les courbes qui montent manche après manche, le leader se détachant.

---

## Étape 5 · Visuel 3 — Rythme & régularité des pilotes

Source : `mart_driver_pace`. Deux options selon ce que tu veux montrer :

**Option simple — tableau classé** (rapide à faire) :
- **Insert → Table**
- Dimension : `driver_name`, `meeting_name`
- Metrics : `median_lap_seconds`, `lap_time_stddev`
- Ajoute un **filtre** ou un **contrôle de date/liste** sur `meeting_name` pour choisir une course.

**Option avancée — nuage de points** (plus visuel) :
- **Insert → Scatter chart**
- Dimension : `driver_name`
- Metric X : `median_lap_seconds` (rapidité — plus à gauche = plus rapide)
- Metric Y : `lap_time_stddev` (régularité — plus bas = plus régulier)
- Le pilote idéal est en **bas à gauche** : rapide ET régulier.

---

## Étape 6 · Publier en lien public

1. En haut à droite du rapport : **Share** → **Manage access**.
2. Section **General access** : passe sur **Anyone with the link** → rôle **Viewer**.
3. Copie le lien. N'importe qui peut maintenant voir le dashboard sans compte Google.

---

## Étape 7 · Intégrer dans ta page Notion (portfolio)

1. Dans Notion, sur ta page projet, tape `/embed` puis Entrée.
2. Colle le lien public Looker.
3. Notion affiche le dashboard en direct dans la page (iframe interactive).

Résultat : le dashboard vit dans Looker (connecté à BigQuery), et ton portfolio Notion l'affiche sans copier-coller de captures.

---

## Récap des sources à créer

| Source Looker (= table BigQuery `marts`) | Visuel |
| --- | --- |
| `mart_pit_stop_performance` | Barres — arrêts au stand par équipe |
| `mart_driver_standings` | Courbes — évolution championnat |
| `mart_driver_pace` | Tableau ou nuage de points — rythme/régularité |

> ✅ **À retenir :** chaque table marts = une source de données Looker en *Owner's credentials*. Une fois branché, il n'y a plus rien à recoder : quand le pipeline recharge BigQuery chaque jour, Looker affiche automatiquement les données à jour au prochain rafraîchissement.
