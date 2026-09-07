# V2.1 — Correction : commentaires Facebook absents de la section Alertes

## Cause racine

Le pipeline quotidien complet (n8n / `run_daily_pipeline`) enchaîne
correctement toutes les étapes nécessaires : collecte → nettoyage → tri des
commentaires (`triage_comments`) → analyse de sentiment → génération des
alertes (`generate_alerts`).

En revanche, les deux chemins utilisés pour tester ou synchroniser les
commentaires **manuellement** s'arrêtaient à la collecte :

- le script `scripts/sync_apify_facebook_comments.py` (et son wrapper
  `scripts/run_apify_comments.ps1`) ;
- l'endpoint `POST /api/facebook/comments/sync`.

Les deux appelaient uniquement `collect_facebook_comments()`. Les
commentaires étaient donc bien enregistrés en base de données (visibles via
`GET /api/facebook/comments`), mais :

- jamais triés → aucun champ `_comment_triage` sur la mention ;
- donc jamais associés à une `MentionAnalysis` "current" ;
- donc jamais éligibles à `generate_alerts_for_negative_mentions`, qui a
  besoin de cette analyse pour créer une ligne `Alert`.

Résultat concret observé : un post Facebook avec 360 commentaires pouvait
contenir des commentaires clairement actionnables (questions, critiques,
suggestions), collectés avec succès, mais **invisibles** dans la section
« Commentaires Facebook à traiter » du portail Réputation Sociale tant que le
pipeline n8n complet n'avait pas tourné derrière.

## Corrections apportées

1. **`scripts/sync_apify_facebook_comments.py`** — enchaîne désormais
   explicitement : collecte (Apify/Meta) → `triage_social_comments()` →
   `generate_alerts_for_negative_mentions()`, avec un résumé lisible à
   chaque étape.
2. **`backend/api/facebook.py` — `POST /api/facebook/comments/sync`** —
   même correctif côté API : la synchronisation manuelle depuis le portail
   déclenche maintenant la chaîne complète et retourne le détail de chaque
   étape (`triage`, `alerts`, `alerts_created`).
3. **`GET /api/facebook/comments/diagnostic`** — nouveaux compteurs :
   - `facebook_comments_not_yet_triaged`
   - `facebook_comments_actionable`
   - `facebook_comments_actionable_with_alert`
   - `facebook_comments_actionable_missing_alert`
   - `pipeline_health` (`"ok"` ou message d'action à effectuer)

   Ces compteurs permettent de détecter immédiatement un futur blocage à
   n'importe quelle étape de la chaîne, sans avoir à lire les logs.
4. **`docs/APIFY_FACEBOOK_COMMENTS.md`** — documentation mise à jour avec
   l'historique du correctif et la nouvelle section « Diagnostiquer un
   blocage ».
5. **`tests/test_facebook_comments_sync_chain.py`** (nouveau) — 3 tests qui
   verrouillent le comportement corrigé : la collecte manuelle (script ET
   endpoint) doit toujours enchaîner collecte → tri → alertes, dans cet
   ordre, y compris quand la collecte ne ramène aucun nouveau commentaire
   (`no_links`) — pour trier/alerter les commentaires déjà en base d'un run
   précédent.

## Vérification

- Suite de tests complète exécutée : **84/84 tests réussis** (81 tests
  existants + 3 nouveaux).
- Compilation Python vérifiée sur les fichiers modifiés
  (`backend/api/facebook.py`, `scripts/sync_apify_facebook_comments.py`).

## Ce qui ne change pas

- Le pipeline n8n quotidien (`ARMA_Pipeline_Quotidien_n8n.json`) était déjà
  correct : aucune modification nécessaire côté workflow.
- La logique de tri (`comment_triage`) et de calcul de sévérité
  (`backend/alerts/service.py`) n'a pas changé : c'est bien l'enchaînement
  des étapes qui posait problème, pas la logique métier elle-même.
