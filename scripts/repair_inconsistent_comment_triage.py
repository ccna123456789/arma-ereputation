"""Répare sans appel Claude les résultats de tri incohérents déjà stockés.

Invariant : off_topic / noise / competitor_only ne peuvent jamais participer au
score ni recommander une réponse. Le script utilise les résultats Claude déjà
stockés, ferme les alertes devenues obsolètes et recalcule le score hebdomadaire.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.comment_triage.claude_provider import EXCLUDED_CATEGORIES, result_from_payload
from backend.ai.comment_triage.service import (
    TRIAGE_FLAGS,
    TRIAGE_PAYLOAD_KEY,
    TRIAGE_POLICY_VERSION,
    apply_triage_to_relations,
)
from backend.database.connection import SessionLocal
from backend.database.models import Mention
from backend.scoring.service import compute_reputation_snapshots


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> int:
    session = SessionLocal()
    checked = 0
    repaired = 0
    relations_changed = 0
    analyses_created = 0
    alerts_ignored = 0
    try:
        comments = list(session.scalars(
            select(Mention).where(Mention.content_type == "social_comment").order_by(Mention.id.asc())
        ))
        for comment in comments:
            checked += 1
            payload = dict(comment.raw_payload or {})
            triage = payload.get(TRIAGE_PAYLOAD_KEY)
            if not isinstance(triage, dict):
                continue
            category = str(triage.get("category") or "").strip().lower()
            inconsistent = category in EXCLUDED_CATEGORIES and (
                bool(triage.get("relevant", False))
                or bool(triage.get("reply_recommended", False))
                or str(triage.get("sentiment") or "neutral").lower() != "neutral"
            )
            if not inconsistent:
                continue

            result = result_from_payload(
                triage,
                str(triage.get("model_name") or "claude-haiku-4-5-20251001"),
                triage.get("model_version"),
            )
            repaired_payload = result.to_dict()
            repaired_payload["policy_version"] = triage.get("policy_version") or TRIAGE_POLICY_VERSION
            if triage.get("classified_at"):
                repaired_payload["classified_at"] = triage.get("classified_at")
            repaired_payload["invariant_repaired_at"] = utc_now().isoformat()
            payload[TRIAGE_PAYLOAD_KEY] = repaired_payload
            comment.raw_payload = payload

            preserved_flags = [
                flag for flag in (comment.quality_flags or [])
                if flag not in TRIAGE_FLAGS
            ]
            comment.quality_flags = list(dict.fromkeys(preserved_flags + result.quality_flags))
            comment.processing_status = "ignored"
            comment.display_in_marketing = False

            counts = apply_triage_to_relations(session, comment, result=result)
            relations_changed += counts["relations_changed"]
            analyses_created += counts["analyses_created"]
            alerts_ignored += counts["alerts_ignored"]
            repaired += 1

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    print(f"Commentaires vérifiés : {checked}")
    print(f"Résultats incohérents réparés : {repaired}")
    print(f"Relations modifiées : {relations_changed}")
    print(f"Analyses créées/mises à jour : {analyses_created}")
    print(f"Alertes fermées/ignorées : {alerts_ignored}")
    print("Recalcul du score hebdomadaire...")
    compute_reputation_snapshots(period_type="weekly")
    print("Réparation terminée sans nouvel appel Claude.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
