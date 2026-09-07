# V11.5 — Couleur par sentiment, validation des alertes, navigation par semaine

Trois demandes de l'encadrant sont traitées ici.

---

## 1. La couleur d'une alerte vient de son sentiment

Avant, la couleur de la carte venait de la **sévérité** (`high` / `medium` / `low`).
Un commentaire neutre mais très diffusé apparaissait donc en rouge, ce qui rendait la
lecture trompeuse.

Désormais :

| Sentiment | Couleur | Classe CSS |
|---|---|---|
| Négatif | Rouge `#D94F4F` | `.alert.sentiment-negative` |
| Positif | Vert `#10B981` | `.alert.sentiment-positive` |
| Neutre | Bleu `#2563EB` | `.alert.sentiment-neutral` |
| Non classé | Gris `#94A3B8` | `.alert.sentiment-unknown` |

Le bleu a été retenu pour le neutre : il se distingue clairement du rouge et du vert
et ne suggère aucun danger, contrairement à l'orange.

Chaque carte porte en plus une pastille explicite (`🔴 Négatif`, `🟢 Positif`,
`🔵 Neutre`, `⚪ Non classé`) et une légende figure en haut de la section 3.
La sévérité reste affichée en texte dans la ligne de métadonnées.

### Origine du sentiment

`GET /api/alerts` renvoie maintenant `sentiment_label` pour **toutes** les alertes,
et non plus seulement pour les commentaires Facebook :

- commentaire social → `raw_payload._comment_triage.sentiment` (tri dédié, calculé sur
  le texte du commentaire) ;
- tout autre contenu → `MentionAnalysis.sentiment_label` de l'analyse NLP courante,
  récupérée par un `outerjoin` ;
- aucun des deux → `null`, la carte reste grise plutôt que d'afficher une couleur
  fausse.

Le champ `sentiment_source` (`comment_triage`, `mention_analysis`, `unknown`) accompagne
la valeur pour la traçabilité.

Quand plusieurs alertes sont regroupées en un seul événement, la carte prend le
sentiment le plus défavorable : un groupe contenant une mention négative reste rouge.

---

## 2. Bouton « Valider »

Chaque carte d'alerte porte un bouton **`✅ Valider — alerte traitée`** accompagné d'un
champ de note facultatif (« réponse envoyée », « appel passé », « sans suite »…).

- Le clic appelle `PATCH /api/alerts/{id}/status` avec `status=resolved`.
- L'alerte **n'est jamais supprimée** : elle passe en état traité et affiche un bandeau
  vert `✔ Alerte traitée le JJ/MM/AAAA par <utilisateur>` suivi de la note saisie.
- Un bouton **`Rouvrir`** annule la validation et efface la trace, pour corriger une
  erreur de manipulation.

### Traçabilité

`AlertStatusUpdate` accepte deux champs facultatifs, `note` et `validated_by`.
L'identité peut aussi venir de l'en-tête `X-ARMA-User` (le portail envoie
`window.ARMA_USER`, `portail` par défaut). Le tout est stocké dans la colonne
`metadata` de l'alerte, donc **aucune migration de base n'est nécessaire**.

`AlertResponse` expose `is_handled`, `validated_by`, `validated_at`, `validation_note`.

### Retrouver une alerte validée

`GET /api/alerts` acceptait uniquement un statut unique et le portail demandait
toujours `status=open` : une alerte validée disparaissait donc définitivement de
l'écran. Le paramètre `status` accepte maintenant :

| Valeur | Effet |
|---|---|
| `open` | alertes à traiter (défaut) |
| `handled` | `acknowledged` + `resolved` + `ignored` |
| `all` | aucun filtre |
| `resolved,acknowledged` | liste explicite |

Un sélecteur **À traiter / Traitées / Toutes** est disponible en haut de la section
Alertes.

La distinction métier existante est conservée : depuis le brouillon de réponse, une
alerte de simple surveillance reste marquée « analysée » (`acknowledged`) et une alerte
appelant une réponse « traitée » (`resolved`). Les deux comptent comme traitées.

---

## 3. Navigation par semaine — le problème des périodes

### Cause exacte

Le tableau de bord appelait `/api/reputation/score` **sans période**. Le backend
répondait par `ORDER BY period_end DESC LIMIT 1`, c'est-à-dire toujours le dernier
snapshot calculé. Toutes les autres sections (commentaires Facebook, détail par
publication, alertes, benchmark) réutilisaient cette période.

Conséquence : dès l'exécution du workflow le lundi, l'écran basculait sur la nouvelle
semaine et les nouveautés de la semaine x-1 devenaient **invisibles**.

Les données n'ont jamais été perdues : elles restent en base, rattachées à leur période
par la date de publication réelle (`manual_published_at` / `published_at`, règle V11.4).
Seule l'interface ne savait pas les redemander.

### Nouvel endpoint

```
GET /api/reputation/periods?organization=ARMA&period_type=weekly&limit=26
```

Retourne les semaines consultables, de la plus récente à la plus ancienne :

```json
{
  "period_start": "2026-08-17", "period_end": "2026-08-23",
  "period_type": "weekly", "label": "Semaine 34 · 17/08/2026 → 23/08/2026",
  "has_snapshot": true, "reputation_score": 55.0, "mention_count": 7,
  "open_alerts": 6, "handled_alerts": 0, "total_alerts": 6, "is_latest": false
}
```

La liste fusionne **deux sources** :

1. les snapshots déjà calculés par le pipeline ;
2. les semaines civiles (lundi → dimanche) couvertes par des dates de publication
   réelles.

La seconde est indispensable : une semaine peut contenir des commentaires et des alertes
sans qu'aucun score n'ait été calculé, si le workflow n'a pas tourné ce lundi-là. Sans
elle, cette semaine resterait invisible.

Les compteurs d'alertes appliquent exactement la même règle de visibilité que la liste
des alertes (fonction partagée `alert_is_displayable`), pour qu'un même chiffre soit
annoncé partout.

### Score d'une semaine précise

`/api/reputation/score` accepte maintenant `period_start` et `period_end`. Sans ces
paramètres, le comportement reste inchangé (dernière période calculée).

Si aucun score n'existe pour la semaine demandée, l'API répond 404 avec un message
explicite — et **le portail continue d'afficher les alertes et les commentaires de cette
semaine**. Un score manquant ne masque plus la collecte.

### Interface

Une barre **Période analysée** figure en haut des deux tableaux de bord :

```
◀ Semaine précédente | [Semaine 34 · 17/08/2026 → 23/08/2026 · score 55/100 · 6 à traiter] | Semaine suivante ▶ | Dernière semaine
```

- le choix pilote **toutes** les sections : score, jauge, commentaires Facebook, détail
  par publication, alertes, benchmark concurrents ;
- un indicateur signale « Semaine antérieure — collecte conservée » quand on n'est pas
  sur la dernière semaine ;
- dans la section 2, cliquer sur une ligne de l'historique affiche cette semaine ;
- valider une alerte met immédiatement à jour les compteurs du sélecteur.

La même barre a été ajoutée à `MarketingContenuARMA.html`, qui présentait exactement le
même défaut sur la zone Veille, les angles et les posts.

---

## 4. Ordre d'affichage des alertes

Les alertes sont triées **négatif → positif → neutre → non classé**, les plus
urgentes en tête. À sentiment égal, le contenu publié le plus récemment apparaît en
premier. Un intertitre (`🔴 Alertes négatives`, `🟢 Alertes positives`,
`🔵 Alertes neutres`) sépare les groupes. Le même ordre s'applique aux commentaires
listés sous chaque publication Facebook.

---

## 5. Angles et brouillons Marketing invisibles

### Symptôme

Les sections « Angles stratégiques retenus » et « Brouillons bilingues à valider »
étaient vides pour **toutes** les semaines, alors que la base contient 71 angles et
168 brouillons.

### Cause

Le filtre de période exigeait qu'au moins une preuve du brouillon ait été publiée
dans la fenêtre :

```sql
coalesce(manual_published_at, published_at) >= start AND < end
```

Or **les 280 liens de preuve pointent vers des mentions sans date de publication**
(`published_at = NULL`, `published_at_confidence = unknown`) : beaucoup de sources
web collectées via Serper n'exposent aucune date exploitable. En SQL, comparer NULL
à une borne est toujours faux, donc aucun brouillon ne passait le filtre, quelle que
soit la semaine demandée.

### Correctif

La fonction `evidence_period_filter` (dans `backend/api/content.py`) applique
désormais deux règles :

1. **Règle principale, inchangée (V11.4)** — l'angle ou le brouillon appartient à la
   semaine si au moins une de ses preuves y a été publiée. Un brouillon dont les
   sources sont datées hors période reste masqué.
2. **Repli** — si *aucune* preuve n'a de date de publication exploitable, l'élément
   est rattaché à sa **semaine de production** (`generated_at`). Ses sources restent
   affichées, date manquante comprise, pour vérification manuelle.

Le résultat sur la base actuelle :

| Semaine | Angles | Brouillons |
|---|---|---|
| 24/08 → 30/08 | 1 | 8 |
| 17/08 → 23/08 | 0 | 0 |
| 10/08 → 16/08 | 1 | 8 |
| 20/07 → 26/07 | 3 | 8 |

La semaine 17/08 → 23/08 reste vide, mais légitimement : aucun run n8n n'a eu lieu
cette semaine-là (runs du 25/07, 10/08, 28/08 et 31/08). Les messages de la page
l'expliquent maintenant explicitement au lieu de dire « exécutez le workflow ».

---

## 6. Semaines affichées « score non calculé »

Trois situations différentes se cachaient derrière ce libellé.

### a. Formule obsolète — 97 snapshots ignorés

Le portail ne lit que les snapshots portant `formula_version = v5_calendar_week_publication_date`.
La base en contenait 10 sous cette version, contre 97 sous d'anciennes versions :

| Version | Snapshots |
|---|---|
| `v3_weighted_non_overlapping` | 65 |
| `v1` | 10 |
| `v2_comments_weighted` | 10 |
| `v4_collection_date_social_comments` | 10 |
| `sentiment-confidence-v1` | 2 |
| **`v5_calendar_week_publication_date`** | **10** |

Cette exclusion est **volontaire** : les anciens snapshots étaient des fenêtres
glissantes de 7 jours pouvant démarrer n'importe quel jour (`2026-08-22 → 2026-08-28`,
`2026-08-21 → 2026-08-27`…) et rattachaient les commentaires à leur date de collecte.
Les mélanger avec la formule courante produirait un historique incohérent, avec des
semaines qui se chevauchent.

### b. Le pipeline ne calcule qu'une semaine à la fois

`compute_reputation_snapshots` calcule la semaine écoulée et la précédente. Une
semaine où le workflow n'a pas tourné n'a donc jamais de score, même si ses mentions
et ses alertes sont bien en base.

**Correctif** : `scripts/backfill_weekly_scores.py` rejoue le calcul officiel, semaine
civile par semaine civile (lundi → dimanche), avec la formule courante. Il ne collecte
rien et ne modifie aucune mention : il n'écrit que des snapshots de score.

```powershell
python -m scripts.backfill_weekly_scores --dry-run   # liste sans rien écrire
python -m scripts.backfill_weekly_scores             # 26 dernières semaines
python -m scripts.backfill_weekly_scores --force     # recalcule aussi l'existant
```

Exécuté sur la base : 25 semaines recalculées.

| Semaine | Avant | Après |
|---|---|---|
| 10/08 → 16/08 | non calculé | 57,1/100 (4 mentions) |
| 03/08 → 09/08 | non calculé | 93,3/100 (6 mentions) |
| 27/07 → 02/08 | non calculé | 55,9/100 (11 mentions) |
| 20/07 → 26/07 | non calculé | 29,7/100 (53 mentions) |

### c. Semaine réellement vide

Une semaine sans aucune mention garde `reputation_score = null`. C'est intentionnel :
50/100 est la valeur neutre interne de la formule, l'afficher ferait croire à une
performance moyenne réelle.

Le portail distingue désormais les trois cas :

| Situation | Libellé affiché |
|---|---|
| Score disponible | `score 57/100` |
| Semaine calculée, zéro mention | `aucune mention` |
| Semaine jamais calculée | `score non calculé` + rappel du script de rattrapage |

---

## 7. Toute période est une semaine civile lundi → dimanche

`get_period_bounds` alignait la semaine sur le calendrier **uniquement** quand
aucune date n'était fournie. Avec un `period_end` explicite, il produisait encore
une fenêtre glissante de 7 jours se terminant à cette date :

```python
get_period_bounds("weekly", date(2026, 7, 31))   # vendredi
# avant : (2026-07-25 samedi, 2026-07-31 vendredi)
# apres : (2026-07-27 lundi,  2026-08-02 dimanche)
```

C'est ainsi que des périodes ne commençant pas un lundi pouvaient apparaître :
il suffisait qu'un appel du workflow, un rattrapage manuel ou une ancienne version
passe une date qui n'était pas un dimanche. Les anciens snapshots `v3` en base en
sont la trace (`2026-08-22 → 2026-08-28`, `2026-08-21 → 2026-08-27`…).

Deux verrous ont été posés :

1. **À l'écriture** — pour `period_type = "weekly"`, une date quelconque est ramenée
   à la semaine civile qui la contient (`get_calendar_week_bounds`). Les périodes
   quotidiennes et mensuelles restent des fenêtres glissantes.
2. **À la lecture** — le sélecteur ignore tout snapshot hebdomadaire qui n'est pas
   une semaine civile complète (`is_calendar_week`). Aucune donnée n'est masquée :
   la semaine civile qui contient ce snapshot reste proposée via les dates de
   publication.

Le test `test_weekly_previous_period_is_adjacent_and_non_overlapping` verrouillait
l'ancien comportement glissant ; il a été mis à jour en conservant son intention
(périodes adjacentes et non chevauchantes) et complété par
`test_weekly_bounds_always_run_monday_to_sunday`.

Vérification sur la base : **26 périodes proposées, 0 non alignée.**

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `backend/scoring/periods.py` | **nouveau** — construction des périodes consultables, comptage des alertes, `is_calendar_week` |
| `backend/scoring/formulas.py` | `get_calendar_week_bounds` — l'hebdomadaire est toujours aligné lundi → dimanche |
| `backend/api/reputation.py` | endpoint `/periods`, paramètres `period_start`/`period_end` sur `/score` |
| `backend/api/alerts.py` | sentiment pour toutes les alertes, filtre de statut étendu, trace de validation |
| `backend/api/schemas.py` | `PeriodOption`, champs de validation sur `AlertResponse`, `note`/`validated_by` sur `AlertStatusUpdate` |
| `backend/alerts/service.py` | `alert_is_displayable` — règle d'affichage partagée |
| `backend/api/content.py` | `evidence_period_filter` — angles et brouillons dont les preuves n'ont pas de date |
| `scripts/backfill_weekly_scores.py` | **nouveau** — recalcule le score des semaines antérieures |
| `frontend/ReputationSocialeARMA.html` | couleurs par sentiment, tri négatif → positif → neutre, bouton Valider, sélecteur de semaine, filtre de statut |
| `frontend/MarketingContenuARMA.html` | sélecteur de semaine, messages de section vide explicites |
| `tests/test_v11_5_sentiment_validation_periods.py` | **nouveau** — 24 tests |

Aucune migration Alembic n'est nécessaire : la trace de validation utilise la colonne
`metadata` (JSONB) déjà présente sur `alerts`.
