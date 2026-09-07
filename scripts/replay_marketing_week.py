from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rejoue uniquement la partie Marketing pour une semaine historique. "
            "La date fournie peut être n'importe quel jour de la semaine ; elle "
            "est automatiquement alignée sur lundi -> dimanche."
        )
    )
    parser.add_argument("period_end", type=date.fromisoformat, help="Date ISO, ex. 2026-08-23")
    parser.add_argument("--provider", default=None, help="claude ou template (sinon .env)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from backend.ai.content.angle_service import generate_strategic_angles
    from backend.ai.content.post_service import generate_posts_for_proposed_angles
    from backend.scoring.formulas import get_period_bounds

    start, end = get_period_bounds("weekly", args.period_end)
    print(f"Semaine Marketing rejouée : {start} -> {end}")
    generate_strategic_angles(period_type="weekly", period_end=end)
    generate_posts_for_proposed_angles(
        provider_name=args.provider,
        period_type="weekly",
        period_end=end,
    )


if __name__ == "__main__":
    main()
