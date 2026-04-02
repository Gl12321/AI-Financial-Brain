import asyncio
from sqlalchemy import text
from src.infrastructure.db.neo4j_client import neo4j_client
from src.infrastructure.db.postgre_client import postgre_client

async def main():
    await neo4j_client.connect()
    session = postgre_client.get_session()

    result = await neo4j_client._driver.execute_query("RETURN 'Hello from Neo4j' AS message")
    message_n = result.records[0].get('message')
    await neo4j_client.close()

    async with session:
        query = text("SELECT 'Hello from Postgres' AS message")
        result = await session.execute(query)
        message_p = result.scalar()

    print(message_p)
    print(message_n)

if __name__ == "__main__":
    asyncio.run(main())