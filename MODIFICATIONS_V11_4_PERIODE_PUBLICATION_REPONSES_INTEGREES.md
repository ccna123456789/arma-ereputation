# V11.4 — Semaine de publication + réponses intégrées aux alertes

## Règle métier hebdomadaire

Le workflow est planifié chaque **lundi à 07:00** dans le fuseau `Africa/Casablanca`.
Le reporting porte sur la **semaine civile complète précédente**, du lundi au dimanche.

Exemple : exécution le lundi 31/08/2026 à 07:00 → période affichée `2026-08-24 → 2026-08-30`.

## Date utilisée

Tous les éléments du POC Réputation sont filtrés par leur date de publication réelle :
`manual_published_at` si corrigée manuellement, sinon `published_at`.

La date `collected_at` reste conservée pour la traçabilité, mais ne décide plus de la semaine.
Un contenu ancien découvert aujourd'hui ne devient donc pas un contenu de la semaine courante.
Les contenus sans date de publication fiable ne sont pas intégrés au score ou aux alertes de la période tant que leur date n'est pas corrigée.

Cette règle s'applique à :
- score ARMA et concurrents ;
- commentaires Facebook ;
- alertes ;
- sujets dominants ;
- veille Marketing ;
- angles stratégiques et preuves servant aux posts générés.

## Interface Réputation

Le brouillon Claude FR/AR est désormais placé **directement sous l'alerte concernée** dans un bloc déroulant :
`Voir la réponse proposée`.
La section séparée de brouillons a été supprimée pour éviter de chercher la correspondance entre une alerte et sa réponse.

## Interface Marketing

La zone `Veille` interroge la même période hebdomadaire que le score de réputation et n'affiche que les contenus publiés dans cette fenêtre.
La date de collecte reste visible uniquement comme preuve de traçabilité.

## Workflow n8n

Le Schedule Trigger de l'export JSON est configuré sur :
- intervalle : 1 semaine ;
- jour : lundi ;
- heure : 07:00 ;
- minute : 00 ;
- fuseau : Africa/Casablanca.

Si le workflow est déjà importé dans n8n, modifier son nœud Schedule Trigger manuellement ou réimporter le workflow V11.4.
