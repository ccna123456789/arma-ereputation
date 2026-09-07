# V11.7 — Semaines civiles et cohérence stricte par date de publication

## Règles métier corrigées

1. **Weekly = lundi → dimanche uniquement.**
   - La période affichée par défaut est toujours la dernière semaine civile complète **T-1**.
   - La semaine en cours, même si elle contient déjà des publications, n'est jamais proposée comme période terminée.
   - Les anciens snapshots hebdomadaires glissants (mardi→lundi, samedi→vendredi, etc.) sont exclus du sélecteur et de l'historique.

2. **Une publication appartient à une seule semaine selon sa vraie date de publication.**
   - Date utilisée : `manual_published_at` si corrigée manuellement, sinon `published_at`.
   - `collected_at` reste uniquement une information de traçabilité.
   - `generated_at` ne sert jamais à rattacher un angle ou un brouillon à une semaine.
   - Une source sans date de publication fiable n'est pas injectée artificiellement dans une semaine.

3. **Marketing : Veille → Angles → Brouillons est désormais cohérent.**
   - Les angles acceptent les `news_article` et `social_post` qualifiés (pertinence >= 0.62).
   - Les `social_comment` restent dans l'e-réputation et ne servent pas au contenu Marketing.
   - Un angle n'apparaît que si ses preuves ont été publiées dans la semaine affichée.
   - Un brouillon n'apparaît que si ses preuves ont été publiées dans la semaine affichée.
   - Si la semaine n'a aucune publication Marketing qualifiée, les sections Angles et Brouillons restent vides.

4. **Plus de réutilisation d'angles d'une ancienne semaine.**
   - Le générateur de posts sélectionne uniquement les angles de la période hebdomadaire ciblée.
   - Si le run d'angles de T-1 produit 0 angle, le run de posts produit 0 brouillon au lieu de reprendre un ancien angle.

5. **Interface Réputation plus robuste.**
   - La barre s'ouvre directement sur T-1.
   - Si le snapshot de score n'a pas encore été calculé, la bonne semaine reste affichée avec un état « score non calculé » au lieu d'une erreur fetch.

## Test historique Marketing

Pour rejouer une semaine précise sans changer le fonctionnement final weekly :

```powershell
python .\scripts\replay_marketing_week.py 2026-08-23 --provider claude
```

La date est automatiquement alignée sur la semaine civile lundi→dimanche qui la contient.

## Validation

Suite de tests du projet : **124 tests passés**.
