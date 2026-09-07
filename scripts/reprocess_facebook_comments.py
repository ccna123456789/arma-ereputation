"""Nettoie les commentaires Facebook existants sans relancer Apify.

Étapes : réparation de la première date de collecte -> re-tri strict -> alertes
-> recalcul du score courant. Claude reste configuré ; si son crédit est
indisponible, le tri passe automatiquement aux règles strictes pour ce run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.comment_triage.service import triage_social_comments
from backend.alerts.service import generate_alerts_for_negative_mentions
from backend.scoring.service import compute_reputation_snapshots
from backend.services.apify_facebook_comments_service import repair_legacy_comment_collection_dates


def main() -> int:
    print("--- Étape 1/4 : réparation des dates de première collecte ---")
    print(json.dumps(repair_legacy_comment_collection_dates(), ensure_ascii=False, indent=2, default=str))

    print("\n--- Étape 2/4 : re-tri strict de tous les commentaires ---")
    print(json.dumps(triage_social_comments(replace_existing=True), ensure_ascii=False, indent=2, default=str))

    print("\n--- Étape 3/4 : mise à jour des alertes ---")
    print(json.dumps(generate_alerts_for_negative_mentions(), ensure_ascii=False, indent=2, default=str))

    print("\n--- Étape 4/4 : recalcul du score hebdomadaire ---")
    compute_reputation_snapshots(period_type="weekly")
    print("\nNettoyage terminé. Rechargez le frontend avec Ctrl+F5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
