from falkordb import FalkorDB
from src.core.config import get_settings
from src.core.logger import setup_logger

settings = get_settings()
logger = setup_logger("FALKORDB_CLIENT")

class FalkorDBClient:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FalkorDBClient, cls).__new__(cls)
            cls._client = FalkorDB(
                host=settings.GRAPH_HOST,
                port=settings.GRAPH_PORT
            )
            logger.info("FalkorDB Client instance created (Sync)")
        return cls._instance

    def connect(self):
        self._client.list_graphs()
        logger.info("Successfully connected to FalkorDB server")

    def get_graph(self, graph_name: str = "movies_knowledge_graph"):
        if self._client is None:
            raise RuntimeError("FalkorDB client is not initialized")
        return self._client.select_graph(graph_name)

    def close(self):
        if self._client:
            self._client.close()
            logger.info("FalkorDB connection closed")

falkor_client = FalkorDBClient()