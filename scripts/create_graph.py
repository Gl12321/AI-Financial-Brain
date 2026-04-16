import asyncio

from src.data_pipline.repositories.delivery_repository import DeliveryRepository
from src.graph.builder import GraphBuilder
from src.infrastructure.db.neo4j.neo4j_client import neo4j_client
from src.core.config import get_settings
from src.core.logger import setup_logger

logger = setup_logger("CREATE_GRAPH_NODES")

settings = get_settings()

async def remove_relationships():
    await neo4j_client.connect()
    try:
        builder = GraphBuilder(None, neo4j_client)
        await builder.delete_all_relationships()
    finally:
        await neo4j_client.close()

async def remove_graph():
    await neo4j_client.connect()
    builder = GraphBuilder(None, neo4j_client)
    await builder.delete_all_nodes()
    await neo4j_client.close()

async def create_nodes():
    reader_repository = DeliveryRepository()
    await neo4j_client.connect()

    try:
        builder = GraphBuilder(reader_repository, neo4j_client)
        await builder.setup()

        logger.info("Starting node creation")
        await builder.create_form_nodes()
        logger.info("Node creation completed successfully")

    finally:
        await neo4j_client.close()

async def build_relationships():
    reader_repository = DeliveryRepository()
    await neo4j_client.connect()

    try:
        builder = GraphBuilder(reader_repository, neo4j_client)

        logger.info("Starting relationship building")
        await builder.build_all_relationships()
        logger.info("Relationship building completed successfully")

    finally:
        await neo4j_client.close()

async def index_embeddings():
    await neo4j_client.connect()

    try:
        builder = GraphBuilder(None, neo4j_client)

        logger.info("Starting embedding indexing")
        await builder.index_all_nodes()
        logger.info("Embedding indexing completed successfully")

    finally:
        await neo4j_client.close()

async def main():
    # await remove_graph()
    # await create_nodes()
    # await build_relationships()
    # await remove_relationships()
    await index_embeddings()

if __name__ == "__main__":
    asyncio.run(main())
