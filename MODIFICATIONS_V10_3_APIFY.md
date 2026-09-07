# Modifications V10.3 — Commentaires Facebook via Apify

## Objectif

Cette version ajoute une collecte structurée et automatisée des commentaires
Facebook publiquement visibles pour les publications retenues dans les deux POC.
Les captures Selenium restent une preuve visuelle secondaire ; elles ne sont plus
la source de données utilisée pour le NLP.

## Chaîne automatisée

```text
Qualification des veilles et alertes Facebook
→ export des URL retenues dans data/fb.txt
→ collecte Apify
→ normalisation et déduplication PostgreSQL
→ nettoyage et détection de langue
→ triage des commentaires
→ sentiment, alertes et décisions
→ brouillons de réponse FR/AR
→ affichage dans Réputation Sociale ARMA
```

## Principales modifications

- nouveau service `backend/services/apify_facebook_comments_service.py` ;
- fournisseur configurable `apify`, `meta`, `auto` ou `disabled` ;
- token Apify conservé uniquement dans `.env` et transmis par en-tête Bearer ;
- récupération automatique des URL de `data/fb.txt` ;
- création ou mise à jour de mentions `social_comment` reliées à leur post parent ;
- conservation du texte, date, likes, profondeur de réponse, identifiants et payload brut ;
- minimisation par défaut des URLs et photos de profils publics ;
- nouvelle route `GET /api/facebook/comments?limit=100` ;
- statut combiné de la collecte et de l’envoi dans `/api/facebook/integration/status` ;
- affichage des commentaires Apify dans le POC Réputation même sans alerte ;
- workflow n8n V10.3 réordonné afin que les commentaires soient analysés dans le même run ;
- étape n8n Facebook reliée au registre d’orchestration, évitant les runs `partial` ;
- envoi des réponses maintenu exclusivement via Meta Graph API après validation humaine ;
- captures Selenium conservées comme preuves visuelles non bloquantes.

## Sécurité et limites

- aucune clé n’est incluse dans le workflow ou dans le ZIP ;
- aucun cookie Facebook personnel n’est utilisé ;
- seuls les commentaires rendus publiquement accessibles peuvent être collectés ;
- Apify ne sert jamais à envoyer une réponse ;
- une réponse réelle exige une Page Meta autorisée et une confirmation humaine.
