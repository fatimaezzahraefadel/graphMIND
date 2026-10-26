"""Client WebHDFS pour écriture de documents et métadonnées dans HDFS."""

from __future__ import annotations

import json

import requests as req_lib

from src.shared.exceptions import CrawlerError
from src.shared.logging import get_logger

logger = get_logger("hdfs_writer")


class HDFSWriter:
    """Écrit des fichiers dans HDFS via l'API WebHDFS (REST).

    Le protocole WebHDFS CREATE utilise deux étapes :
    1. PUT sur le NameNode → 307 redirect vers le DataNode.
    2. PUT sur l'URL du DataNode avec le contenu réel.
    """

    def __init__(self, namenode_url: str, user: str = "root") -> None:
        self.base_url = namenode_url.rstrip("/")
        self.user = user

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    def _url(self, path: str, op: str, **params: str) -> str:
        """Construit l'URL WebHDFS avec les paramètres de requête.

        Args:
            path: Chemin HDFS (ex. ``/data/raw/html/abc123``).
            op: Opération WebHDFS (``GETFILESTATUS``, ``CREATE``…).
            **params: Paramètres supplémentaires.

        Returns:
            URL complète.
        """
        all_params = {"user.name": self.user, "op": op, **params}
        qs = "&".join(f"{k}={v}" for k, v in all_params.items())
        return f"{self.base_url}/webhdfs/v1{path}?{qs}"

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def exists(self, hdfs_path: str) -> bool:
        """Vérifie si un fichier existe dans HDFS.

        Utilise GETFILESTATUS : retourne True si le fichier existe (HTTP 200),
        False si absent (HTTP 404), lève CrawlerError sur toute autre erreur.

        Args:
            hdfs_path: Chemin absolu dans HDFS.

        Returns:
            True si le fichier existe, False sinon.

        Raises:
            CrawlerError: Sur toute réponse HTTP inattendue.
        """
        r = req_lib.get(self._url(hdfs_path, "GETFILESTATUS"), timeout=10)
        if r.status_code == 200:
            return True
        if r.status_code == 404:
            return False
        raise CrawlerError(
            f"HDFS GETFILESTATUS failed: {r.status_code}",
            component="hdfs_writer",
            context={"path": hdfs_path, "status_code": r.status_code},
        )

    def write(self, hdfs_path: str, content: bytes, overwrite: bool = False) -> None:
        """Écrit un fichier dans HDFS via WebHDFS CREATE (deux étapes).

        Si ``overwrite=False`` et que le fichier existe déjà, l'opération est
        ignorée (idempotence).

        Args:
            hdfs_path: Chemin de destination dans HDFS.
            content: Contenu binaire à écrire.
            overwrite: Si True, écrase le fichier existant.

        Raises:
            CrawlerError: Si WebHDFS retourne une erreur inattendue.
        """
        if not overwrite and self.exists(hdfs_path):
            logger.info("hdfs_skip_existing", path=hdfs_path)
            return

        # Étape 1 : CREATE → le NameNode répond 307 avec l'URL du DataNode
        r = req_lib.put(
            self._url(hdfs_path, "CREATE", overwrite=str(overwrite).lower()),
            allow_redirects=False,
            timeout=10,
        )
        if r.status_code != 307:
            raise CrawlerError(
                f"HDFS CREATE step1 failed: {r.status_code}",
                component="hdfs_writer",
                context={"path": hdfs_path, "status_code": r.status_code},
            )

        location = r.headers["Location"]

        # Étape 2 : PUT vers l'URL du DataNode avec le contenu réel
        r2 = req_lib.put(location, data=content, timeout=30)
        if r2.status_code not in (200, 201):
            raise CrawlerError(
                f"HDFS CREATE step2 failed: {r2.status_code}",
                component="hdfs_writer",
                context={"path": hdfs_path, "status_code": r2.status_code},
            )

        logger.info("hdfs_written", path=hdfs_path, size=len(content))

    def write_metadata(self, hdfs_path: str, metadata: dict) -> None:
        """Sérialise les métadonnées en JSON et les écrit dans HDFS (overwrite=True).

        Args:
            hdfs_path: Chemin destination (ex. ``/data/raw/html/abc123.meta.json``).
            metadata: Dictionnaire de métadonnées.
        """
        self.write(
            hdfs_path,
            json.dumps(metadata, default=str).encode("utf-8"),
            overwrite=True,
        )
