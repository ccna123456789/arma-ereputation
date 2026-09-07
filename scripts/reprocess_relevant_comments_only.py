"""Reclasse avec Claude uniquement les commentaires déjà jugés pertinents.

But : corriger la polarité (positif/neutre/négatif) sans repayer l'analyse des
commentaires déjà exclus comme noise/off_topic/competitor_only. Les exclus
conservent leur décision d'exclusion et reçoivent seulement la nouvelle version
de politique pour éviter un retraitement inutile au prochain run n8n.
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai.comment_triage.claude_provider import ClaudeCommentTriageProvider
from backend.ai.comment_triage.service import (
    OWN_ORGANIZATION_NAME,
    TRIAGE_FLAGS,
    TRIAGE_PAYLOAD_KEY,
    TRIAGE_POLICY_VERSION,
    _belongs_to_arma,
    apply_triage_to_relations,
    utc_now,
)
from backend.database.connection import SessionLocal
from backend.database.models import Mention
from backend.alerts.service import generate_alerts_for_negative_mentions
from backend.scoring.service import compute_reputation_snapshots


def main() -> int:
    session = SessionLocal()
    provider = ClaudeCommentTriageProvider()
    checked = 0
    reclassified = 0
    excluded_policy_bumped = 0
    relations_changed = 0
    analyses_created = 0
    alerts_ignored = 0
    failed = 0

    try:
        comments = list(session.scalars(
            select(Mention)
            .where(Mention.content_type == "social_comment")
            .order_by(Mention.id.asc())
        ))
        print(f"Commentaires sociaux trouvés : {len(comments)}")

        for comment in comments:
            checked += 1
            payload = dict(comment.raw_payload or {})
            old_triage = payload.get(TRIAGE_PAYLOAD_KEY)

            # Les commentaires déjà exclus n'ont pas besoin d'un nouvel appel
            # Claude : le correctif V11.3 concerne surtout le sentiment des
            # commentaires pertinents. On met simplement la version à jour.
            if isinstance(old_triage, dict) and not bool(old_triage.get("relevant", False)):
                old_triage = dict(old_triage)
                old_triage["policy_version"] = TRIAGE_POLICY_VERSION
                old_triage["sentiment_policy_upgraded_at"] = utc_now().isoformat()
                payload[TRIAGE_PAYLOAD_KEY] = old_triage
                comment.raw_payload = payload
                excluded_policy_bumped += 1
                continue

            try:
                parent = session.get(Mention, comment.parent_mention_id) if comment.parent_mention_id else None
                parent_title = parent.display_title or parent.title if parent else None
                parent_text = (parent.clean_text or parent.raw_text) if parent else None
                if _belongs_to_arma(session, comment, parent):
                    parent_title = f"[Publication rattachée à ARMA] {parent_title or ''}".strip()

                result = provider.classify(
                    comment_text=comment.clean_text or comment.raw_text,
                    parent_title=parent_title,
                    parent_text=parent_text,
                    organization_name=OWN_ORGANIZATION_NAME,
                    language_hint=comment.detected_language,
                )

                triage_payload = result.to_dict()
                triage_payload["policy_version"] = TRIAGE_POLICY_VERSION
                triage_payload["classified_at"] = utc_now().isoformat()
                payload[TRIAGE_PAYLOAD_KEY] = triage_payload
                comment.raw_payload = payload

                preserved_flags = [
                    flag for flag in (comment.quality_flags or [])
                    if flag not in TRIAGE_FLAGS
                ]
                comment.quality_flags = list(dict.fromkeys(preserved_flags + result.quality_flags))
                comment.processing_status = "qualified" if result.relevant else "ignored"
                comment.display_in_marketing = False

                counts = apply_triage_to_relations(session, comment, result=result)
                relations_changed += counts["relations_changed"]
                analyses_created += counts["analyses_created"]
                alerts_ignored += counts["alerts_ignored"]
                reclassified += 1
                print(
                    f"Commentaire {comment.id} -> {result.category} | "
                    f"sentiment={result.sentiment} | score={result.relevant} | "
                    f"réponse={result.reply_recommended}"
                )
                session.commit()
            except Exception as exc:
                session.rollback()
                failed += 1
                print(f"Commentaire {comment.id} en échec : {exc}")

        session.commit()
    finally:
        session.close()

    print("\n--- Résumé reclassification ciblée ---")
    print(f"Commentaires vérifiés : {checked}")
    print(f"Commentaires pertinents réanalysés par Claude : {reclassified}")
    print(f"Commentaires exclus sans nouvel appel Claude : {excluded_policy_bumped}")
    print(f"Relations modifiées : {relations_changed}")
    print(f"Analyses créées/mises à jour : {analyses_created}")
    print(f"Alertes fermées/ignorées : {alerts_ignored}")
    print(f"Échecs : {failed}")
    if failed:
        raise RuntimeError(f"Reclassification incomplète : {failed} échec(s).")

    print("\n--- Mise à jour des alertes négatives ---")
    print(generate_alerts_for_negative_mentions())

    print("\n--- Recalcul du score hebdomadaire ---")
    compute_reputation_snapshots(period_type="weekly")
    print("\nCorrection sentiment terminée.")
    print("Régénérez ensuite les brouillons : python -m backend.ai.response_drafts.service --provider claude --replace-existing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
