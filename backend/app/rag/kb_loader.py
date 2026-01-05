"""
Knowledge Base Loader
Loads and parses company-specific knowledge from various file formats
Supports: .txt, .md, .json files
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from ..logger import logger

class Document:
    """
    Represents a single document chunk with metadata
    """
    def __init__(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.content = content
        self.metadata = metadata or {}
    
    def __repr__(self):
        return f"Document(content={self.content[:50]}..., metadata={self.metadata})"


class KnowledgeBaseLoader:
    """
    Loads knowledge base documents from company directories
    """
    
    def __init__(self, companies_dir: Path):
        """
        Initialize loader with path to companies directory
        
        Args:
            companies_dir (Path): Path to companies/ directory
        """
        self.companies_dir = Path(companies_dir)
        if not self.companies_dir.exists():
            raise FileNotFoundError(f"Companies directory not found: {companies_dir}")
        
        logger.info(f"Initialized KnowledgeBaseLoader with directory: {companies_dir}")
    
    def load_company_knowledge(self, company_id: str) -> List[Document]:
        """
        Load all knowledge documents for a specific company
        
        Args:
            company_id (str): Company identifier (e.g., 'healthplus', 'techstore')
            
        Returns:
            List[Document]: List of document objects with content and metadata
        """
        company_path = self.companies_dir / company_id
        
        if not company_path.exists():
            logger.warning(f"Company directory not found: {company_path}")
            return []
        
        logger.info(f"Loading knowledge base for company: {company_id}")
        
        documents = []
        
        # Load all supported file types
        for file_path in company_path.rglob('*'):
            if file_path.is_file():
                try:
                    if file_path.suffix == '.json':
                        docs = self._load_json(file_path, company_id)
                    elif file_path.suffix in ['.txt', '.md']:
                        docs = self._load_text(file_path, company_id)
                    else:
                        continue  # Skip unsupported file types
                    
                    documents.extend(docs)
                    logger.info(f"Loaded {len(docs)} documents from {file_path.name}")
                    
                except Exception as e:
                    logger.error(f"Error loading file {file_path}: {e}")
        
        logger.info(f"Total documents loaded for {company_id}: {len(documents)}")
        return documents
    
    def _load_json(self, file_path: Path, company_id: str) -> List[Document]:
        """
        Load and parse JSON files (FAQs, services, products, etc.)
        
        Args:
            file_path (Path): Path to JSON file
            company_id (str): Company identifier
            
        Returns:
            List[Document]: Parsed documents
        """
        documents = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if 'faqs' in data:
            # FAQ format
            for faq in data['faqs']:
                content = f"Question: {faq.get('question', '')}\nAnswer: {faq.get('answer', '')}"
                metadata = {
                    'company_id': company_id,
                    'source_file': file_path.name,
                    'type': 'faq',
                    'category': faq.get('category', 'general')
                }
                documents.append(Document(content, metadata))
        
        elif 'products' in data:
            # Products format
            for product in data['products']:
                content = f"Product: {product.get('name', '')}\n"
                content += f"Category: {product.get('category', '')}\n"
                content += f"Price: {product.get('price', '')}\n"
                content += f"Description: {product.get('description', '')}"
                
                metadata = {
                    'company_id': company_id,
                    'source_file': file_path.name,
                    'type': 'product',
                    'category': product.get('category', 'general')
                }
                documents.append(Document(content, metadata))
        
        elif 'services' in data:
            # Services format
            for service in data['services']:
                content = f"Service: {service.get('name', '')}\n"
                content += f"Description: {service.get('description', '')}\n"
                if 'price' in service:
                    content += f"Price: {service.get('price', '')}\n"
                
                metadata = {
                    'company_id': company_id,
                    'source_file': file_path.name,
                    'type': 'service',
                    'category': service.get('category', 'general')
                }
                documents.append(Document(content, metadata))
        
        elif 'courses' in data:
            # Courses format (for EduLearn)
            for course in data['courses']:
                content = f"Course: {course.get('title', '')}\n"
                content += f"Description: {course.get('description', '')}\n"
                content += f"Duration: {course.get('duration', '')}\n"
                if 'price' in course:
                    content += f"Price: {course.get('price', '')}"
                
                metadata = {
                    'company_id': company_id,
                    'source_file': file_path.name,
                    'type': 'course',
                    'category': course.get('category', 'general')
                }
                documents.append(Document(content, metadata))
        
        else:
            # Generic JSON - convert entire object to text
            content = json.dumps(data, indent=2)
            metadata = {
                'company_id': company_id,
                'source_file': file_path.name,
                'type': 'generic_json'
            }
            documents.append(Document(content, metadata))
        
        return documents
    
    def _load_text(self, file_path: Path, company_id: str) -> List[Document]:
        """
        Load and parse text/markdown files
        Chunks large documents for better retrieval
        
        Args:
            file_path (Path): Path to text file
            company_id (str): Company identifier
            
        Returns:
            List[Document]: Parsed document chunks
        """
        documents = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by sections (headers, double newlines, etc.)
        chunks = self._chunk_text(content, max_chunk_size=1000, overlap=100)
        
        for idx, chunk in enumerate(chunks):
            metadata = {
                'company_id': company_id,
                'source_file': file_path.name,
                'type': 'text',
                'chunk_index': idx,
                'total_chunks': len(chunks)
            }
            documents.append(Document(chunk, metadata))
        
        return documents
    
    def _chunk_text(self, text: str, max_chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval
        
        Args:
            text (str): Text to chunk
            max_chunk_size (int): Maximum characters per chunk
            overlap (int): Number of overlapping characters between chunks
            
        Returns:
            List[str]: List of text chunks
        """
        # Try to split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds max size, save current chunk
            if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap from end of previous chunk
                current_chunk = current_chunk[-overlap:] if overlap > 0 else ""
            
            current_chunk += para + "\n\n"
        
        # Add remaining content
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # If no chunks created, split by max size
        if not chunks:
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size - overlap)]
        
        return chunks
    
    def get_available_companies(self) -> List[str]:
        """
        Get list of available company IDs
        
        Returns:
            List[str]: List of company directory names
        """
        companies = [
            d.name for d in self.companies_dir.iterdir() 
            if d.is_dir() and not d.name.startswith('.')
        ]
        logger.info(f"Available companies: {companies}")
        return companies
    
    def load_all_companies(self) -> Dict[str, List[Document]]:
        """
        Load knowledge bases for all available companies
        
        Returns:
            Dict[str, List[Document]]: Dictionary mapping company_id to documents
        """
        all_knowledge = {}
        
        for company_id in self.get_available_companies():
            documents = self.load_company_knowledge(company_id)
            all_knowledge[company_id] = documents
        
        logger.info(f"Loaded knowledge for {len(all_knowledge)} companies")
        return all_knowledge
