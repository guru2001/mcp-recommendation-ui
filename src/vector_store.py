"""Vector database for storing and searching MCP servers."""
import os
import json
from typing import List, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB
VECTOR_DB_PATH = "./vector_db"
COLLECTION_NAME = "mcp_servers"

# Initialize embedding model (using a lightweight model)
_embedding_model = None


def get_embedding_model():
    """Lazy load the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        # Using a lightweight model that's fast and doesn't require GPU
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def get_vector_db():
    """Get or create the ChromaDB client."""
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(
        path=VECTOR_DB_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    return client


def get_collection():
    """Get or create the collection for MCP servers."""
    client = get_vector_db()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "MCP servers from Glama.ai"}
    )
    return collection


def create_search_text(server: dict) -> str:
    """Create searchable text from server metadata."""
    parts = [
        server.get("name", ""),
        server.get("description", ""),
    ]
    # Add additional metadata if available
    if "command" in server:
        parts.append(server["command"])
    if "type" in server:
        parts.append(f"type: {server['type']}")
    
    return " ".join(filter(None, parts))


async def store_servers(servers: List[dict], batch_size: int = 50):
    """Store MCP servers in the vector database."""
    if not servers:
        return
    
    collection = get_collection()
    model = get_embedding_model()
    
    # Prepare data for batch insertion
    ids = []
    documents = []
    metadatas = []
    
    for server in servers:
        server_id = server.get("name", "").lower().replace(" ", "-")
        if not server_id:
            continue
        
        # Create searchable text
        search_text = create_search_text(server)
        
        # Store metadata (excluding large fields)
        metadata = {
            "name": server.get("name", ""),
            "description": server.get("description", ""),
            "type": server.get("type", "stdio"),
            "source": server.get("source", "glama.ai"),
        }
        
        # Add command or url if available
        if "command" in server:
            metadata["command"] = server["command"]
        if "url" in server:
            metadata["url"] = server["url"]
        
        ids.append(server_id)
        documents.append(search_text)
        metadatas.append(metadata)
    
    # Generate embeddings and store in batches
    for i in range(0, len(documents), batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_docs = documents[i:i + batch_size]
        batch_metas = metadatas[i:i + batch_size]
        
        # Generate embeddings
        embeddings = model.encode(batch_docs, show_progress_bar=False).tolist()
        
        # Upsert to collection (will update if exists)
        collection.upsert(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_docs,
            metadatas=batch_metas
        )


async def search_servers(query: str, n_results: int = 10) -> List[dict]:
    """Search for MCP servers using semantic search."""
    if not query or not query.strip():
        return []
    
    collection = get_collection()
    model = get_embedding_model()
    
    # Generate query embedding
    query_embedding = model.encode([query], show_progress_bar=False).tolist()[0]
    
    # Search the collection
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, 30)  # Limit to 30 max for performance
    )
    
    # Convert results to server dictionaries
    servers = []
    if results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i] if "distances" in results else None
            
            server = {
                "name": metadata.get("name", ""),
                "description": metadata.get("description", ""),
                "type": metadata.get("type", "stdio"),
                "source": metadata.get("source", "glama.ai"),
            }
            
            # Add command or url if available
            if "command" in metadata:
                server["command"] = metadata["command"]
            if "url" in metadata:
                server["url"] = metadata["url"]
            
            # Add similarity score (1 - distance for cosine similarity)
            if distance is not None:
                server["similarity"] = 1 - distance
            
            servers.append(server)
    
    return servers


def get_all_servers() -> List[dict]:
    """Get all servers from the vector database."""
    collection = get_collection()
    results = collection.get()
    
    servers = []
    if results["ids"]:
        for i in range(len(results["ids"])):
            metadata = results["metadatas"][i]
            
            server = {
                "name": metadata.get("name", ""),
                "description": metadata.get("description", ""),
                "type": metadata.get("type", "stdio"),
                "source": metadata.get("source", "glama.ai"),
            }
            
            if "command" in metadata:
                server["command"] = metadata["command"]
            if "url" in metadata:
                server["url"] = metadata["url"]
            
            servers.append(server)
    
    return servers


def clear_vector_db():
    """Clear all servers from the vector database."""
    client = get_vector_db()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

