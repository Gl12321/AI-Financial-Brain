import asyncio

from src.data_pipline.repositories.delivery_repository import DeliveryRepository
from src.graph.builder import GraphBuilder
from src.infrastructure.db.neo4j.neo4j_client import neo4j_client
from src.core.config import get_settings
from src.core.logger import setup_logger

logger = setup_logger("CREATE_GRAPH_NODES")

settings = get_settings()

async def create_nodes():
    reader_repository = DeliveryRepository()
    await neo4j_client.connect()

    try:
        builder = GraphBuilder(reader_repository, neo4j_client)
        await builder.setup()

        logger.info("Starting node creation")
        await builder.create_all_nodes()
        logger.info("Node creation completed successfully")

    finally:
        await neo4j_client.close()


async def main():
    await create_nodes()

if __name__ == "__main__":
    asyncio.run(main())
