from src.graph import queries
from src.core.logger import setup_logger

logger = setup_logger("GRAPH_BUILDER")


class GraphBuilder:
    def __init__(self, repository, neo4j_client):
        self.repo = repository
        self.neo4j = neo4j_client

    async def create_chunk_nodes(self):
        self.neo4j_client.execute(queries.CREATE_CHUNK_CONSTRAINT_QUERY)

        chunks = await self.repo.get_all_chunks_for_graph()

        logger.info("Start creating chunk nodes")
        batch_size = 1000
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            self.neo4j_client.execute(queries.CREATE_CHUNKS_BATCH_QUERY, batch)
        logger.info(f"{len(chunks)} chunk nodes created")

    def index_chunk_nodes(self):
        self.neo4j.execute(queries.CREATE_CHUNK_VECTOR_INDEX)

        embeddings_data = self.repo.get_embeddings_of_chunks()

        logger.info(f"Write embeddings into each chunks")
        batch_size = 500
        for i in range(0, len(embeddings_data), batch_size):
            batch = embeddings_data[i:i + batch_size]
            self.neo4j.execute(queries.ADD_EMBEDDINGS_TO_CHUNKS, batch=batch)
        logger.info("embeddings written")

    def build_chunks_topology(self):
        logger.info("Starting start chunk topology construction")

        records = self.neo4j.execute(queries.GET_DISTINCT_FORMS_QUERY)
        distinct_form_ids = [r['formId'] for r in records]

        sections = ['item1', 'item1a', 'item7', 'item7a']

        total_links = 0

        for form_id in distinct_form_ids:
            for section_item in sections:
                result = self.neo4j.execute(
                    queries.LINK_SECTION_CHUNKS_QUERY,
                    formIdParam=form_id,
                    itemParam=section_item
                )

                if result and result[0]['size(section_chunk_list)'] > 0:
                    total_links += 1
                    logger.debug(f"Linked {section_item} for form {form_id}")

        logger.info(f"Start chunk topology built. Total sections processed: {total_links}")

    async def create_form_nodes(self):
        self.neo4j.execute(queries.CREATE_FORM_CONSTRAINT_QUERY)

        forms = await self.repo.get_all_forms_for_graph()

        logger.info("Start creating Form nodes")
        for form in forms:
            self.neo4j.execute(queries.MERGE_FORM_NODE_QUERY, formInfo=form)
        logger.info(f"{len(forms)} Form nodes created")

    def index_form_nodes(self):
        self.neo4j.execute(
            queries.CREATE_FORM_VECTOR_INDEX,
            vectorDimensionsParam=vector_dims
        )

        enriched_forms = self.repo.get_enriched_forms_metadata()

        logger.info("Writing summaries and embeddings into Form nodes")
        for form_data in enriched_forms:
            self.neo4j.execute(queries.UPDATE_FORM_SUMMARY_QUERY, formInfo=form_data)
        logger.info("Form embeddings and summaries written")

    def build_form_hierarchy(self):
        logger.info("Connecting Chunks to parent Forms")
        self.neo4j.execute(queries.LINK_CHUNKS_TO_FORM_QUERY)

        logger.info("Connecting Forms to section heads")
        self.neo4j.execute(queries.LINK_FORM_TO_SECTION_HEAD_QUERY)

        logger.info("Form hierarchy and section entry points established")


    def final_build(self):
        self.create_chunk_nodes()
        self.index_chunk_nodes()
        self.build_chunks_topology()

        self.create_form_nodes()
        self.index_form_nodes()
        self.build_form_hierarchy()