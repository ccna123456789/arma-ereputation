from __future__ import annotations

from typing import Any

from sqlalchemy import select

from backend.collectors.serper_client import SerperClient
from backend.database.connection import SessionLocal
from backend.database.models import PipelineRun, WatchQuery
from backend.services.collection_service import (
    MAX_RESULTS,
    clean_text,
    create_content_hash,
    create_external_id,
    create_mention,
    create_pipeline_run,
    get_serper_source,
    mark_pipeline_as_failed,
    mention_already_exists,
    utc_now,
)


# Nous commençons seulement par trois requêtes ARMA.
# Une requête correspond généralement à un appel Serper.
SELECTED_QUERIES = [
    "ARMA Environnement Maroc",
    "ARMA propreté Casablanca",
    "ARMA gestion des déchets Maroc",
]


def get_selected_query_ids() -> list[int]:
    """
    Récupère les identifiants des trois requêtes
    de veille sélectionnées.
    """

    session = SessionLocal()

    try:
        statement = (
            select(WatchQuery)
            .where(
                WatchQuery.query_text.in_(SELECTED_QUERIES),
                WatchQuery.is_active.is_(True),
            )
            .order_by(WatchQuery.id)
        )

        watch_queries = list(
            session.scalars(statement).all()
        )

        found_queries = {
            watch_query.query_text
            for watch_query in watch_queries
        }

        missing_queries = [
            query_text
            for query_text in SELECTED_QUERIES
            if query_text not in found_queries
        ]

        if missing_queries:
            print(
                "Attention : certaines requêtes "
                "sont absentes de la base :"
            )

            for query_text in missing_queries:
                print(f"- {query_text}")

        return [
            watch_query.id
            for watch_query in watch_queries
        ]

    finally:
        session.close()


def collect_one_query(
    watch_query_id: int,
    client: SerperClient,
) -> dict[str, Any]:
    """
    Collecte et enregistre les résultats d'une seule
    requête de veille.
    """

    session = SessionLocal()
    pipeline_run_id: int | None = None

    try:
        source = get_serper_source(session)

        watch_query = session.get(
            WatchQuery,
            watch_query_id,
        )

        if watch_query is None:
            raise RuntimeError(
                "La requête de veille est introuvable : "
                f"{watch_query_id}"
            )

        query_text = watch_query.query_text
        language = watch_query.language or "fr"

        filters = watch_query.filters or {}
        country = str(
            filters.get("country", "ma")
        ).lower()

        print("\n" + "=" * 75)
        print(f"Requête : {query_text}")
        print(f"Langue : {language}")
        print(f"Pays : {country}")

        pipeline_run = create_pipeline_run(
            session=session,
            source=source,
            watch_query=watch_query,
        )

        pipeline_run_id = pipeline_run.id

        print(
            f"Pipeline créé : {pipeline_run_id}"
        )

        results = client.search_news(
            query=query_text,
            language=language,
            country=country,
            num=MAX_RESULTS,
        )

        # Serper peut parfois retourner plus de résultats
        # que la valeur demandée.
        results = results[:MAX_RESULTS]

        items_received = len(results)
        items_created = 0
        items_duplicated = 0
        items_ignored = 0

        print(
            f"Résultats reçus : {items_received}"
        )

        for result in results:
            if not isinstance(result, dict):
                items_ignored += 1
                print("Résultat invalide ignoré.")
                continue

            external_id = create_external_id(result)
            content_hash = create_content_hash(result)

            already_exists = mention_already_exists(
                session=session,
                source_id=source.id,
                external_id=external_id,
                content_hash=content_hash,
            )

            title = clean_text(
                result.get("title")
            ) or "Sans titre"

            if already_exists:
                items_duplicated += 1
                print(f"Doublon ignoré : {title}")
                continue

            mention = create_mention(
                result=result,
                source=source,
                pipeline_run=pipeline_run,
                language=language,
                country=country,
            )

            if mention is None:
                items_ignored += 1
                print(f"Résultat vide ignoré : {title}")
                continue

            session.add(mention)
            session.flush()

            items_created += 1
            print(f"Mention ajoutée : {title}")

        current_pipeline = session.get(
            PipelineRun,
            pipeline_run_id,
        )

        if current_pipeline is None:
            raise RuntimeError(
                "Impossible de retrouver le pipeline."
            )

        current_pipeline.status = "completed"
        current_pipeline.finished_at = utc_now()
        current_pipeline.items_received = items_received
        current_pipeline.items_created = items_created
        current_pipeline.items_duplicated = items_duplicated
        current_pipeline.error_message = None
        current_pipeline.statistics = {
            "query": query_text,
            "language": language,
            "country": country,
            "requested_results": MAX_RESULTS,
            "received_results": items_received,
            "created_results": items_created,
            "duplicated_results": items_duplicated,
            "ignored_results": items_ignored,
            "collection_mode": "batch",
        }

        session.commit()

        print(
            f"Requête terminée : "
            f"{items_created} nouvelles mentions, "
            f"{items_duplicated} doublons."
        )

        return {
            "query": query_text,
            "status": "completed",
            "received": items_received,
            "created": items_created,
            "duplicated": items_duplicated,
            "ignored": items_ignored,
        }

    except Exception as error:
        if pipeline_run_id is not None:
            mark_pipeline_as_failed(
                session=session,
                pipeline_run_id=pipeline_run_id,
                error=error,
            )
        else:
            session.rollback()

        print(
            f"Erreur pendant la requête "
            f"{watch_query_id} : {error}"
        )

        return {
            "query_id": watch_query_id,
            "status": "failed",
            "received": 0,
            "created": 0,
            "duplicated": 0,
            "ignored": 0,
            "error": str(error),
        }

    finally:
        session.close()


def collect_selected_queries() -> None:
    """
    Lance successivement les trois requêtes choisies.
    """

    print(
        "Début de la collecte multiple."
    )
    print(
        f"Nombre maximal d'appels Serper : "
        f"{len(SELECTED_QUERIES)}"
    )
    print(
        f"Résultats maximum par requête : "
        f"{MAX_RESULTS}"
    )

    query_ids = get_selected_query_ids()

    if not query_ids:
        print(
            "Aucune requête disponible."
        )
        return

    client = SerperClient()
    summaries: list[dict[str, Any]] = []

    for watch_query_id in query_ids:
        summary = collect_one_query(
            watch_query_id=watch_query_id,
            client=client,
        )

        summaries.append(summary)

    total_received = sum(
        summary["received"]
        for summary in summaries
    )

    total_created = sum(
        summary["created"]
        for summary in summaries
    )

    total_duplicated = sum(
        summary["duplicated"]
        for summary in summaries
    )

    total_ignored = sum(
        summary["ignored"]
        for summary in summaries
    )

    failed_queries = sum(
        summary["status"] == "failed"
        for summary in summaries
    )

    print("\n" + "=" * 75)
    print("Résumé de la collecte multiple")
    print(f"- Requêtes exécutées : {len(summaries)}")
    print(f"- Requêtes échouées : {failed_queries}")
    print(f"- Résultats reçus : {total_received}")
    print(f"- Mentions créées : {total_created}")
    print(f"- Doublons ignorés : {total_duplicated}")
    print(f"- Résultats vides ignorés : {total_ignored}")


if __name__ == "__main__":
    collect_selected_queries()