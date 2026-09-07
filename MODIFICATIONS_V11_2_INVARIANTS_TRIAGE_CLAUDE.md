# V11.2 — Invariants stricts du tri Claude

Cette correction verrouille une incohérence observée lors du re-tri réel avec Claude : certaines réponses LLM pouvaient contenir une catégorie `off_topic`, `noise` ou `competitor_only` tout en laissant `relevant=true`.

## Règles désormais garanties

- `off_topic` => `relevant=false`, `reply_recommended=false`, sentiment neutral, exclu du score.
- `noise` => `relevant=false`, `reply_recommended=false`, sentiment neutral, exclu du score.
- `competitor_only` => `relevant=false`, `reply_recommended=false`, sentiment neutral, exclu du score ARMA.
- Si les règles métier strictes détectent au contraire un vrai signal ARMA et que Claude renvoie par erreur une catégorie exclue, la catégorie métier cohérente issue des règles remplace la catégorie exclue avant stockage.
- Les quality flags contradictoires (`comment_relevant`, `comment_actionable`, `reputation_signal`, `negative_alert_candidate`) sont retirés d'un résultat finalement exclu.

Trois tests de non-régression vérifient ces invariants.

## Réparation sans repayer 371 appels Claude

Après un run Claude déjà terminé, exécuter :

```powershell
.\scripts\repair_inconsistent_comment_triage.ps1
```

Ce script ne contacte pas Anthropic. Il normalise uniquement les résultats déjà stockés qui ont une catégorie exclue mais un indicateur `relevant/reply/sentiment` incohérent, ferme les alertes correspondantes et recalcule le score.
