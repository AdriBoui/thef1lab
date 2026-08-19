# 07 · Comment Python et dbt s'articulent

**Le point clé : Python et dbt ne se parlent jamais directement.** Ils communiquent uniquement via BigQuery, qui sert de « boîte aux lettres » entre les deux.

## La séquence exacte (2 étapes séparées)

```
ÉTAPE 1 — PYTHON (ingestion)
  python -m ingestion.run
  ├─ appelle l'API OpenF1
  ├─ récupère le JSON
  └─ écrit dans BigQuery : raw_openf1.raw_laps, raw_drivers, etc.
  ▉ Python S'ARRÊTE ICI. Il ne connaît même pas l'existence de dbt.

        ⬇  seul lien entre les deux = les tables raw_* dans BigQuery

ÉTAPE 2 — DBT (transformation)
  dbt run
  ├─ lit les tables raw_* (que Python vient d'écrire)
  ├─ exécute les fichiers .sql
  └─ crée les tables staging.* puis marts.*
  ▉ dbt n'appelle jamais Python. Il lit juste ce qui est déjà dans BigQuery.
```

Le **moment de bascule** = quand Python a fini d'écrire et que `dbt run` démarre. Ce qui enchaîne les deux, c'est **GitHub Actions** : il lance d'abord Python, attend la fin, PUIS lance dbt.

## Quand les fichiers .sql entrent en jeu

Uniquement pendant `dbt run`, dans un ordre que **dbt calcule tout seul** :

```
1. stg_laps.sql      lit  raw_openf1.raw_laps     → crée  staging.stg_laps
2. stg_drivers.sql   lit  raw_openf1.raw_drivers  → crée  staging.stg_drivers
   ... (tout le staging d'abord)
3. dim_driver.sql    lit  staging.stg_drivers     → crée  marts.dim_driver
4. fact_laps.sql     lit  staging.stg_laps        → crée  marts.fact_laps
   ... (les marts ensuite, car ils dépendent du staging)
```

Comment dbt connaît l'ordre ? Dans un fichier `.sql` on écrit `{{ ref('stg_laps') }}` au lieu du nom de table en dur. Ce `ref()` dit « je dépends de stg_laps » → dbt en déduit l'ordre automatiquement. **Le SQL = le "quoi transformer".**

## Quand les fichiers .yaml entrent en jeu

Les YAML **ne transforment aucune donnée**. Deux rôles distincts :

| Fichier YAML | Rôle | Quand |
| --- | --- | --- |
| `sources.yml` | Dit à dbt *où* sont les tables raw | lu au début de `dbt run` |
| `schema.yml` | Déclare les **tests** (unique, not_null, relationships) | exécutés par `dbt test`, après `dbt run` |
| `dbt_project.yml` | Config générale (staging = vues, marts = tables) | lu à chaque commande dbt |

`dbt test` est une **troisième commande**, après `dbt run`, qui vérifie les tables déjà créées.

## Résumé

- **.py** = extraire et charger le brut (le "EL")
- **.sql** = transformer (le "T") — le cœur du métier
- **.yml** = configurer + tester (jamais transformer)

---

# 08 · Les credentials BigQuery

**Les DEUX outils ont besoin des credentials BigQuery**, chacun de son côté, car tous deux se connectent à BigQuery.

| | Se connecte pour… | S'authentifie via… |
| --- | --- | --- |
| **Python** | *écrire* les tables `raw_*` | la clé du service account |
| **dbt** | *lire* raw + *écrire* staging/marts | la même clé du service account |

Ils utilisent la **même clé** (le fichier JSON du service account `f1-pipeline`), mais la lisent différemment :

**Python** — via la variable d'environnement standard de Google (dans `.env`) :

```
GOOGLE_APPLICATION_CREDENTIALS=./credentials/thef1lab-xxxxx.json
```

**dbt** — via son propre fichier de config `profiles.yml` :

```yaml
thef1lab:
  outputs:
    prod:
      type: bigquery
      method: service-account
      project: thef1lab
      keyfile: ./credentials/thef1lab-xxxxx.json   # la même clé
      location: EU
```

## À retenir

dbt n'a aucune connaissance de Python ni de son `.env`. Il a sa propre config qui pointe vers la même clé. Les deux outils sont indépendants ; ils partagent seulement :

1. **la destination** (BigQuery, projet `thef1lab`)
2. **la clé d'accès** (le service account)

C'est pour ça que le service account a **deux rôles** :

- `BigQuery Data Editor` → droit d'écrire/créer des tables (Python ET dbt)
- `BigQuery Job User` → droit de lancer des requêtes SQL (surtout dbt)

Où vit cette config selon l'environnement :

- **En local** (Mac) : `~/.dbt/profiles.yml`
- **Dans GitHub Actions** : le workflow le recrée à la volée depuis le secret `GCP_SA_KEY`.
