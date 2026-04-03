CREATE_CHUNK_CONSTRAINT_QUERY = """
CREATE CONSTRAINT unique_chunk IF NOT EXISTS 
FOR (c:Chunk) REQUIRE c.chunkId IS UNIQUE
"""

CREATE_CHUNKS_BATCH_QUERY = """
UNWIND $batch AS chunkParam
MERGE (c:Chunk {chunkId: chunkParam.chunkId})
ON CREATE SET 
    c.names = chunkParam.names,
    c.formId = chunkParam.formId,
    c.cik = chunkParam.cik,
    c.cusip6 = chunkParam.cusip6,
    c.source = chunkParam.source,
    c.item = chunkParam.item,
    c.chunkSeqId = chunkParam.chunkSeqId,
    c.text = chunkParam.text
"""