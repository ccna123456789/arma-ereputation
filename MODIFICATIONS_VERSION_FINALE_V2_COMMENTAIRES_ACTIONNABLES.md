# Version finale V2 — commentaires Facebook actionnables

Cette version corrige le cas où des commentaires visibles sous une publication Facebook
n'apparaissaient pas clairement dans le portail ARMA.

## Corrections principales

- Rattachement des commentaires au post Serper/Marketing par URL **et par identifiant Facebook**.
- Réparation automatique des commentaires déjà enregistrés avec un parent technique incorrect.
- Nouvelle tentative Apify individuelle pour un nombre limité de posts qui retournent zéro commentaire dans le run groupé.
- Classement de tous les commentaires utiles en positif, neutre ou négatif pour le score.
- Création d'une alerte pour :
  - toute critique négative pertinente ;
  - toute question ou suggestion pour laquelle une réponse est recommandée, même si son sentiment est neutre.
- Section distincte **Commentaires Facebook à traiter** placée avant les autres alertes.
- Détail par publication : nombre collecté, classé, négatif, actionnable et alerté.
- Les preuves visuelles Selenium sont désactivées par défaut afin de ne pas bloquer le workflow pendant une heure.

## Exemples désormais traités

- `Il faut nettoyer avec de l'eau et du détergent.` → neutre, suggestion, réponse recommandée, alerte.
- `Si c'est la même société à Tanger, c'est devenu catastrophique.` → négatif, réponse recommandée, alerte.
- `17$` → bruit exclu.
- `Bravo` sous un post rattaché à ARMA → positif, inclus dans le score, sans alerte.

## Vérification

- 81 tests automatisés réussis.
- Syntaxe Python et JavaScript vérifiée.
