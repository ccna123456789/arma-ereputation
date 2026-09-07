# V11 — Filtrage propre des commentaires Facebook

Cette version corrige trois points du portail Réputation Sociale.

## 1. La période Facebook suit exactement la période du score

Si le score affiche par exemple `2026-08-21 → 2026-08-27`, les blocs suivants utilisent automatiquement cette même période :

- résumé des commentaires Facebook ;
- détail des commentaires par publication ;
- alertes affichées dans le portail.

Pour un **commentaire social**, la date utilisée est `mentions.collected_at`, c'est-à-dire la **première collecte dans ARMA**, et non la date de publication/envoi du commentaire sur Facebook.

Les autres contenus (articles/posts) conservent la date de publication, avec la date de collecte comme secours.

## 2. Une resynchronisation ne rend plus un vieux commentaire « nouveau »

Avant cette version, Apify remplaçait `collected_at` lorsqu'un commentaire déjà connu était revu. Un commentaire ancien pouvait donc réapparaître artificiellement dans la semaine courante.

Désormais :

- création d'un nouveau commentaire → `collected_at` est fixé ;
- commentaire déjà connu → `collected_at` est conservé ;
- `last_seen_at` est stocké dans les métadonnées pour tracer la dernière observation ;
- une réparation des anciennes dates utilise la plus ancienne preuve système disponible (ancienne analyse ou alerte).

## 3. Filtrage hors-sujet plus strict

Le simple fait qu'un commentaire soit écrit sous une publication rattachée à ARMA ne suffit plus pour l'inclure dans la réputation.

Les demandes sans lien avec la propreté urbaine (logement social, emploi, visa, aide administrative, etc.) sont exclues. Les questions et suggestions doivent maintenant comporter un signal explicite ARMA/propreté/service concerné.

La politique de tri devient :

`final-actionable-comments-v3-strict-context`

Les règles locales deviennent :

`comment-rules-final-v2`

## 4. Claude reste configuré

`COMMENT_TRIAGE_PROVIDER=claude` reste supporté. Si l'API Anthropic est temporairement indisponible ou si le crédit est épuisé :

1. le premier échec Claude est détecté ;
2. le run continue avec les règles strictes locales ;
3. la collecte/tri ne casse plus ;
4. au prochain run, Claude est essayé de nouveau automatiquement.

Quand le crédit Claude est rechargé, aucune modification de code n'est nécessaire.

## 5. Recalcul du score

La formule reste la même, y compris le poids `0.25` des commentaires sociaux, mais sa version est maintenant :

`v4_collection_date_social_comments`

Cela évite d'afficher un ancien snapshot calculé avec l'ancienne politique temporelle.

## Première utilisation après remplacement du projet

Conservez votre `.env` local (il n'est volontairement pas inclus dans le ZIP de livraison), puis lancez :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\reprocess_facebook_comments.ps1
```

Ce script ne relance pas Apify. Il effectue :

1. réparation des anciennes dates de première collecte ;
2. reclassification de tous les commentaires ;
3. nettoyage / création des alertes ;
4. recalcul du score hebdomadaire.

Ensuite lancez le backend/frontend et rechargez le portail avec `Ctrl + F5`.
