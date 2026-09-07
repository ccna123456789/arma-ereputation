# V10.5 — Diagnostic et collecte réelle des commentaires Facebook

- Mise à jour de l'entrée de l'Actor officiel `apify/facebook-comments-scraper` :
  `resultsLimit`, `includeNestedComments`, `viewOption`.
- Les erreurs Apify ne sont plus cachées à n8n : le nœud de collecte est marqué
  en échec lorsqu'une erreur réelle survient.
- Chaque nœud d'orchestration retourne maintenant son résultat détaillé
  (`urls_submitted`, `comments_created`, `comments_updated`, etc.).
- Nouvel endpoint sans secret : `GET /api/facebook/comments/diagnostic`.
- Le workflow n8n V10.3 existant reste compatible : aucun nouveau workflow à créer.
