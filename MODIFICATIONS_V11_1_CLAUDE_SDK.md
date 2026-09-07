# V11.1 — Compatibilité SDK Anthropic

Cette révision corrige l'erreur :

`Messages.create() got an unexpected keyword argument 'temperature'`

Les versions récentes du SDK Python Anthropic ont retiré `temperature`, `top_p` et `top_k` de la signature directe de `messages.create()`. Les quatre fournisseurs Claude du projet n'envoient donc plus `temperature=0` :

- `backend/ai/comment_triage/claude_provider.py`
- `backend/ai/content/claude_provider.py`
- `backend/ai/sentiment/claude_provider.py`
- `backend/ai/response_drafts/claude_provider.py`

Le reste de la logique V11 est inchangé : filtrage strict, fallback règles en cas d'indisponibilité Claude, première date de collecte conservée, période Facebook alignée sur le score.

Après remplacement du code, relancer :

```powershell
.\scripts\reprocess_facebook_comments.ps1
```

Le résumé attendu ne doit plus afficher `Replis Claude -> règles : 371` si l'API, la clé et le crédit sont valides.
