from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.collectors.serper_client import SerperClient
from backend.database.connection import SessionLocal
from backend.database.models import (
    Organization,
    PipelineRun,
    Source,
    WatchQuery,
)
from backend.services.collection_service import (
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


# ============================================================
# Configuration des organisations
# ============================================================

# Nom enregistré dans PostgreSQL -> texte utilisé dans Google.
ORGANIZATION_SEARCH_NAMES = {
    "ARMA": "ARMA Environnement",
    "OZONE": "OZONE Environnement Maroc",
    "Averda": "Averda Maroc",
    "Suez Maroc": "Suez Maroc",
    "SOS": "SOS environnement Maroc",
}


# ============================================================
# Configuration des plateformes sociales
# ============================================================

PLATFORMS = {
    "LinkedIn": {
        "source_name": "LinkedIn",
        "accepted_domains": (
            "linkedin.com",
        ),
    },
    "Facebook": {
        "source_name": "Facebook",
        "accepted_domains": (
            "facebook.com",
        ),
    },
    "Instagram": {
        "source_name": "Instagram",
        "accepted_domains": (
            "instagram.com",
        ),
    },
    "X": {
        "source_name": "X / Twitter",
        "accepted_domains": (
            "x.com",
            "twitter.com",
        ),
    },
}


# Nombre maximal de résultats conservés
# pour chaque recherche Serper.
MAX_RESULTS_PER_QUERY = 5


# Toutes les plateformes sociales prises en charge.
PLATFORMS_TO_RUN = [
    "LinkedIn",
    "Facebook",
    "Instagram",
    "X",
]


# Nombre maximal de recherches :
# 5 organisations × 4 plateformes = 20 recherches.
MAX_QUERIES_PER_RUN = (
    len(ORGANIZATION_SEARCH_NAMES)
    * len(PLATFORMS_TO_RUN)
)


def get_target_organizations(
    session: Session,
) -> list[Organization]:
    """
    Récupère ARMA et tous les concurrents actifs
    enregistrés dans PostgreSQL.
    """

    organization_names = list(
        ORGANIZATION_SEARCH_NAMES.keys()
    )

    statement = (
        select(Organization)
        .where(
            Organization.name.in_(organization_names),
            Organization.is_active.is_(True),
        )
        .order_by(Organization.id)
    )

    organizations = list(
        session.scalars(statement).all()
    )

    found_names = {
        organization.name
        for organization in organizations
    }

    missing_names = [
        name
        for name in organization_names
        if name not in found_names
    ]

    if missing_names:
        raise RuntimeError(
            "Organisations absentes de PostgreSQL : "
            + ", ".join(missing_names)
        )

    return organizations


def get_platform_source(
    session: Session,
    source_name: str,
) -> Source:
    """
    Récupère la source correspondant à la plateforme :
    LinkedIn, Facebook, Instagram ou X.
    """

    source = session.scalar(
        select(Source).where(
            Source.name == source_name,
            Source.is_active.is_(True),
        )
    )

    if source is None:
        raise RuntimeError(
            f"La source sociale '{source_name}' "
            "est absente de PostgreSQL. "
            "Relance le fichier seed.py."
        )

    return source


def build_social_query(
    organization_name: str,
    platform_name: str,
) -> str:
    """
    Construit une requête sociale sans utiliser
    l'opérateur site:.

    L'opérateur site: a été refusé par le compte
    gratuit Serper pour certaines plateformes.

    Exemples :
    "ARMA Environnement" Facebook
    "Averda Maroc" Instagram
    "Suez Maroc" X Twitter
    """

    search_name = ORGANIZATION_SEARCH_NAMES[
        organization_name
    ]

    platform_keywords = {
        "LinkedIn": "LinkedIn",
        "Facebook": "Facebook",
        "Instagram": "Instagram",
        "X": "X Twitter",
    }

    keyword = platform_keywords[platform_name]

    return f'"{search_name}" {keyword}'


def get_or_create_social_watch_query(
    session: Session,
    organization: Organization,
    query_text: str,
    platform_name: str,
) -> WatchQuery:
    """
    Récupère une requête sociale existante ou
    la crée dans la table watch_queries.
    """

    watch_query = session.scalar(
        select(WatchQuery).where(
            WatchQuery.organization_id == organization.id,
            WatchQuery.query_text == query_text,
        )
    )

    if watch_query is not None:
        return watch_query

    watch_query = WatchQuery(
        organization_id=organization.id,
        query_text=query_text,
        language="fr",
        category="social",
        frequency="daily",
        filters={
            "country": "ma",
            "platform": platform_name,
        },
        is_active=True,
    )

    session.add(watch_query)
    session.flush()

    print(
        "Requête sociale ajoutée dans PostgreSQL : "
        f"{query_text}"
    )

    return watch_query


def result_matches_platform(
    result: dict[str, Any],
    accepted_domains: tuple[str, ...],
) -> bool:
    """
    Vérifie que l'URL du résultat appartient réellement
    à la plateforme sociale recherchée.

    Exemple :
    une recherche Facebook doit retourner une URL
    facebook.com et non un article de presse.
    """

    link = clean_text(
        result.get("link")
    )

    if not link:
        return False

    try:
        hostname = urlsplit(link).netloc.casefold()
    except ValueError:
        return False

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return any(
        hostname == domain
        or hostname.endswith(f".{domain}")
        for domain in accepted_domains
    )


def collect_one_social_query(
    organization_id: int,
    platform_name: str,
    client: SerperClient,
) -> dict[str, Any]:
    """
    Exécute une recherche sociale pour une organisation
    et une plateforme.

    Les résultats sont :
    - filtrés selon le domaine de la plateforme ;
    - comparés aux mentions existantes ;
    - enregistrés dans PostgreSQL ;
    - associés à un pipeline d'exécution.
    """

    session = SessionLocal()
    pipeline_run_id: int | None = None

    try:
        organization = session.get(
            Organization,
            organization_id,
        )

        if organization is None:
            raise RuntimeError(
                "Organisation introuvable : "
                f"{organization_id}"
            )

        if platform_name not in PLATFORMS:
            raise RuntimeError(
                "Plateforme non prise en charge : "
                f"{platform_name}"
            )

        platform = PLATFORMS[platform_name]

        # Serper est l'agrégateur qui effectue la recherche.
        serper_source = get_serper_source(session)

        # La mention sera associée à sa plateforme réelle.
        platform_source = get_platform_source(
            session=session,
            source_name=platform["source_name"],
        )

        query_text = build_social_query(
            organization_name=organization.name,
            platform_name=platform_name,
        )

        watch_query = get_or_create_social_watch_query(
            session=session,
            organization=organization,
            query_text=query_text,
            platform_name=platform_name,
        )

        print("\n" + "=" * 78)
        print(f"Organisation : {organization.name}")
        print(f"Plateforme : {platform_name}")
        print(f"Requête : {query_text}")

        pipeline_run = create_pipeline_run(
            session=session,
            source=serper_source,
            watch_query=watch_query,
            run_type="serper_social_collection",
            requested_results=MAX_RESULTS_PER_QUERY,
        )

        pipeline_run_id = pipeline_run.id

        print(
            f"Pipeline social créé : "
            f"{pipeline_run_id}"
        )

        results = client.search_web(
            query=query_text,
            language="fr",
            country="ma",
            num=MAX_RESULTS_PER_QUERY,
        )

        # Serper peut parfois retourner plus de résultats
        # que la quantité demandée.
        results = results[:MAX_RESULTS_PER_QUERY]

        items_received = len(results)
        items_created = 0
        items_duplicated = 0
        items_ignored = 0

        print(
            f"Résultats reçus : "
            f"{items_received}"
        )

        for result in results:
            if not isinstance(result, dict):
                items_ignored += 1

                print(
                    "Résultat invalide ignoré."
                )

                continue

            title = (
                clean_text(result.get("title"))
                or "Sans titre"
            )

            # Vérifier que le résultat vient réellement
            # de LinkedIn, Facebook, Instagram ou X.
            if not result_matches_platform(
                result=result,
                accepted_domains=platform[
                    "accepted_domains"
                ],
            ):
                items_ignored += 1

                print(
                    "Résultat hors plateforme ignoré : "
                    f"{title}"
                )

                continue

            external_id = create_external_id(
                result
            )

            content_hash = create_content_hash(
                result
            )

            already_exists = mention_already_exists(
                session=session,
                source_id=platform_source.id,
                external_id=external_id,
                content_hash=content_hash,
            )

            if already_exists:
                items_duplicated += 1

                print(
                    "Doublon social ignoré : "
                    f"{title}"
                )

                continue

            # Copier le résultat avant de lui ajouter
            # les informations internes de collecte.
            enriched_result = dict(result)

            enriched_result["_collection"] = {
                "channel": "social",
                "aggregator": "Serper",
                "platform": platform_name,
                "organization_id": organization.id,
                "organization_name": organization.name,
                "search_query": query_text,
            }

            mention = create_mention(
                result=enriched_result,
                source=platform_source,
                pipeline_run=pipeline_run,
                language="fr",
                country="ma",
            )

            if mention is None:
                items_ignored += 1

                print(
                    "Résultat vide ignoré : "
                    f"{title}"
                )

                continue

            session.add(mention)
            session.flush()

            items_created += 1

            print(
                "Mention sociale ajoutée : "
                f"{title}"
            )

        current_pipeline = session.get(
            PipelineRun,
            pipeline_run_id,
        )

        if current_pipeline is None:
            raise RuntimeError(
                "Impossible de retrouver "
                "le pipeline social."
            )

        current_pipeline.status = "completed"
        current_pipeline.finished_at = utc_now()
        current_pipeline.items_received = items_received
        current_pipeline.items_created = items_created
        current_pipeline.items_duplicated = (
            items_duplicated
        )
        current_pipeline.error_message = None

        current_pipeline.statistics = {
            "organization_id": organization.id,
            "organization_name": organization.name,
            "platform": platform_name,
            "query": query_text,
            "country": "ma",
            "language": "fr",
            "requested_results": MAX_RESULTS_PER_QUERY,
            "received_results": items_received,
            "created_results": items_created,
            "duplicated_results": items_duplicated,
            "ignored_results": items_ignored,
            "collection_channel": "social",
            "aggregator": "Serper",
        }

        session.commit()

        # Synchronise automatiquement les liens apres une collecte Facebook.
        if platform_name == "facebook":
            from backend.services.facebook_retained_links_service import (
                export_retained_facebook_links,
            )

            export_retained_facebook_links(session)

        print(
            f"Recherche terminée : "
            f"{items_created} nouvelle(s) mention(s), "
            f"{items_duplicated} doublon(s), "
            f"{items_ignored} résultat(s) ignoré(s)."
        )

        return {
            "organization": organization.name,
            "platform": platform_name,
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
            "\nErreur pendant la collecte sociale : "
            f"{error}"
        )

        return {
            "organization_id": organization_id,
            "platform": platform_name,
            "status": "failed",
            "received": 0,
            "created": 0,
            "duplicated": 0,
            "ignored": 0,
            "error": str(error),
        }

    finally:
        session.close()


def collect_social_mentions() -> None:
    """
    Lance la collecte sociale pour ARMA et ses concurrents
    sur LinkedIn, Facebook, Instagram et X.

    Le programme crée toutes les combinaisons entre :
    - les cinq organisations ;
    - les quatre plateformes.
    """

    session = SessionLocal()

    try:
        organizations = get_target_organizations(
            session
        )

        organization_ids = [
            organization.id
            for organization in organizations
        ]

    finally:
        session.close()

    targets: list[tuple[int, str]] = []

    # Créer toutes les combinaisons :
    # chaque plateforme pour chaque organisation.
    for platform_name in PLATFORMS_TO_RUN:
        for organization_id in organization_ids:
            targets.append(
                (
                    organization_id,
                    platform_name,
                )
            )

    # Protection supplémentaire contre un nombre
    # d'appels supérieur à la limite configurée.
    targets = targets[:MAX_QUERIES_PER_RUN]

    print("Début de la collecte sociale.")

    print(
        f"Organisations concernées : "
        f"{len(organization_ids)}"
    )

    print(
        "Plateformes activées : "
        + ", ".join(PLATFORMS_TO_RUN)
    )

    print(
        f"Appels Serper maximum : "
        f"{len(targets)}"
    )

    client = SerperClient()

    summaries: list[dict[str, Any]] = []

    for organization_id, platform_name in targets:
        summary = collect_one_social_query(
            organization_id=organization_id,
            platform_name=platform_name,
            client=client,
        )

        summaries.append(summary)

    total_received = sum(
        item["received"]
        for item in summaries
    )

    total_created = sum(
        item["created"]
        for item in summaries
    )

    total_duplicated = sum(
        item["duplicated"]
        for item in summaries
    )

    total_ignored = sum(
        item["ignored"]
        for item in summaries
    )

    total_failed = sum(
        item["status"] == "failed"
        for item in summaries
    )

    print("\n" + "=" * 78)
    print("Résumé de la collecte sociale")

    print(
        f"- Recherches exécutées : "
        f"{len(summaries)}"
    )

    print(
        f"- Recherches échouées : "
        f"{total_failed}"
    )

    print(
        f"- Résultats reçus : "
        f"{total_received}"
    )

    print(
        f"- Mentions créées : "
        f"{total_created}"
    )

    print(
        f"- Doublons ignorés : "
        f"{total_duplicated}"
    )

    print(
        f"- Résultats hors plateforme ou vides : "
        f"{total_ignored}"
    )


if __name__ == "__main__":
    collect_social_mentions()
