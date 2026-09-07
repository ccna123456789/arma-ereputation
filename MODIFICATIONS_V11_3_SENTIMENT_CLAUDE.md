# V11.3 — Correction du sentiment des commentaires Claude

Cette version corrige les faux positifs observés dans le portail :

- « propreté » ne déclenche plus un sentiment positif via le sous-mot « propre » ;
- une plainte polie commençant par « merci » reste négative si elle décrit un dysfonctionnement ;
- une critique constructive reste négative si elle décrit un mauvais service ;
- la responsabilité attribuée aux citoyens / à un tiers est neutre par défaut, pas positive ;
- les règles locales n’écrasent Claude que pour des signaux non ambigus ;
- un `positive_feedback` n’est plus automatiquement mis dans la file « commentaire à traiter ».

Après remplacement des deux providers, relancer le tri des commentaires pertinents avec `scripts\reprocess_relevant_comments_only.ps1`, puis régénérer les brouillons via n8n ou le service de réponses.
