# V10.4 — Commentaires Facebook intégrés aux alertes

- Suppression de la section séparée « Commentaires Facebook » du portail réputation.
- Les commentaires retenus apparaissent maintenant dans la section **Alertes ARMA**.
- Filtrage conservateur des commentaires : 30 jours par défaut, plainte/question liée à ARMA, exclusion des prix seuls (`17$`), spam, commentaires visant uniquement un concurrent et commentaires défendant ARMA ou accusant uniquement les habitants.
- Les alertes de commentaires ne sont exposées par l'API que lorsque le triage les juge pertinentes et actionnables.
- Les brouillons FR/AR sont modifiables dans le navigateur.
- Bouton **Envoyer sur Facebook** uniquement pour un commentaire Facebook éligible, après validation humaine et confirmation Meta.
- Pour une autre source, le bouton copie le brouillon et ouvre la publication ; aucun faux envoi n'est affiché.

Configuration : `COMMENT_MAX_AGE_DAYS=30` dans `.env`.
