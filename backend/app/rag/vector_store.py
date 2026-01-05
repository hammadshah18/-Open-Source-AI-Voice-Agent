"""
Vector Store for Retrieval-Augmented Generation (RAG)
Uses Sentence Transformers for embeddings and FAISS for similarity search
Fully local and open-source implementation
"""

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from pathlib import Path
import pickle
from typing import List, Dict, Tuple, Optional
from .kb_loader import Document, KnowledgeBaseLoader
from ..logger import logger
from ..config import BASE_DIR

class VectorStore:
    """
    Vector store for semantic search over company knowledge base
    Uses FAISS for efficient similarity search
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        index_path: Optional[Path] = None
    ):
        """
        Initialize vector store with embedding model
        
        Args:
            model_name (str): Sentence Transformer model name
                             'all-MiniLM-L6-v2' is lightweight and fast (384 dimensions)
                             'all-mpnet-base-v2' is more accurate but slower (768 dimensions)
            index_path (Path): Path to save/load FAISS index (optional)
        """
        logger.info(f"Initializing VectorStore with model: {model_name}")
        
        # Load embedding model
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"Embedding model loaded. Dimension: {self.embedding_dim}")
        
        # Initialize FAISS index (using flat L2 distance for accuracy)
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Store documents and their metadata
        self.documents: List[Document] = []
        self.company_id: Optional[str] = None
        
        # Index path for persistence
        self.index_path = index_path or (BASE_DIR / "backend" / "data" / "faiss_index")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
    
    def add_documents(self, documents: List[Document], company_id: str):
        """
        Add documents to the vector store
        
        Args:
            documents (List[Document]): Documents to add
            company_id (str): Company identifier for these documents
        """
        if not documents:
            logger.warning("No documents to add to vector store")
            return
        
        logger.info(f"Adding {len(documents)} documents to vector store for {company_id}")
        
        # Extract text content
        texts = [doc.content for doc in documents]
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        
        # Add to FAISS index - ensure correct shape
        embedding_array = embeddings.astype('float32')
        if len(embedding_array.shape) == 1:
            embedding_array = embedding_array.reshape(1, -1)
        self.index.add(embedding_array)  # type: ignore
        
        # Store documents
        self.documents.extend(documents)
        self.company_id = company_id
        
        logger.info(f"Added {len(documents)} documents. Total in index: {self.index.ntotal}")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Document, float]]:
        """
        Search for most relevant documents
        
        Args:
            query (str): Search query
            top_k (int): Number of top results to return
            score_threshold (float): Minimum similarity score (optional)
            
        Returns:
            List[Tuple[Document, float]]: List of (document, distance) tuples
                                         Lower distance = more similar
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty. No documents to search.")
            return []
        
        logger.info(f"Searching for: {query[:100]}...")
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        
        # Search in FAISS index (reshape to 2D array for FAISS)
        query_vec = query_embedding.astype('float32').reshape(1, -1)
        distances, indices = self.index.search(query_vec, top_k)  # type: ignore
        
        # Prepare results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx]
                
                # Filter by score threshold if provided
                if score_threshold is None or distance <= score_threshold:
                    results.append((doc, float(distance)))
        
        logger.info(f"Found {len(results)} relevant documents")
        
        return results
    
    def get_relevant_context(
        self, 
        query: str, 
        top_k: int = 3,
        max_context_length: int = 2000
    ) -> str:
        """
        Get concatenated context from top relevant documents
        Useful for RAG prompting
        
        Args:
            query (str): User query
            top_k (int): Number of documents to retrieve
            max_context_length (int): Maximum total characters in context
            
        Returns:
            str: Concatenated context from relevant documents
        """
        results = self.search(query, top_k=top_k)
        
        if not results:
            return ""
        
        # Build context from results
        context_parts = []
        total_length = 0
        
        for doc, distance in results:
            content = doc.content
            
            # Check if adding this document exceeds max length
            if total_length + len(content) > max_context_length:
                # Add truncated version
                remaining = max_context_length - total_length
                if remaining > 100:  # Only add if reasonable amount of text
                    context_parts.append(content[:remaining] + "...")
                break
            
            context_parts.append(content)
            total_length += len(content)
            
            # Add source information
            source = doc.metadata.get('source_file', 'unknown')
            context_parts.append(f"\n[Source: {source}]\n")
        
        context = "\n\n".join(context_parts)
        
        logger.info(f"Retrieved context: {len(context)} characters from {len(results)} documents")
        
        return context
    
    def save_index(self, path: Optional[Path] = None):
        """
        Save FAISS index and documents to disk
        
        Args:
            path (Path): Directory to save index (optional)
        """
        save_path = path or self.index_path
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        index_file = save_path / f"{self.company_id}_index.faiss"
        faiss.write_index(self.index, str(index_file))
        
        # Save documents and metadata
        docs_file = save_path / f"{self.company_id}_documents.pkl"
        with open(docs_file, 'wb') as f:
            pickle.dump(self.documents, f)
        
        logger.info(f"Index saved to {save_path}")
    
    def load_index(self, company_id: str, path: Optional[Path] = None) -> bool:
        """
        Load FAISS index and documents from disk
        
        Args:
            company_id (str): Company identifier
            path (Path): Directory to load from (optional)
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        load_path = path or self.index_path
        
        index_file = load_path / f"{company_id}_index.faiss"
        docs_file = load_path / f"{company_id}_documents.pkl"
        
        if not index_file.exists() or not docs_file.exists():
            logger.warning(f"Index files not found for {company_id}")
            return False
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            
            # Load documents
            with open(docs_file, 'rb') as f:
                self.documents = pickle.load(f)
            
            self.company_id = company_id
            
            logger.info(f"Index loaded for {company_id}: {self.index.ntotal} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            return False
    
    def clear(self):
        """
        Clear the vector store
        """
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.documents = []
        self.company_id = None
        logger.info("Vector store cleared")
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the vector store
        
        Returns:
            Dict: Statistics including document count, company, etc.
        """
        return {
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal,
            "company_id": self.company_id,
            "embedding_dimension": self.embedding_dim
        }


class RAGSystem:
    """
    Complete RAG system integrating knowledge base loading and vector search
    """
    
    def __init__(
        self, 
        companies_dir: Path,
        model_name: str = "all-MiniLM-L6-v2",
        auto_load: bool = False
    ):
        """
        Initialize RAG system
        
        Args:
            companies_dir (Path): Path to companies directory
            model_name (str): Sentence Transformer model name
            auto_load (bool): Automatically load index if available
        """
        self.kb_loader = KnowledgeBaseLoader(companies_dir)
        self.vector_store = VectorStore(model_name=model_name)
        self.current_company = None
        
        logger.info("RAG System initialized")
        
        if auto_load:
            logger.info("Auto-load enabled, checking for existing indexes...")
    
    def load_company(self, company_id: str, force_rebuild: bool = False):
        """
        Load or rebuild index for a specific company
        
        Args:
            company_id (str): Company identifier
            force_rebuild (bool): Force rebuild even if index exists
        """
        logger.info(f"Loading RAG for company: {company_id}")
        
        # Try to load existing index first
        if not force_rebuild and self.vector_store.load_index(company_id):
            self.current_company = company_id
            logger.info(f"Loaded existing index for {company_id}")
            return
        
        # Build new index
        logger.info(f"Building new index for {company_id}")
        
        # Load documents
        documents = self.kb_loader.load_company_knowledge(company_id)
        
        if not documents:
            logger.warning(f"No documents found for {company_id}")
            return
        
        # Clear and rebuild vector store
        self.vector_store.clear()
        self.vector_store.add_documents(documents, company_id)
        
        # Save index
        self.vector_store.save_index()
        
        self.current_company = company_id
        logger.info(f"RAG system ready for {company_id}")
    
    def retrieve(self, query: str, top_k: int = 3) -> str:
        """
        Retrieve relevant context for a query
        
        Args:
            query (str): User query
            top_k (int): Number of documents to retrieve
            
        Returns:
            str: Retrieved context
        """
        if self.current_company is None:
            logger.warning("No company loaded in RAG system")
            return ""
        
        return self.vector_store.get_relevant_context(query, top_k=top_k)
    
    def switch_company(self, company_id: str):
        """
        Switch to a different company's knowledge base
        
        Args:
            company_id (str): Company identifier
        """
        if company_id == self.current_company:
            logger.info(f"Already using {company_id}")
            return
        
        self.load_company(company_id)
