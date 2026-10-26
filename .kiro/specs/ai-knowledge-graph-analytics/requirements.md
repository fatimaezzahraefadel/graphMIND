# Document d'exigences — Plateforme d'analytique sur graphe de connaissances alimentée par IA

## Introduction

Cette plateforme combine Big Data (HDFS, Spark), extraction d'information par LLM, Neo4j et GraphRAG. Elle collecte des documents hétérogènes, en extrait des entités et des relations, construit **un seul graphe de connaissances** et compare, sur ce même graphe, deux approches d'analyse :

1. **Graph Analytics** : requêtes Cypher et algorithmes Neo4j Graph Data Science (GDS).
2. **GraphRAG** : récupération dans le graphe combinée à un LLM pour répondre en langage naturel.

**Domaine du corpus** : écosystème d'innovation (universités, entreprises, chercheurs, projets de R&D, technologies, événements). Le corpus est entièrement synthétique.

**Contribution visée** : une évaluation comparative de l'analytique structurée et de GraphRAG sur un graphe construit automatiquement, qui répond aux 5 questions de recherche suivantes :

- **QR1** : avec quelle précision un LLM extrait-il entités et relations de documents hétérogènes ?
- **QR2** : comment la résolution d'entités affecte-t-elle la qualité du graphe ?
- **QR3** : comment GraphRAG se comporte-t-il face à Cypher direct sur des questions multi-sauts et sémantiques ?
- **QR4** : quels compromis entre qualité des réponses, complétude, latence et coût d'inférence ?
- **QR5** : comment la provenance des sources améliore-t-elle la fiabilité et l'explicabilité des réponses ?

Approche : preuve de concept Docker Compose d'abord (HDFS, Spark, Neo4j, service d'extraction LLM, service GraphRAG), sur une petite collection et un schéma partagé, puis distribution et benchmark une fois le flux de bout en bout validé.

## Glossaire

- **Crawler** : composant de collecte, parsing et extraction des métadonnées.
- **HDFS_Storage** : stockage distribué des documents bruts et des sorties intermédiaires.
- **Graph_Schema** : schéma YAML versionné des types de nœuds, relations et propriétés, partagé par tous les services.
- **LLM_Client** : interface abstraite vers un fournisseur LLM (OpenAI, Anthropic, Ollama, Mock).
- **LLMResponse** : objet retourné par le LLM_Client (`text`, `tokens_in`, `tokens_out`, `latency_ms`).
- **Extraction_Service** : service Python qui segmente, extrait entités et relations et valide les sorties.
- **Entity_Resolver** : composant de normalisation, de déduplication et de fusion des entités.
- **Spark_ETL** : traitement Spark de validation, déduplication et transformation.
- **Neo4j_Graph** : graphe de connaissances (Neo4j + plugins GDS et APOC).
- **Graph_Analytics_Module** : requêtes Cypher et algorithmes GDS.
- **GraphRAG_Service** : récupération graphe + génération LLM avec citations.
- **Evaluator** : module de benchmark comparatif.
- **Ground_Truth** : jeu de questions de référence (`data/ground_truth.json`) et annotations d'extraction (`data/extraction_gold.json`).
- **Provenance** : lien entre un élément du graphe et le document, le passage et la position qui l'ont produit.
- **Relation explicite** : relation dont le texte justificatif (`evidence`) figure littéralement dans le passage source.
- **Relation déduite** : relation produite par le LLM sans justification vérifiable (`inferred=true`).
- **Mode mock** : exécution sans réseau ni clé API (`MOCK_CRAWLER=true`, `MOCK_LLM=true`, `MOCK_EMBEDDINGS=true`).

---

## Exigences

### Exigence 1 : Collecte de sources hétérogènes

**User Story :** En tant que data engineer, je veux collecter des documents depuis plusieurs types de sources, afin d'alimenter la plateforme avec des données variées.

#### Critères d'acceptation

1. QUAND une configuration de sources est fournie, ALORS le Crawler DOIT collecter les documents de chaque source configurée.
2. Le Crawler DOIT supporter les types de source : pages web, API JSON, système de fichiers, emails (`.eml`) et base de données (résultat de requête SQL).
3. SI une source est inaccessible, ALORS le Crawler DOIT journaliser l'URL ou le chemin et le type d'erreur, puis continuer avec les sources restantes.
4. QUAND il collecte une source web, ALORS le Crawler DOIT respecter `robots.txt` et appliquer une limite de débit configurable.
5. Le Crawler DOIT ne collecter que les sources figurant dans une liste d'autorisation configurée (`ALLOWED_SOURCES`).

### Exigence 2 : Parsing multi-formats

**User Story :** En tant que data engineer, je veux extraire le texte de chaque format de document, afin de le fournir à l'extraction.

#### Critères d'acceptation

1. QUAND un document HTML est parsé, ALORS le parseur DOIT supprimer balises, scripts, styles et éléments multimédias.
2. QUAND un PDF est parsé, ALORS le parseur DOIT extraire le texte page par page en préservant l'ordre de lecture.
3. QUAND un document Word est parsé, ALORS le parseur DOIT extraire les paragraphes et le contenu des tableaux.
4. QUAND un email est parsé, ALORS le parseur DOIT extraire expéditeur, destinataire, objet, date et corps.
5. QUAND un JSON est parsé, ALORS le parseur DOIT conserver la hiérarchie des clés et extraire les valeurs textuelles.
6. QUAND des lignes de base de données sont parsées, ALORS le parseur DOIT les sérialiser en texte en conservant les noms de colonnes.
7. SI le type de document n'est pas supporté, ALORS le Crawler DOIT lever `UnsupportedDocumentTypeError`, journaliser l'événement et ignorer le document.
8. SI un fichier est corrompu, ALORS le Crawler DOIT journaliser l'identifiant du document et continuer.

### Exigence 3 : Stockage HDFS et métadonnées

**User Story :** En tant que data engineer, je veux stocker les documents bruts avec leurs métadonnées, afin de garantir la traçabilité et la reproductibilité.

#### Critères d'acceptation

1. Le Crawler DOIT stocker chaque document brut dans HDFS_Storage dans son format original, sous `/data/raw/{document_type}/{content_hash}`.
2. Le Crawler DOIT associer à chaque document les métadonnées : `source`, `collected_at` (ISO 8601), `document_type`, `content_hash` (SHA-256), `license`.
3. Le `content_hash` DOIT être reproductible : un même contenu produit toujours le même hash.
4. SI un document de même `content_hash` existe déjà, ALORS le Crawler DOIT ne pas le réécrire (ingestion idempotente).

### Exigence 4 : Corpus synthétique et mode mock

**User Story :** En tant que développeur, je veux un corpus synthétique reproductible, afin de tester le pipeline sans réseau et sans droits tiers.

#### Critères d'acceptation

1. Le dépôt DOIT contenir un corpus de 20 à 30 documents synthétiques couvrant HTML, PDF, Word, JSON et email, dans le domaine de l'écosystème d'innovation.
2. Le corpus DOIT inclure des variantes de noms volontaires pour une même entité (ex. « Université Atlas de Rabat », « Univ. Atlas Rabat », « UAR ») afin de rendre la résolution d'entités mesurable.
3. Le corpus DOIT contenir des chaînes de relations permettant des questions multi-sauts (ex. personne → organisation → projet → technologie).
4. Le corpus DOIT être généré de façon déterministe par un script (`scripts/generate_corpus.py`, graine fixe) et chaque fichier DOIT porter la licence « synthétique ».
5. QUAND `MOCK_CRAWLER=true`, ALORS le Crawler DOIT utiliser exclusivement le corpus local, sans accès réseau.

### Exigence 5 : Schéma de graphe partagé

**User Story :** En tant qu'architecte, je veux un schéma unique et versionné, afin que tous les composants soient cohérents.

#### Critères d'acceptation

1. Le Graph_Schema DOIT être défini dans `config/graph_schema.yaml` avec un numéro de version.
2. Le Graph_Schema DOIT définir les types de nœuds : `Person`, `Organization`, `Location`, `Project`, `Technology`, `Event`, `Document`.
3. Le Graph_Schema DOIT définir les types de relations avec types source et cible autorisés : `WORKS_FOR`, `COLLABORATES_WITH`, `LOCATED_IN`, `LEADS`, `PARTICIPATES_IN`, `FUNDS`, `USES`, `ORGANIZES`, `MENTIONS`.
4. Le Graph_Schema DOIT définir les propriétés communes : `confidence_score` ∈ [0, 1] et `inferred` (booléen).
5. Le Graph_Schema DOIT fournir `validate_node`, `validate_relation` et `is_compatible(autre_schema)`.
6. Tous les services DOIVENT lire le même fichier de schéma au démarrage.

### Exigence 6 : Client LLM abstrait

**User Story :** En tant que développeur, je veux changer de fournisseur LLM sans modifier le code métier, afin de comparer des modèles et de tester sans API.

#### Critères d'acceptation

1. Le LLM_Client DOIT exposer `extract_entities`, `extract_relations`, `generate_response`, chacune retournant un `LLMResponse` (`text`, `tokens_in`, `tokens_out`, `latency_ms`) ou un résultat structuré accompagné de cet objet.
2. Le système DOIT fournir les implémentations **réelles** `OpenAIClient`, `AnthropicClient` et `OllamaClient`, ainsi que `MockLLMClient`.
3. QUAND `create_llm_client()` est appelée, ALORS elle DOIT lire `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `MOCK_LLM` depuis l'environnement.
4. SI la configuration est invalide ou une clé manque hors mode mock, ALORS le système DOIT lever `LLMConfigError` en nommant la variable manquante.
5. Le `MockLLMClient` DOIT être déterministe : deux appels avec la même entrée produisent la même sortie.
6. Le système DOIT journaliser à chaque appel le modèle, `tokens_in`, `tokens_out` et la latence.
7. SI une erreur réseau, un délai dépassé ou une limite de débit survient, ALORS le système DOIT lever `LLMCallError` sans modifier l'état du pipeline.
8. Les prompts d'extraction DOIVENT injecter le Graph_Schema et exiger une sortie JSON conforme.

### Exigence 7 : Segmentation et extraction d'entités

**User Story :** En tant que data scientist, je veux extraire des entités typées de chaque passage, afin de peupler le graphe.

#### Critères d'acceptation

1. Le système DOIT segmenter chaque document en passages d'au plus 2000 caractères, en respectant les limites de mots.
2. Le système DOIT n'accepter que des types d'entités définis dans le Graph_Schema.
3. Chaque entité DOIT avoir `label`, `type`, `confidence_score` et une provenance (`source_doc`, `passage_id`, `char_offset`).
4. QUAND le libellé d'une entité apparaît littéralement (après normalisation) dans le passage, ALORS l'entité DOIT être marquée `inferred=false`, sinon `inferred=true`.
5. SI le passage est vide, ALORS le système DOIT ne pas appeler le LLM.
6. L'identifiant d'une entité DOIT être déterministe (voir exigence 10.2).

### Exigence 8 : Extraction de relations

**User Story :** En tant que data scientist, je veux extraire des relations justifiées, afin de distinguer faits explicites et déductions.

#### Critères d'acceptation

1. Le système DOIT extraire les relations entre les entités détectées dans le même passage.
2. Le type, la direction et les types d'extrémités d'une relation DOIVENT être compatibles avec le Graph_Schema.
3. Chaque relation DOIT porter un champ `evidence` (extrait du passage justifiant la relation), un `confidence_score` et une provenance.
4. QUAND `evidence` est non vide ET figure dans le passage (après normalisation), ALORS la relation DOIT être marquée `inferred=false`.
5. SI `evidence` est vide ou absent du passage, ALORS la relation DOIT être marquée `inferred=true` et `evidence` DOIT être vidé.
6. SI une relation référence une entité inconnue, ALORS le système DOIT l'ignorer et journaliser l'anomalie.

### Exigence 9 : Validation, sérialisation et reprise sur erreur

**User Story :** En tant qu'ingénieur, je veux des sorties validées et des échecs maîtrisés, afin d'avoir un pipeline fiable.

#### Critères d'acceptation

1. Le système DOIT valider toute sortie d'extraction avec des modèles Pydantic.
2. La sérialisation JSON puis la désérialisation d'une entité ou d'une relation DOIT produire un objet identique champ par champ.
3. SI une sortie ne respecte pas le format, ALORS le système DOIT lever `ExtractionParseError` et réessayer jusqu'à 3 fois avec un prompt reformulé et un backoff exponentiel.
4. SI un appel LLM échoue avec `LLMCallError`, ALORS le système DOIT réessayer avec un backoff exponentiel.
5. SI l'échec persiste après les réessais, ALORS le système DOIT journaliser `document_id` et `passage_id`, ignorer le passage et continuer.
6. Un `confidence_score` hors de [0, 1] DOIT être rejeté comme non conforme.

### Exigence 10 : Résolution d'entités

**User Story :** En tant que data scientist, je veux fusionner les doublons, afin d'obtenir un graphe sans entités redondantes.

#### Critères d'acceptation

1. L'Entity_Resolver DOIT normaliser les libellés (minuscules, espaces, accents, ponctuation).
2. Les identifiants DOIVENT être déterministes : `sha256("{type}:{libellé_normalisé}")[:16]` pour les entités, `sha256("{relation_type}:{id_source}:{id_cible}")[:16]` pour les relations.
3. L'Entity_Resolver DOIT comparer les entités uniquement au sein d'un même type, avec la similarité `rapidfuzz` et un seuil configurable `SIMILARITY_THRESHOLD` (défaut 0,85).
4. QUAND deux entités sont fusionnées, ALORS le résultat DOIT contenir l'union de leurs provenances, la liste des alias, et le score de confiance maximal.
5. QUAND des entités sont fusionnées, ALORS les `source_entity_id` et `target_entity_id` des relations DOIVENT être réécrits vers l'identifiant canonique ; aucune relation ne DOIT pointer vers une entité inexistante.
6. QUAND `ENABLE_ENTITY_RESOLUTION=false`, ALORS le pipeline DOIT contourner la fusion floue (seule la normalisation d'identifiant reste appliquée).
7. Le système DOIT journaliser chaque fusion avec les entités sources et l'entité résultante.
8. QUAND une entité fusionnée combine des marquages différents, ALORS `inferred` DOIT valoir `false` si au moins une source est explicite.

### Exigence 11 : Persistance des extractions et cache

**User Story :** En tant que chercheur, je veux rejouer l'ETL sans rappeler le LLM, afin de réduire coût et variabilité des expériences.

#### Critères d'acceptation

1. Le Extraction_Service DOIT écrire les `ExtractionOutput` en JSON Lines dans HDFS sous `/data/extracted/{run_id}/`.
2. Chaque exécution DOIT enregistrer ses métadonnées : modèle LLM, version du prompt, version du Graph_Schema, valeur de `ENABLE_ENTITY_RESOLUTION`.
3. Le système DOIT mettre en cache les extractions par clé (hash du passage, modèle, version du prompt) et réutiliser le cache lors d'une réexécution.

### Exigence 12 : ETL Spark

**User Story :** En tant que data engineer, je veux valider, dédupliquer et transformer à grande échelle, afin de charger un graphe propre.

#### Critères d'acceptation

1. Le Spark_ETL DOIT lire les extractions depuis HDFS.
2. Le Spark_ETL DOIT valider chaque entité et relation contre le Graph_Schema.
3. SI un élément viole le schéma, ALORS le Spark_ETL DOIT l'isoler dans `/data/errors/` au format JSON (`document_id`, `entity_id`, `violation`, `raw_data`, `timestamp`).
4. Le Spark_ETL DOIT dédupliquer par identifiant en fusionnant les provenances et en conservant le score maximal.
5. Le Spark_ETL DOIT conserver les métadonnées de provenance à travers toutes les transformations.
6. Le Spark_ETL DOIT écrire les données prêtes à charger en JSON Lines dans `/data/curated/`.
7. Le Spark_ETL DOIT lire `SPARK_MASTER_URL` et supporter le mode `local[*]` pour les tests.

### Exigence 13 : Chargement dans Neo4j

**User Story :** En tant que data engineer, je veux un chargement idempotent et traçable, afin que le graphe soit cohérent après chaque rejeu.

#### Critères d'acceptation

1. Le chargeur DOIT créer des contraintes d'unicité sur `id` pour chaque type de nœud.
2. Le chargeur DOIT créer des index sur `label` et `type`.
3. Le chargeur DOIT utiliser des `MERGE` par lots (`UNWIND`) afin que charger deux fois les mêmes données ne crée aucun doublon.
4. Les labels de nœuds et types de relations insérés dans les requêtes DOIVENT être validés contre le Graph_Schema (liste blanche).
5. Le chargeur DOIT créer un nœud `Document` par document collecté, à partir des métadonnées du Crawler.
6. Le chargeur DOIT créer, pour chaque entité extraite, une relation `MENTIONS` (`Document` → entité) portant `passage_id`, `char_offset` et `confidence_score`.
7. QUAND une relation existe déjà, ALORS le `MERGE` DOIT ne pas écraser sa provenance : `evidence` et `source_docs` sont unis, `confidence_score` prend le maximum, `inferred` vaut `false` si au moins une source est explicite.
8. SI le chargement échoue, ALORS le chargeur DOIT lever `Neo4jLoadError` avec le contexte.
9. Le chargeur DOIT fournir une commande de réinitialisation du graphe pour les expériences.

### Exigence 14 : Embeddings et index vectoriels

**User Story :** En tant que data scientist, je veux une recherche sémantique sur le graphe, afin de répondre aux questions formulées sans libellé exact.

#### Critères d'acceptation

1. Le système DOIT fournir un `Embedder` abstrait avec une implémentation réelle (`sentence-transformers`, modèle multilingue) et une implémentation mock déterministe (`MOCK_EMBEDDINGS=true`).
2. La dimension des vecteurs DOIT être configurable (`EMBEDDING_DIM`).
3. Le texte embeddé d'un nœud DOIT combiner son libellé, ses alias et sa description.
4. Le système DOIT créer un index vectoriel Neo4j par type de nœud.
5. SI le modèle ou la dimension change, ALORS le système DOIT recréer les index et recalculer les embeddings.

### Exigence 15 : Graph Analytics — requêtes Cypher

**User Story :** En tant qu'analyste, je veux des requêtes réutilisables, afin d'interroger le graphe de façon structurée.

#### Critères d'acceptation

1. Le module DOIT fournir `get_neighborhood(node_id, depth)` avec les nœuds voisins, relations et types.
2. Le module DOIT fournir `find_paths(from_id, to_id, max_depth)` avec la longueur et la séquence de nœuds ; un chemin introuvable donne un résultat vide, pas une erreur.
3. Le module DOIT fournir `multi_hop_query(start_id, hops, relation_types)`.
4. Le module DOIT fournir `aggregate(query, params)` avec requêtes paramétrées.
5. Chaque résultat DOIT inclure `confidence_score`, `inferred` et les documents sources (via `MENTIONS`).
6. Le module DOIT valider les paramètres (profondeur bornée, types de relations dans la liste blanche).

### Exigence 16 : Graph Analytics — algorithmes GDS

**User Story :** En tant qu'analyste, je veux exécuter des algorithmes de graphe, afin de révéler la structure du réseau.

#### Critères d'acceptation

1. Le module DOIT créer ou réutiliser une projection GDS (`_get_or_create_projection`) avec une propriété de poids (`confidence_score`).
2. Le module DOIT fournir PageRank, détection de communautés (Louvain), centralité d'intermédiarité, plus court chemin (Dijkstra) et similarité de nœuds.
3. Le coût d'une arête pour Dijkstra DOIT valoir `1 - confidence_score`.
4. Le module DOIT journaliser l'algorithme, ses paramètres et son temps d'exécution.
5. Les associations produites par similarité ou communautés DOIVENT être étiquetées `computed` et ne jamais être présentées comme des faits vérifiés.

### Exigence 17 : GraphRAG — récupération

**User Story :** En tant qu'utilisateur, je veux poser une question en langage naturel, afin d'obtenir le contexte pertinent du graphe.

#### Critères d'acceptation

1. Le GraphRAG_Service DOIT identifier les entités mentionnées dans la question (entity linking par libellé, alias et similarité vectorielle).
2. Le service DOIT supporter les modes `vector`, `neighborhood`, `text2cypher` et `hybrid`, choisis par `RETRIEVAL_MODE` (défaut `hybrid`).
3. En mode vectoriel, le service DOIT interroger les index vectoriels par similarité.
4. En mode voisinage, le service DOIT étendre le sous-graphe des entités liées sur une profondeur configurable.
5. En mode Text2Cypher, le service DOIT générer une requête Cypher via le LLM en injectant le Graph_Schema dans le prompt.
6. Le service DOIT exécuter toute requête générée dans une **transaction en lecture seule** et DOIT rejeter toute requête contenant une clause d'écriture (`CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DROP`, `LOAD CSV`, `FOREACH`) ou un appel de procédure hors liste blanche.
7. Le service DOIT limiter le contexte à `MAX_CONTEXT_NODES` nœuds.
8. Le service DOIT collecter la provenance de chaque nœud et relation récupérés.

### Exigence 18 : GraphRAG — génération de réponses

**User Story :** En tant qu'utilisateur, je veux une réponse sourcée, afin de vérifier ce qu'elle affirme.

#### Critères d'acceptation

1. Le service DOIT construire un contexte structuré (nœuds, relations, passages sources) dans la limite configurée.
2. Le prompt DOIT imposer de répondre uniquement à partir du contexte fourni.
3. Chaque réponse DOIT inclure des citations (`source_doc`, `passage_id`, `node_id`, `is_inferred`, `confidence_score`).
4. QUAND une information provient d'un élément inféré, ALORS la réponse DOIT l'indiquer explicitement.
5. SI le contexte est vide ou insuffisant, ALORS le service DOIT retourner une réponse partielle avec `is_partial=true` et ne pas inventer de contenu.
6. Le service DOIT journaliser la question, la requête de récupération, le contexte, les tokens et la latence totale.

### Exigence 19 : Vérité terrain

**User Story :** En tant que chercheur, je veux des références fiables, afin de mesurer objectivement les approches.

#### Critères d'acceptation

1. `data/ground_truth.json` DOIT contenir au moins 20 questions, avec au moins 5 de chaque type : `multi_hop`, `semantic`, `neighborhood`, `aggregation`.
2. Chaque question DOIT inclure `id`, `text`, `type`, `expected_entities`, `expected_answer_contains`, `cypher_query` et `notes`.
3. Le champ `cypher_query` DOIT être une requête Cypher de référence exécutable, utilisée par l'approche Graph Analytics.
4. `data/extraction_gold.json` DOIT lister, par document, les entités et relations attendues.
5. Les fichiers DOIVENT être versionnés dans le dépôt.
6. Un script de cohérence DOIT vérifier que les entités attendues existent dans `extraction_gold.json` et que chaque `cypher_query` est syntaxiquement valide.

### Exigence 20 : Métriques d'évaluation

**User Story :** En tant que chercheur, je veux des métriques comparables, afin de répondre aux questions de recherche.

#### Critères d'acceptation

1. L'Evaluator DOIT calculer précision et rappel en comparant l'ensemble d'entités retournées à l'ensemble attendu.
2. Pour GraphRAG, l'ensemble retourné DOIT combiner les entités citées et les entités du graphe identifiées dans le texte de la réponse ; un juge LLM optionnel (`JUDGE_ENABLED`) PEUT compléter la vérification.
3. L'Evaluator DOIT calculer par approche et par type de question : précision, rappel, latence (moyenne, médiane, min, max, écart-type) et coût en tokens (avec tarifs configurables).
4. L'Evaluator DOIT mesurer l'explicabilité : présence de citations, validité des citations (document existant), marquage correct des éléments inférés, traçabilité vers HDFS.
5. L'Evaluator DOIT mesurer la qualité d'extraction (précision, rappel, F1 par type) contre `extraction_gold.json`.
6. L'Evaluator DOIT mesurer la qualité du graphe : nombre de doublons restants et de nœuds orphelins.

### Exigence 21 : Expériences et rapport

**User Story :** En tant que chercheur, je veux un rapport reproductible, afin de documenter les conclusions.

#### Critères d'acceptation

1. **E1** : le système DOIT évaluer l'extraction contre `extraction_gold.json` (QR1).
2. **E2** : le système DOIT rejouer l'ETL depuis les extractions persistées avec `ENABLE_ENTITY_RESOLUTION` activé puis désactivé, et comparer la qualité du graphe et les réponses (QR2).
3. **E3** : le système DOIT comparer Graph Analytics et GraphRAG par type de question (QR3, QR4).
4. **E4** : le système DOIT comparer les modes de récupération `vector`, `neighborhood`, `text2cypher` et `hybrid`.
5. Le rapport Markdown DOIT contenir des tableaux comparatifs et une section dédiée à chacune des 5 questions de recherche, dont l'apport de la provenance (QR5).
6. Le rapport DOIT enregistrer la configuration (modèles, versions, seuils, graine) pour la reproductibilité.
7. SI le benchmark est exécuté avec `MOCK_LLM=true`, ALORS le rapport DOIT l'indiquer et considérer les résultats comme non significatifs.

### Exigence 22 : API REST

**User Story :** En tant que client, je veux une API cohérente, afin d'utiliser toutes les fonctions de la plateforme.

#### Critères d'acceptation

1. L'API FastAPI DOIT exposer : `POST /ingest` (admin), `POST /extract` (admin), `GET /analytics/neighborhood/{node_id}`, `GET /analytics/paths`, `POST /analytics/gds/{algorithm}`, `POST /graphrag/ask`, `POST /evaluate` (admin), `GET /schema`, `GET /health` (public).
2. L'API DOIT valider les entrées avec Pydantic et retourner HTTP 422 en cas d'entrée invalide.
3. L'API DOIT retourner des codes HTTP appropriés et une documentation OpenAPI.
4. La sérialisation puis la désérialisation d'une réponse DOIT produire un objet identique.

### Exigence 23 : Authentification et autorisation

**User Story :** En tant qu'administrateur, je veux contrôler l'accès, afin de protéger les fonctions sensibles.

#### Critères d'acceptation

1. L'API DOIT utiliser des jetons JWT (secret `JWT_SECRET`, durée `JWT_EXPIRE_MINUTES`) avec le rôle dans les claims.
2. Les rôles DOIVENT être `admin` et `user`.
3. SI l'utilisateur n'est pas authentifié, ALORS l'API DOIT retourner HTTP 401 ; SI le rôle est insuffisant, ALORS HTTP 403.
4. Les mots de passe DOIVENT être hachés avec bcrypt et jamais stockés en clair.
5. Le compte administrateur initial DOIT provenir de `ADMIN_USERNAME` et `ADMIN_PASSWORD`.

### Exigence 24 : Interface utilisateur

**User Story :** En tant qu'utilisateur, je veux une interface simple, afin d'explorer le graphe et poser des questions.

#### Critères d'acceptation

1. L'interface Streamlit DOIT proposer les pages : Graphe, Questions, Analytics, Évaluation.
2. La page Graphe DOIT visualiser nœuds et arêtes (bibliothèque `pyvis` ou `streamlit-agraph`) et afficher la provenance d'un élément sélectionné.
3. L'interface DOIT distinguer visuellement les éléments inférés des éléments explicites.
4. La page Questions DOIT afficher la réponse, les citations et le mode de récupération.
5. La page Évaluation DOIT lancer le benchmark et afficher le rapport.

### Exigence 25 : Monitoring et journalisation

**User Story :** En tant qu'exploitant, je veux observer le système, afin de diagnostiquer les problèmes.

#### Critères d'acceptation

1. Le système DOIT produire des logs JSON structurés (`timestamp`, `level`, `component`, `event`, contexte).
2. Le système DOIT exposer les métriques : documents ingérés, nœuds par type, latence et tokens des appels LLM, latence des requêtes GraphRAG.
3. `GET /health` DOIT retourner l'état de Neo4j, HDFS, Spark et du LLM.
4. Le système DOIT journaliser toute erreur avec un contexte suffisant au diagnostic, sans jamais journaliser de secret.

### Exigence 26 : Éthique, provenance et rétention

**User Story :** En tant que responsable de conformité, je veux un usage licite et traçable, afin de limiter les risques.

#### Critères d'acceptation

1. Le système DOIT se limiter à des sources licites et autorisées ; le corpus de démonstration DOIT être entièrement synthétique et ne contenir aucune donnée personnelle réelle.
2. Le système DOIT appliquer le contrôle d'accès de l'exigence 23.
3. Le dépôt DOIT contenir `docs/data_retention_policy.md` (durées de conservation des documents, du graphe et des logs) et une commande de purge.
4. Le système NE DOIT PAS présenter une association inférée ou calculée comme un fait vérifié.
5. Chaque élément du graphe DOIT être traçable jusqu'au document source.

### Exigence 27 : Infrastructure et configuration

**User Story :** En tant que développeur, je veux tout lancer en une commande, afin de reproduire l'environnement.

#### Critères d'acceptation

1. Le `docker-compose.yml` DOIT définir : `namenode`, `datanode`, `spark-master`, `spark-worker`, `neo4j` (GDS et APOC), `llm-extraction`, `graphrag-service`, `fastapi`, `streamlit`.
2. Tous les services DOIVENT partager un réseau unique `graphmind`.
3. Le Compose DOIT définir des `healthcheck` et `depends_on` dans l'ordre de démarrage correct.
4. Le service `llm-extraction` DOIT exécuter le job Spark via `spark-submit`.
5. Un profil allégé (un seul datanode, Spark en mode local) DOIT être disponible pour les machines à mémoire limitée.
6. `.env.example` DOIT documenter toutes les variables sans secret réel, dont `JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
7. Le `Makefile` DOIT fournir : `make up`, `make ingest`, `make extract`, `make etl`, `make benchmark`, `make test-phase1` à `make test-phase7`, `make test-all`.
8. Le `README.md` DOIT contenir l'installation, le lancement, un schéma Mermaid de l'architecture, le Graph_Schema, les décisions techniques, les limites connues et la politique de données.
9. Les dépendances DOIVENT être épinglées.

### Exigence 28 : Stratégie de tests

**User Story :** En tant que développeur, je veux des tests fiables, afin de valider chaque phase.

#### Critères d'acceptation

1. Le projet DOIT utiliser `pytest` ; les propriétés universelles DOIVENT être testées avec Hypothesis (au moins 100 exemples par propriété).
2. Le pipeline complet DOIT s'exécuter de bout en bout en mode mock, sans réseau ni clé API.
3. Les tests d'intégration Neo4j et HDFS DOIVENT utiliser des conteneurs (`testcontainers`).
4. Les tests Hypothesis NE DOIVENT PAS utiliser de fixture à portée fonction dans `@given` ; les dépendances sont instanciées dans le test.
5. Chaque phase DOIT avoir une cible `make test-phaseN`.
