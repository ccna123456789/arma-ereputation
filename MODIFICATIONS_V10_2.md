# Modifications V10.2

- `data/fb.txt` devient le registre automatique des posts Facebook retenus dans les deux POC.
- Les alertes portant sur un commentaire exportent la publication Facebook parente.
- Ajout du registre détaillé `data/fb_registry.json`.
- Ajout du service Selenium de captures publiques, sans authentification ni contournement.
- Captures versionnées par run dans `data/facebook_screenshots` avec manifests JSON/TXT.
- Ajout des endpoints `/api/facebook-screenshots/*` et du service statique des preuves visuelles.
- Affichage de la première capture disponible dans les cartes Marketing et Réputation.
- Ajout des étapes n8n 17 et 18 : export des liens puis captures.
- L'indisponibilité de Chrome/Facebook n'arrête pas le reste du pipeline ; elle est signalée dans la qualité.
- Correction de la requête Marketing pour utiliser la date manuelle lorsqu'elle existe.
- Scripts PowerShell backend/frontend rendus plus robustes.
- Suppression des références obsolètes au collecteur YouTube dans le guide principal.
- 59 tests réussis.
