# Version finale — commentaires Facebook, sentiment et alertes

## Objectif métier

La plateforme collecte les commentaires Facebook publics accessibles pour les
publications retenues dans le POC Marketing et dans le POC Réputation. Chaque
commentaire utile est ensuite classé en **positif**, **neutre** ou **négatif**.

- Les trois classes participent au calcul du score de réputation.
- Un commentaire négatif concernant ARMA crée une alerte individuelle.
- Un brouillon FR/AR est généré lorsqu'une réponse publique est recommandée.
- Le brouillon reste modifiable et l'envoi réel exige une validation humaine et
  les autorisations Meta de la Page.
- Les prix seuls (`17$`), le spam, le contenu vide et les commentaires portant
  uniquement sur un concurrent restent exclus du score et des alertes ARMA.

## Correction principale

Les publications Facebook découvertes par Serper étaient enregistrées sous une
source comme `facebook.com` ou `Serper`, alors que l'ancien rattachement Apify ne
recherchait que la source exacte `Facebook`. Les commentaires pouvaient donc être
attachés à un doublon technique sans relation ARMA.

La version finale recherche maintenant l'URL Facebook dans toutes les
publications, leur payload brut et leurs métadonnées. Elle privilégie le post
original déjà visible dans le portail, puis transmet ses relations ARMA aux
commentaires.

## Configuration `.env`

```env
FACEBOOK_COMMENTS_PROVIDER=apify
APIFY_FACEBOOK_COMMENTS_ENABLED=true
APIFY_API_TOKEN=...
APIFY_FACEBOOK_ACTOR_ID=apify/facebook-comments-scraper
APIFY_API_BASE_URL=https://api.apify.com

APIFY_MAX_POSTS_PER_RUN=20
APIFY_COLLECT_ALL_COMMENTS=true
APIFY_ALL_COMMENTS_LIMIT=500
APIFY_MAX_COMMENTS_PER_POST=500
APIFY_INCLUDE_REPLIES=true
APIFY_COMMENTS_MODE=Newest
APIFY_ONLY_COMMENTS_NEWER_THAN=
APIFY_RUN_TIMEOUT_SECONDS=300
APIFY_STORE_PROFILE_URLS=false

FACEBOOK_REGISTRY_PRESERVE_EXISTING=true
```

`APIFY_ALL_COMMENTS_LIMIT` est une limite de sécurité par publication. Elle peut
être augmentée ou diminuée selon le volume et le budget Apify.

## Mise à niveau depuis V10.5

1. Copier l'ancien fichier `.env` à la racine de cette version.
2. Ajouter ou remplacer les variables ci-dessus.
3. Exécuter une seule fois `scripts/setup_project.ps1` dans ce nouveau dossier.
4. Démarrer le backend.
5. Garder le workflow n8n V10.3 Apify déjà importé : ses étapes restent
   compatibles. Exécuter le workflow complet une fois afin de rattacher et
   reclasser les commentaires existants avec la nouvelle politique.
6. Démarrer le frontend et recharger avec `Ctrl + F5`.

## Vérification

```text
http://127.0.0.1:8000/api/facebook/comments/diagnostic
http://127.0.0.1:8000/api/facebook/comments/summary?organization=ARMA&days=90
http://127.0.0.1:8000/api/alerts?organization=ARMA&status=open&days=90&limit=100
```

Dans l'interface, une alerte issue d'un commentaire porte le type :

```text
FACEBOOK · APIFY · COMMENTAIRE
```

Deux commentaires négatifs sous le même post restent deux alertes distinctes.
