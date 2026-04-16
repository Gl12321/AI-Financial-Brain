from neomodel import adb
from src.core.logger import setup_logger
from src.infrastructure.db.neo4j.models import Chunk, Form, Section, Company, Manager
from src.core.config import get_settings

settings = get_settings()
logger = setup_logger("GRAPH_BUILDER")

BATCH_SIZE = 1000


class GraphBuilder:
    def __init__(self, reader_repository, neo4j_client):
        self.repo = reader_repository
        self.neo4j = neo4j_client

    async def setup(self):
        await adb.set_connection(settings.neo4j_url_async)

    async def delete_all_nodes(self):
        async with await self.neo4j.get_session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("Deleted all nodes")

    async def delete_all_relationships(self):
        async with await self.neo4j.get_session() as session:
            await session.run("MATCH ()-[r]->() DELETE r")
        logger.info("Deleted all relationships")

    async def create_chunk_nodes(self):
        offset = 0
        total = 0

        while True:
            chunks = await self.repo.get_chunks_for_graph(limit=BATCH_SIZE, offset=offset)
            if not chunks:
                break

            for chunk_data in chunks:
                try:
                    await Chunk.nodes.get(chunk_id=chunk_data["chunk_id"])
                except Chunk.DoesNotExist:
                    await Chunk(
                        chunk_id=chunk_data["chunk_id"],
                        form_id=chunk_data["form_id"],
                        item=chunk_data["item"],
                        sequence=chunk_data["sequence"],
                        cik=chunk_data["cik"],
                        cusip6=chunk_data["cusip6"],
                        text=chunk_data["text"],
                        names=chunk_data.get("names"),
                        text_embedding=chunk_data["text_embedding"]
                    ).save()

            total += len(chunks)
            offset += BATCH_SIZE

        logger.info(f"Created/Updated {total} Chunk nodes")

    async def create_form_nodes(self):
        offset = 0
        total = 0

        while True:
            forms = await self.repo.get_forms_for_graph(limit=BATCH_SIZE, offset=offset)
            embeddings = await self.repo.get_form_embeddings_for_graph(limit=BATCH_SIZE, offset=offset)
            if not forms:
                break

            for form_data in forms:
                form_embedding = embeddings.get(form_data["form_id"])
                try:
                    existing = await Form.nodes.get(form_id=form_data["form_id"])
                    if form_embedding and not existing.text_embedding:
                        existing.text_embedding = form_embedding
                        await existing.save()
                except Form.DoesNotExist:
                    await Form(
                        form_id=form_data["form_id"],
                        cik=form_data["cik"],
                        cusip6=form_data["cusip6"],
                        source=form_data["source"],
                        summary=form_data["summary"],
                        names=form_data["names"],
                        text_embedding=form_embedding
                    ).save()

            total += len(forms)
            offset += BATCH_SIZE

        logger.info(f"Created/Updated {total} Form nodes")

    async def create_section_nodes(self):
        offset = 0
        total = 0

        while True:
            sections = await self.repo.get_sections_for_graph(limit=BATCH_SIZE, offset=offset)
            if not sections:
                break

            for section_data in sections:
                try:
                    await Section.nodes.get(section_id=section_data["section_id"])
                except Section.DoesNotExist:
                    await Section(
                        section_id=section_data["section_id"],
                        item=section_data["item"],
                        name=section_data["name"],
                        form_id=section_data["form_id"],
                        text_embedding=section_data.get("text_embedding")
                    ).save()

            total += len(sections)
            offset += BATCH_SIZE

        logger.info(f"Created/Updated {total} Section nodes")

    async def create_companies_nodes(self):
        offset = 0
        total = 0

        while True:
            companies = await self.repo.get_companies_for_graph(limit=BATCH_SIZE, offset=offset)
            if not companies:
                break

            for company_data in companies:
                try:
                    await Company.nodes.get(cik=company_data["cik"])
                except Company.DoesNotExist:
                    await Company(
                        cik=company_data["cik"],
                        name=company_data["name"],
                        cusip6=company_data["cusip6"],
                        names=company_data.get("names")
                    ).save()

            total += len(companies)
            offset += BATCH_SIZE

        logger.info(f"Created/Updated {total} Company nodes")

    async def create_managers_nodes(self):
        offset = 0
        total = 0

        while True:
            managers = await self.repo.get_managers_for_graph(limit=BATCH_SIZE, offset=offset)
            if not managers:
                break

            for manager_data in managers:
                try:
                    await Manager.nodes.get(manager_cik=manager_data["manager_cik"])
                except Manager.DoesNotExist:
                    await Manager(
                        manager_cik=manager_data["manager_cik"],
                        name=manager_data["name"],
                        address=manager_data["address"]
                    ).save()

            total += len(managers)
            offset += BATCH_SIZE

        logger.info(f"Created/Updated {total} Manager nodes")

    async def create_all_nodes(self):
        await self.create_form_nodes()
        await self.create_section_nodes()
        await self.create_chunk_nodes()
        await self.create_companies_nodes()
        await self.create_managers_nodes()


    async def build_form_company_topology(self):
        async with await self.neo4j.get_session() as session:
            result = await session.run("""
                MATCH (c:Company), (f:Form)
                WHERE c.cik = f.cik
                MERGE (c)-[:SUBMITTED]->(f)
            """)
            summary = await result.consume()
            logger.info(f"Created {summary.counters.relationships_created} Company-Form relationships")

    async def build_form_section_topology(self):
        async with await self.neo4j.get_session() as session:
            result = await session.run("""
                MATCH (f:Form), (s:Section)
                WHERE s.form_id = f.form_id
                MERGE (f)-[:CONTAINS]->(s)
            """)
            summary = await result.consume()
            logger.info(f"Created {summary.counters.relationships_created} Form-Section relationships")

    async def build_section_chunk_topology(self):
        async with await self.neo4j.get_session() as session:
            result = await session.run("""
                MATCH (s:Section), (ch:Chunk)
                WHERE ch.form_id = s.form_id AND ch.item = s.item AND ch.sequence = 0
                MERGE (s)-[:STARTS_WITH]->(ch)
            """)
            summary1 = await result.consume()
            result = await session.run("""
                MATCH (ch:Chunk), (f:Form)
                WHERE ch.form_id = f.form_id
                MERGE (ch)-[:BELONGS_TO]->(f)
            """)
            summary2 = await result.consume()
            result = await session.run("""
                MATCH (ch1:Chunk), (ch2:Chunk)
                WHERE ch1.form_id = ch2.form_id AND ch1.item = ch2.item AND ch2.sequence = ch1.sequence + 1
                MERGE (ch1)-[:NEXT]->(ch2)
            """)
            summary3 = await result.consume()
            total = summary1.counters.relationships_created + summary2.counters.relationships_created + summary3.counters.relationships_created
            logger.info(f"Created {total} chunk relationships")

    async def build_manager_company_topology(self):
        offset = 0
        total = 0
        while True:
            holdings = await self.repo.get_holdings_for_graph(limit=BATCH_SIZE, offset=offset)
            if not holdings:
                break
            for holding in holdings:
                async with await self.neo4j.get_session() as session:
                    await session.run("""
                        MATCH (m:Manager {manager_cik: $manager_cik}), (c:Company {cusip6: $cusip6})
                        MERGE (m)-[r:INVESTED_IN]->(c)
                        ON CREATE SET r.values = $values, r.shares = $shares, r.dates = $dates, r.cusips = $cusips
                        ON MATCH SET r.values = $values, r.shares = $shares, r.dates = $dates, r.cusips = $cusips
                    """, {
                        "manager_cik": holding["manager_cik"],
                        "cusip6": holding["cusip6"],
                        "values": holding["values"],
                        "shares": holding["shares"],
                        "dates": holding["dates"],
                        "cusips": holding["cusips"]
                    })
                    total += 1
            offset += BATCH_SIZE
        logger.info(f"Created {total} Manager-Company investment relationships")

    async def build_all_relationships(self):
        await self.build_form_company_topology()
        await self.build_form_section_topology()
        await self.build_section_chunk_topology()
        await self.build_manager_company_topology()


    async def index_form_nodes(self):
        async with await self.neo4j.get_session() as session:
            await session.run("""
                CREATE VECTOR INDEX form_embedding_index IF NOT EXISTS
                FOR (f:Form) ON (f.text_embedding)
                OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}
            """, {"dim": settings.MODELS["embedder"]["dimension"]})
        logger.info("Created vector index for Form embeddings")

    async def index_chunks_nodes(self):
        async with await self.neo4j.get_session() as session:
            await session.run("""
                CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
                FOR (c:Chunk) ON (c.text_embedding)
                OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}
            """, {"dim": settings.MODELS["embedder"]["dimension"]})
        logger.info("Created vector index for Chunk embeddings")

    async def index_section_nodes(self):
        async with await self.neo4j.get_session() as session:
            await session.run("""
                CREATE VECTOR INDEX section_embedding_index IF NOT EXISTS
                FOR (s:Section) ON (s.text_embedding)
                OPTIONS {indexConfig: {`vector.dimensions`: $dim, `vector.similarity_function`: 'cosine'}}
            """, {"dim": settings.MODELS["embedder"]["dimension"]})
        logger.info("Created vector index for Section embeddings")

    async def index_all_nodes(self):
        await self.index_form_nodes()
        await self.index_chunks_nodes()
        await self.index_section_nodes()


    async def final_build(self):
        await self.create_all_nodes()
        await self.build_all_relationships()
        await self.index_all_nodes()