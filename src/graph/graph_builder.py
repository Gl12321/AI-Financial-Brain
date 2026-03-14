import pandas as pd
import json
from src.core.config import get_settings
from src.core.logger import setup_logger
from src.infrastructure.db.falkordb_client import falkor_client

logger = setup_logger("FALKOR_INGESTOR")
settings = get_settings()


class FalkorGraphBuilder:
    def __init__(self, client, batch_size=1000):
        self.client = client
        self.batch_size = batch_size
        self.graph_name = "movies_knowledge_graph"

    def db_cleanup(self):
        logger.info("Cleaning up database")
        graph = self.client.get_graph(self.graph_name)
        graph.query("MATCH (n) DETACH DELETE n")
        logger.info("Database cleanup done.")

    def _execute_batch(self, query, data_list):
        graph = self.client.get_graph(self.graph_name)
        for i in range(0, len(data_list), self.batch_size):
            batch = data_list[i: i + self.batch_size]
            try:
                graph.query(query, {'batch': batch})
            except Exception as e:
                logger.error(f"Batch execution failed: {e}")

    def load_movies(self, metadata_file, embeddings_file, limit=12000):
        logger.info("Loading and merging movie data with embeddings")

        movies_df = pd.read_csv(
            settings.DATA_RAW_DIR / metadata_file,
            dtype={'tmdbId': str}
        ).head(limit)

        embeddings_df = pd.read_csv(
            settings.DATA_RAW_DIR / embeddings_file,
            dtype={'tmdbId': str}
        )

        df = pd.merge(movies_df, embeddings_df, on="tmdbId", how="inner")

        df['embedding'] = df['embedding'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
        df = df.fillna("None")

        records = df.to_dict(orient='records')
        query = """
        UNWIND $batch AS row
        MERGE (m:Movie {tmdbId: toInteger(row.tmdbId)})
        SET m.title = row.title,
            m.original_title = row.original_title,
            m.overview = row.overview,
            m.release_date = row.release_date,
            m.embedding = row.embedding,
            m.budget = toInteger(row.budget),
            m.revenue = toInteger(row.revenue),
            m.runtime = toFloat(row.runtime)
        """
        self._execute_batch(query, records)
        logger.info(f"Loaded {len(records)} movies with embeddings.")
        return len(records[0]['embedding']) if records else 1536

    def load_genres(self, filename):
        df = pd.read_csv(settings.DATA_RAW_DIR / filename).fillna("None")
        records = df.to_dict(orient='records')
        query = """
        UNWIND $batch AS row
        MATCH (m:Movie {tmdbId: toInteger(row.tmdbId)})
        MERGE (g:Genre {genre_id: toInteger(row.genre_id)})
        SET g.genre_name = row.genre_name
        MERGE (m)-[:HAS_GENRE]->(g)
        """
        self._execute_batch(query, records)
        logger.info(f"Loaded genres and relationships.")

    def load_cast(self, filename):
        df = pd.read_csv(settings.DATA_RAW_DIR / filename).fillna("None")
        records = df.to_dict(orient='records')
        query = """
        UNWIND $batch AS row
        MATCH (m:Movie {tmdbId: toInteger(row.tmdbId)})
        MERGE (p:Person {actor_id: toInteger(row.actor_id)})
        SET p.name = row.name, p:Actor
        MERGE (p)-[a:ACTED_IN]->(m)
        SET a.character = row.character
        """
        self._execute_batch(query, records)
        logger.info(f"Loaded cast relationships.")

    def load_crew(self, filename):
        df = pd.read_csv(settings.DATA_RAW_DIR / filename).fillna("None")
        records = df.to_dict(orient='records')
        for job, rel in [("Director", "DIRECTED"), ("Producer", "PRODUCED")]:
            job_records = [r for r in records if r['job'] == job]
            query = f"""
            UNWIND $batch AS row
            MATCH (m:Movie {{tmdbId: toInteger(row.tmdbId)}})
            MERGE (p:Person {{crew_id: toInteger(row.crew_id)}})
            SET p.name = row.name, p:{job}
            MERGE (p)-[:{rel}]->(m)
            """
            self._execute_batch(query, job_records)
        logger.info(f"Loaded crew relationships (Directors/Producers).")

    def create_vector_index(self, dimension):
        graph = self.client.get_graph(self.graph_name)
        try:
            graph.query(f"CALL db.idx.vector.createNodeIndex('Movie', 'embedding', {dimension}, 'L2')")
            logger.info(f"Vector index created with dimension: {dimension}")
        except Exception as e:
            logger.warning(f"Vector index error: {e}")


def main():
    falkor_client.connect()
    builder = FalkorGraphBuilder(falkor_client)

    dim = builder.load_movies('normalized_movies.csv', 'movie_embeddings.csv')

    builder.load_genres('normalized_genres.csv')
    builder.load_cast('normalized_cast.csv')
    builder.load_crew('normalized_crew.csv')

    builder.create_vector_index(dimension=dim)

    falkor_client.close()


if __name__ == "__main__":
    main()