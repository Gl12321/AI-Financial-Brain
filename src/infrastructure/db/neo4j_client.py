import asyncio
from neo4j import AsyncGraphDatabase
from src.core.config import get_settings
from src.core.logger import setup_logger

settings = get_settings()
logger = setup_logger("NEO4J_CLIENT")

class Neo4jClient:
    _instance = None
    _driver = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        if self._driver is None:
            uri = f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}"
            self._driver = AsyncGraphDatabase.driver(
                uri,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            await self._driver.verify_connectivity()
            logger.info("Neo4j Async Driver initialized and connected")

    async def get_session(self, database: str = "neo4j"):
        if self._driver is None:
            await self.connect()
        return self._driver.session(database=database)

    async def close(self):
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j Async connection closed")

neo4j_client = Neo4jClient()
