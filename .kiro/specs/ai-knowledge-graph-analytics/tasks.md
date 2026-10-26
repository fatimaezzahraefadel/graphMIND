# Plan d'implémentation — Plateforme d'analytique sur graphe de connaissances alimentée par IA

## Vue d'ensemble

Le plan suit les 7 phases du PDF. Chaque phase livre un composant validé par des tests. Le flux de bout en bout est d'abord validé **en mode mock** sur le corpus synthétique (`MOCK_CRAWLER`, `MOCK_LLM`, `MOCK_EMBEDDINGS`), puis avec un vrai LLM pour le benchmark.

Langage : Python 3.11+ (PySpark, FastAPI, Streamlit, Hypothesis, pytest, testcontainers).

Les tâches marquées `*` sont optionnelles (tests) mais fortement recommandées ; ne pas les ignorer toutes.

**Règle d'exécution** : s'arrêter à chaque checkpoint et faire valider le résultat avant de continuer. Ne pas enchaîner toutes les phases sans vérifier le flux de bout en bout.

---

## Tâches

- [ ] 1. Fondations du projet
  - Créer l'arborescence : `src/{shared,crawler,llm,extraction,resolver,etl,embeddings,analytics,graphrag,evaluation,api,ui}`, `tests/`, `config/`, `data/`, `docker/`, `scripts/`, `docs/`
  - Créer `src/shared/exceptions.py` : `PlatformError`, `CrawlerError`, `UnsupportedDocumentTypeError`, `LLMConfigError`, `LLMCallError`, `ExtractionParseError`, `SchemaViolationError`, `EntityResolutionError`, `SparkETLError`, `Neo4jLoadError`, `GraphAnalyticsError`, `GraphRAGError`, `AuthError` (ne pas utiliser le nom `ValidationError`)
  - Créer `src/shared/logging.py` : logs JSON structurés avec `structlog`, sans secrets
  - Créer `config/graph_schema.yaml` (7 types de nœuds, 9 types de relations, propriétés communes) et `src/shared/graph_schema.py` (`GraphSchema.load`, `validate_node`, `validate_relation`, `is_compatible`, `assert_node_type`, `assert_relation_type`)
  - Créer `src/shared/ids.py` : `normalize_label`, `entity_id`, `relation_id` (sha256 tronqué à 16 caractères)
  - Créer `src/shared/config.py` : lecture centralisée des variables d'environnement
  - Créer `.env.example` complet (LLM, embeddings, résolution d'entités, infrastructure, GraphRAG, crawler, auth `JWT_SECRET`/`ADMIN_USERNAME`/`ADMIN_PASSWORD`, évaluation) sans secret réel
  - Créer `requirements.txt` (dépendances épinglées) et la configuration `pytest` / profil Hypothesis (100 exemples)
  - _Exigences : 5, 10.2, 27.6, 27.9, 28.1_

- [ ] 2. Phase 1 — Crawler et ingestion HDFS
  - [ ] 2.1 Modèles et configuration du Crawler
    - `DocumentMetadata`, `ParsedDocument`, `CrawlerConfig` dans `src/crawler/collector.py`
    - Hash SHA-256 reproductible du contenu brut
    - _Exigences : 3.2, 3.3_
  - [ ] 2.2 Parseurs
    - HTML, PDF (ordre de lecture), Word (paragraphes et tableaux), email (`.eml`), JSON (hiérarchie des clés), lignes de base de données
    - `UnsupportedDocumentTypeError` + log pour un type non supporté ; log + continuation pour un fichier corrompu
    - _Exigences : 2.1 à 2.8_
  - [ ] 2.3 Sources de collecte
    - `src/crawler/sources/` : web (respect de `robots.txt`, limite de débit), API JSON, système de fichiers, emails, base de données
    - Liste d'autorisation `ALLOWED_SOURCES` ; source inaccessible → log et continuation
    - _Exigences : 1.1 à 1.5_
  - [ ] 2.4 Écriture HDFS
    - `src/crawler/hdfs_writer.py` (WebHDFS) : `/data/raw/{document_type}/{content_hash}` + métadonnées ; document déjà présent → ignoré
    - _Exigences : 3.1, 3.2, 3.4_
  - [ ] 2.5 Corpus synthétique
    - `scripts/generate_corpus.py` (graine fixe) : 20 à 30 documents HTML, PDF, Word, JSON, email dans le domaine de l'écosystème d'innovation
    - Variantes de noms volontaires (ex. « Université Atlas de Rabat » / « Univ. Atlas Rabat » / « UAR »), chaînes de relations multi-sauts, licence « synthétique » dans les métadonnées
    - _Exigences : 4.1 à 4.4, 26.1_
  - [ ] 2.6 Classe `Crawler` principale
    - `collect`, `parse_document`, `write_to_hdfs` ; mode mock (`MOCK_CRAWLER=true`) sans accès réseau
    - _Exigences : 1, 3, 4.5_
  - [ ]* 2.7 Tests Phase 1
    - Unitaires : chaque parseur, source inaccessible, type non supporté, fichier corrompu, ingestion idempotente
    - Propriété : hash stable pour un même contenu ; date `collected_at` au format ISO 8601
    - _Exigences : 2, 3, 28_

- [ ] 3. Docker Compose minimal et Makefile de base
  - `docker-compose.yml` : `namenode`, `datanode`, `spark-master`, `spark-worker`, `neo4j` (plugins GDS et APOC), réseau unique `graphmind`, `healthcheck` et `depends_on`
  - Profil allégé (un seul datanode, Spark en mode local)
  - `Makefile` : `make up`, `make down`, `make test-phase1`, `make test-all`
  - Script `scripts/init_neo4j.cypher` : contraintes d'unicité sur `id` pour chaque type de nœud et index sur `label` et `type`
  - Test de fumée : écrire puis relire un fichier dans HDFS, ouvrir une session Spark, exécuter une requête Neo4j
  - _Exigences : 13.1, 13.2, 27.1 à 27.3, 27.5, 27.7_

- [ ] 4. Checkpoint Phase 1
  - Lancer `make up`, `MOCK_CRAWLER=true`, vérifier que le corpus est stocké dans HDFS avec ses métadonnées
  - `pytest tests/phase1_ingestion/ -v`
  - Demander à l'utilisateur de valider avant de continuer

- [ ] 5. Phase 2 — Client LLM
  - [ ] 5.1 Interface et fabrique
    - `LLMResponse` (`text`, `tokens_in`, `tokens_out`, `latency_ms`), `LLMClient` abstrait, `create_llm_client()` (lit `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `MOCK_LLM`), `LLMConfigError` nommant la variable manquante
    - _Exigences : 6.1, 6.3, 6.4_
  - [ ] 5.2 Implémentations
    - `MockLLMClient` déterministe (sortie dérivée du hash du passage)
    - Implémentations **réelles** : `OpenAIClient`, `AnthropicClient`, `OllamaClient` (aucun stub différé)
    - Journalisation modèle, tokens, latence ; `LLMCallError` sur réseau, délai ou limite de débit
    - Prompts d'extraction : injection du Graph_Schema, sortie JSON exigée, champ `evidence` demandé pour chaque relation
    - _Exigences : 6.2, 6.5 à 6.8_
  - [ ]* 5.3 Tests du client LLM
    - Unitaires : configuration manquante, erreur réseau, journalisation (client HTTP simulé pour les providers réels)
    - Propriété 9 : déterminisme du mock (`tests/phase2_extraction/`)
    - _Exigences : 6, 28.4_

- [ ] 6. Phase 2 — Modèles et service d'extraction
  - [ ] 6.1 Modèles Pydantic
    - `Provenance`, `EntityResult` (avec `aliases`, `provenances: list[Provenance]`, `inferred`), `RelationResult` (avec `evidence`), `ExtractionOutput`
    - Validation de `confidence_score` dans [0, 1]
    - _Exigences : 7.3, 8.3, 9.1, 9.2, 9.6_
  - [ ]* 6.2 Tests de propriétés des modèles
    - Propriété 1 (round-trip entités), 2 (round-trip relations), 3 (score borné)
    - _Exigences : 9.2, 9.6_
  - [ ] 6.3 Segmenteur et extracteurs
    - `segmenter.py` (≤ 2000 caractères, limites de mots), `entity_extractor.py`, `relation_extractor.py`
    - Passage vide → aucun appel LLM
    - Rejet des types hors Graph_Schema, des relations incompatibles et des relations référençant une entité inconnue (log)
    - _Exigences : 7.1, 7.2, 7.5, 8.1, 8.2, 8.6_
  - [ ] 6.4 Vérification de l'evidence
    - `evidence_checker.py` : après normalisation, `evidence` sous-chaîne du passage → `inferred=False`, sinon `inferred=True` et `evidence=""` ; même logique pour le libellé des entités
    - _Exigences : 7.4, 8.4, 8.5_
  - [ ]* 6.5 Test de propriété 4
    - Cohérence explicite/inféré sur des passages et des evidences générés
    - _Exigences : 7.4, 8.4, 8.5_
  - [ ] 6.6 Service d'extraction
    - `service.py` : lecture HDFS → segmentation → extraction → vérification → `ExtractionOutput`
    - `extract_with_retry` : 3 essais, prompt reformulé, backoff exponentiel sur `ExtractionParseError` et `LLMCallError`
    - Échec définitif : log (`document_id`, `passage_id`) et continuation
    - Cache par clé (hash du passage, modèle, `PROMPT_VERSION`)
    - Écriture JSON Lines dans `/data/extracted/{run_id}/` et `run_meta.json`
    - _Exigences : 9.3 à 9.5, 11_
  - [ ]* 6.7 Tests unitaires de l'extraction
    - 3 essais sur format invalide, passage vide, entité hors schéma, cache réutilisé, échec définitif journalisé
    - _Exigences : 9, 11_

- [ ] 7. Phase 2 — Entity Resolver
  - [ ] 7.1 Implémentation
    - `normalize_label`, `find_duplicates` (regroupement par type, `rapidfuzz`, `SIMILARITY_THRESHOLD`), `merge` (union des provenances et alias, score max, `inferred` = ET logique), `resolve(entities, relations)` (réécriture des identifiants des relations)
    - Option `ENABLE_ENTITY_RESOLUTION` ; journalisation de chaque fusion
    - _Exigences : 10_
  - [ ]* 7.2 Tests de propriétés
    - Propriété 5 (identifiants déterministes), 6 (fusion de deux entités du même type), 7 (intégrité des relations)
    - _Exigences : 10.2, 10.4, 10.5_
  - [ ]* 7.3 Tests unitaires du resolver
    - Accents, seuil configurable, aucune fusion entre types différents, option désactivée, seuil 1.0
    - _Exigences : 10_

- [ ] 8. Checkpoint Phase 2
  - `pytest tests/phase2_extraction/ -v --hypothesis-seed=0`
  - Lancer l'extraction en mode mock sur le corpus et vérifier les fichiers dans `/data/extracted/`
  - Faire un essai avec un vrai LLM sur 2 ou 3 documents et inspecter les entités, les `evidence` et le marquage `inferred`
  - Demander à l'utilisateur de valider le schéma et les modèles

- [ ] 9. Phase 3 — Spark ETL
  - [ ] 9.1 Session Spark et validation
    - `spark_session.py` (`SPARK_MASTER_URL` ou `local[*]`)
    - `validator.py` : validation contre le Graph_Schema, isolation dans `/data/errors/{run_id}/` (`document_id`, `entity_id`, `violation`, `raw_data`, `timestamp`)
    - _Exigences : 12.1 à 12.3, 12.7_
  - [ ] 9.2 Déduplication et transformation
    - `deduplicator.py` : regroupement par `id`, union des provenances, score max, `inferred` = ET logique
    - `transformer.py` : nœuds, relations et mentions au format Neo4j ; écriture dans `/data/curated/{run_id}/`
    - `job.py` : point d'entrée `spark-submit`
    - _Exigences : 12.4 à 12.6_
  - [ ] 9.3 Chargement Neo4j
    - `neo4j_loader.py` : `MERGE` par lots (`UNWIND`) avec labels et types validés par liste blanche
    - Création des nœuds `Document` depuis les métadonnées du Crawler, relations `MENTIONS` (`passage_id`, `char_offset`, `confidence_score`)
    - `MERGE` de relations sans écrasement de la provenance : union de `evidence` et `source_docs`, score max, `inferred` = ET logique
    - `reset_graph()` pour les expériences ; `Neo4jLoadError` avec contexte
    - _Exigences : 13_
  - [ ]* 9.4 Test de propriété 8 et tests unitaires
    - Nœuds conformes au schéma ; violation isolée dans `/data/errors/` ; dédup multi-documents ; provenance préservée
    - _Exigences : 12, 13.7_
  - [ ]* 9.5 Tests d'intégration Neo4j (testcontainers)
    - Propriété 12 : charger deux fois les mêmes données ne change ni le nombre de nœuds ni celui de relations
    - Les relations `MENTIONS` pointent vers les `Document` ; contraintes et index présents
    - _Exigences : 13.3, 13.6, 28.3_

- [ ] 10. Checkpoint Phase 3
  - `make extract && make etl` en mode mock : vérifier le graphe dans Neo4j Browser (7474) : types de nœuds, `MENTIONS`, absence de doublons
  - `pytest tests/phase3_etl/ -v`
  - Demander à l'utilisateur de valider le graphe

- [ ] 11. Embeddings et index vectoriels
  - `src/embeddings/embedder.py` : `Embedder` abstrait, `SentenceTransformerEmbedder` (modèle multilingue, `EMBEDDING_DIM`), `MockEmbedder` déterministe (`MOCK_EMBEDDINGS`)
  - `node_embedder.py` : texte = libellé + alias + description, stockage dans `n.embedding`
  - `vector_index.py` : un index vectoriel par type de nœud ; recréation des index si le modèle ou la dimension change
  - _Exigences : 14_
  - [ ]* Tests : mock déterministe (propriété 9), création des index, requête `db.index.vector.queryNodes`
  - _Exigences : 14, 28_

- [ ] 12. Phase 4 — Graph Analytics
  - [ ] 12.1 Requêtes Cypher
    - `GraphAnalyticsModule` : `get_neighborhood`, `find_paths` (résultat vide si aucun chemin), `multi_hop_query`, `aggregate`, `run_reference_query`
    - Validation des paramètres (profondeur bornée, types de relations en liste blanche) ; résultats avec `confidence_score`, `inferred` et documents sources via `MENTIONS`
    - _Exigences : 15_
  - [ ] 12.2 Algorithmes GDS
    - `_get_or_create_projection` avec poids `confidence_score`
    - PageRank, Louvain, betweenness, Dijkstra (coût `1 - confidence_score`), similarité de nœuds
    - Journalisation de l'algorithme, des paramètres et du temps ; résultats calculés étiquetés `computed`
    - _Exigences : 16_
  - [ ]* 12.3 Tests Phase 4
    - Voisinage de profondeur 0, chemin introuvable, marquage `inferred` et `computed`, chaînage d'algorithmes
    - _Exigences : 15, 16_

- [ ] 13. Phase 5 — GraphRAG
  - [ ] 13.1 Entity linking et récupération
    - `entity_linker.py` (libellé, alias, similarité vectorielle)
    - `retriever.py` : modes `vector`, `neighborhood`, `text2cypher`, `hybrid` (`RETRIEVAL_MODE`), limitation `MAX_CONTEXT_NODES`, collecte de la provenance
    - `cypher_guard.py` : rejet des clauses d'écriture et des procédures hors liste blanche ; exécution via `execute_read` ; schéma injecté dans le prompt Text2Cypher
    - _Exigences : 17_
  - [ ]* 13.2 Test de propriété 10
    - Toute requête avec clause d'écriture est rejetée ; une requête de lecture valide est acceptée
    - _Exigences : 17.6_
  - [ ] 13.3 Contexte, génération et service
    - `context_builder.py`, `response_generator.py` (réponse uniquement à partir du contexte, citations, marquage des éléments inférés), `models.py` (`Citation`, `GraphRAGResponse`), `service.py`
    - Contexte vide → `is_partial=True` sans invention ; journalisation question, requête, contexte, tokens, latence
    - _Exigences : 18_
  - [ ]* 13.4 Tests Phase 5
    - Réponse partielle sur contexte vide, citations présentes et valides, marquage inféré, journalisation, comportement de chaque mode de récupération
    - _Exigences : 17, 18_

- [ ] 14. Checkpoint Phase 5
  - `pytest tests/phase5_graphrag/ -v --hypothesis-seed=0`
  - Poser 5 questions réelles (dont 2 multi-sauts et 2 sémantiques) avec un vrai LLM et vérifier réponses, citations et marquage inféré
  - Demander à l'utilisateur de valider avant l'évaluation

- [ ] 15. Phase 6 — Évaluation comparative
  - [ ] 15.1 Vérité terrain
    - `data/ground_truth.json` : ≥ 20 questions (≥ 5 de chaque type : `multi_hop`, `semantic`, `neighborhood`, `aggregation`) avec `id`, `text`, `type`, `expected_entities`, `expected_answer_contains`, `cypher_query`, `notes`
    - `data/extraction_gold.json` : entités et relations attendues par document
    - `scripts/check_ground_truth.py` : cohérence des entités attendues et validité syntaxique de chaque `cypher_query`
    - _Exigences : 19_
  - [ ] 15.2 Modèles et métriques
    - `EvaluationResult`, `BenchmarkReport` ; précision et rappel sur ensembles d'entités ; latence (moyenne, médiane, min, max, écart-type) ; coût avec `LLM_PRICE_*`
    - Explicabilité : citations présentes et valides, marquage inféré correct, traçabilité vers HDFS
    - Qualité d'extraction (précision, rappel, F1 par type) ; qualité du graphe (doublons restants, nœuds orphelins) ; juge LLM optionnel (`JUDGE_ENABLED`)
    - _Exigences : 20_
  - [ ] 15.3 Évaluateur, expériences et rapport
    - `evaluator.py`, `experiments.py` : E1 (extraction), E2 (résolution d'entités activée/désactivée par rejeu de l'ETL depuis `/data/extracted/` avec `reset_graph()`), E3 (Analytics vs GraphRAG), E4 (modes de récupération)
    - Rapport Markdown : tableaux comparatifs, section par question de recherche (QR1 à QR5), configuration enregistrée ; résultats étiquetés « non significatifs » si `MOCK_LLM=true`
    - `make benchmark`
    - _Exigences : 21_
  - [ ]* 15.4 Tests Phase 6
    - Précision 1.0 sur résultat parfait, rappel 0.0 sans bonne réponse, statistiques de latence, rapport avec les 5 sections, détection d'un Ground Truth incohérent
    - _Exigences : 19, 20, 21_

- [ ] 16. Checkpoint Phase 6
  - Exécuter le benchmark avec un vrai LLM (ou Ollama) et vérifier le rapport
  - Demander à l'utilisateur de valider les résultats et les conclusions

- [ ] 17. Phase 7 — API, interface, monitoring et contrôle d'accès
  - [ ] 17.1 Authentification
    - `src/api/auth.py` : `Role`, JWT (secret `JWT_SECRET`, `JWT_EXPIRE_MINUTES`), bcrypt, compte initial `ADMIN_USERNAME`/`ADMIN_PASSWORD`, `require_role` ; HTTP 401 / 403
    - _Exigences : 23_
  - [ ] 17.2 Endpoints FastAPI
    - `POST /auth/login`, `POST /ingest`, `POST /extract`, `GET /analytics/neighborhood/{node_id}`, `GET /analytics/paths`, `POST /analytics/gds/{algorithm}`, `POST /graphrag/ask`, `POST /evaluate`, `GET /schema`, `GET /health`
    - Validation Pydantic (HTTP 422), documentation OpenAPI
    - _Exigences : 22_
  - [ ]* 17.3 Tests API
    - Propriété 11 (round-trip des réponses), 401 / 403, 422, `/health` public, `/ingest` interdit à `user`
    - _Exigences : 22, 23_
  - [ ] 17.4 Interface Streamlit
    - Pages Graphe (`pyvis` ou `streamlit-agraph`, provenance, éléments inférés distincts), Questions, Analytics, Évaluation
    - _Exigences : 24_
  - [ ] 17.5 Monitoring
    - Logs JSON, métriques (documents ingérés, nœuds par type, latence et tokens LLM, latence GraphRAG), `/health` avec l'état de Neo4j, HDFS, Spark et LLM
    - _Exigences : 25_

- [ ] 18. Infrastructure complète et documentation
  - [ ] 18.1 Compléter `docker-compose.yml`
    - Ajouter `llm-extraction` (:8001, exécute `spark-submit`), `graphrag-service` (:8002), `fastapi` (:8000), `streamlit` (:8501) ; `healthcheck` et `depends_on` ; réseau `graphmind`
    - _Exigences : 27.1 à 27.4_
  - [ ] 18.2 Makefile et documentation
    - Cibles `make up`, `ingest`, `extract`, `etl`, `benchmark`, `test-phase1` à `test-phase7`, `test-all`
    - `README.md` : installation, lancement, schéma Mermaid, Graph_Schema, décisions techniques, limites connues, politique de données
    - `docs/data_retention_policy.md` et commande de purge
    - _Exigences : 26.3, 27.5, 27.8_
  - [ ]* 18.3 Test d'intégration de bout en bout
    - Pipeline complet en mode mock : ingestion → extraction → ETL → analytics → GraphRAG → évaluation
    - _Exigences : 28.2_

- [ ] 19. Checkpoint final
  - `pytest tests/ -v --hypothesis-seed=0`
  - `make up` démarre tous les services sans erreur ; le benchmark génère un rapport répondant aux 5 questions de recherche
  - Demander à l'utilisateur de valider la plateforme complète

---

## Notes

- Ordre de dépendance : 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19. Au sein d'une tâche, les sous-tâches s'exécutent dans l'ordre.
- Le Docker Compose minimal (tâche 3) précède tout code qui a besoin de HDFS, Spark ou Neo4j.
- Les propriétés 1 à 12 sont définies dans `design.md` ; chaque test de propriété utilise Hypothesis avec 100 exemples minimum et n'utilise pas de fixture à portée fonction dans `@given`.
- Les résultats du benchmark ne sont significatifs qu'avec un vrai LLM ; le mode mock sert aux tests de logique.
- Toutes les données sont synthétiques ; aucune donnée personnelle réelle n'est collectée.
