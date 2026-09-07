# Modifications V9 finale n8n

## Orchestration

- n8n devient l'orchestrateur quotidien officiel ;
- préflight API, déclencheur manuel et planifié à 07:00 ;
- 19 étapes métier séquentielles et traçables ;
- verrou anti-double exécution ;
- statut `completed` ou `partial` et contrôle qualité final ;
- suppression des scripts de planification Windows pour éviter les doublons.

## POC Marketing

- 8 brouillons FR/AR sur LinkedIn, Instagram, Facebook et X ;
- numérotation 1/8 à 8/8 ;
- dédoublonnage d'événements multi-sources ;
- garde-fou factuel : promesses absolues, nombres, villes et technologies non
  soutenus par les preuves sont refusés ;
- correction des fragments comme « notre commitment » et `#MarochesDemain` ;
- gabarit de secours prudent en cas d'échec Claude ;
- prompts d'images sans logo/uniforme ARMA inventé ;
- indicateurs de contrôle qualité et de fallback dans l'API.

## POC Réputation

- périodes hebdomadaires adjacentes sans chevauchement ;
- formule versionnée `v3_weighted_non_overlapping` ;
- reclassification des anciennes alertes ouvertes ;
- sévérité haute pour paie/RH, juridique, autorités, marchés publics et conflits
  sociaux ;
- régénération des décisions Claude après reclassification ;
- statuts `acknowledged` et `resolved` exposés dans le portail ;
- benchmark sans score artificiel lorsque le volume est nul.

## Qualité et sécurité

- endpoint `/api/quality/status` ;
- clé n8n comparée de manière sécurisée ;
- aucun secret dans le workflow ou le ZIP ;
- imports de packages sans connexion implicite à PostgreSQL ;
- tests unitaires et structurels couvrant les règles V9.
