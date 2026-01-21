"""
RAG (Retrieval Augmented Generation) Pipeline
Handles PDF processing, embedding, storage, and retrieval with improved context memory
"""
import os
import sys
import logging
from typing import Tuple, List, Optional
import tempfile
import hashlib
import streamlit as st

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config import config

logger = logging.getLogger(__name__)

# Constants - IMPROVED for better retrieval
MAX_FILE_SIZE_MB = 10
CHUNK_SIZE = 1000  # Increased from 500 for more context per chunk
CHUNK_OVERLAP = 200  # Increased overlap for better continuity
TOP_K_RESULTS = 8  # Increased from 3 for more diverse results
MIN_RELEVANCE_SCORE = 0.25  # Lowered from 0.5 to catch more relevant content


class RAGPipeline:
    """RAG Pipeline for PDF-based question answering with improved context memory"""
    
    def __init__(self):
        self._embeddings = None
        self._vector_store = None
        self._persist_directory = os.path.join(tempfile.gettempdir(), "medbook_chroma")
        self._document_summaries = {}  # Store document summaries
    
    @property
    def embeddings(self):
        """Lazy load embeddings model"""
        if self._embeddings is None:
            try:
                self._embeddings = HuggingFaceEmbeddings(
                    model_name="all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                logger.info("Embeddings model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embeddings model: {e}")
                raise
        return self._embeddings
    
    @property
    def vector_store(self) -> Optional[Chroma]:
        """Get or create vector store"""
        if self._vector_store is None:
            try:
                # Try to load existing store
                if os.path.exists(self._persist_directory):
                    self._vector_store = Chroma(
                        persist_directory=self._persist_directory,
                        embedding_function=self.embeddings,
                        collection_name="medbook_docs"
                    )
                    logger.info("Loaded existing vector store")
            except Exception as e:
                logger.warning(f"Could not load existing vector store: {e}")
        return self._vector_store
    
    def get_last_context(self) -> Optional[str]:
        """Get the last retrieved context from session state"""
        return st.session_state.get('last_rag_context', None)
    
    def get_last_sources(self) -> List[str]:
        """Get the last sources from session state"""
        return st.session_state.get('last_rag_sources', [])
    
    def get_document_summary(self, doc_name: str) -> Optional[str]:
        """Get stored summary for a document"""
        if 'document_summaries' not in st.session_state:
            st.session_state.document_summaries = {}
        return st.session_state.document_summaries.get(doc_name)
    
    def store_document_summary(self, doc_name: str, first_chunks: List[str]):
        """Store a summary of the document (first few chunks) for quick reference"""
        if 'document_summaries' not in st.session_state:
            st.session_state.document_summaries = {}
        # Store first 3 chunks as document overview
        summary = "\n\n".join(first_chunks[:3])
        st.session_state.document_summaries[doc_name] = summary
        logger.info(f"Stored summary for {doc_name}")
    
    def validate_pdf(self, uploaded_file) -> Tuple[bool, str]:
        """
        Validate an uploaded PDF file
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            (is_valid, error_message)
        """
        if uploaded_file is None:
            return False, "No file provided"
        
        # Check file type
        if not uploaded_file.name.lower().endswith('.pdf'):
            return False, f"'{uploaded_file.name}' is not a PDF file. Please upload PDF files only."
        
        # Check file size
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return False, f"'{uploaded_file.name}' is too large ({file_size_mb:.1f}MB). Maximum size is {MAX_FILE_SIZE_MB}MB."
        
        if uploaded_file.size == 0:
            return False, f"'{uploaded_file.name}' is empty. Please upload a valid PDF."
        
        # Try to read the PDF to check if it's valid
        try:
            uploaded_file.seek(0)
            reader = PdfReader(uploaded_file)
            if len(reader.pages) == 0:
                return False, f"'{uploaded_file.name}' has no pages. Please upload a valid PDF."
            
            # Check if there's any extractable text
            total_text = ""
            for page in reader.pages[:5]:  # Check first 5 pages
                text = page.extract_text() or ""
                total_text += text
            
            if len(total_text.strip()) < 50:
                return False, f"'{uploaded_file.name}' appears to be empty or contains only images. Please upload a PDF with text content."
            
            uploaded_file.seek(0)
            return True, ""
            
        except Exception as e:
            return False, f"'{uploaded_file.name}' could not be read. It may be corrupted or password-protected. Error: {str(e)}"
    
    def extract_text_from_pdf(self, uploaded_file) -> Tuple[str, int]:
        """
        Extract text from a PDF file
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            (extracted_text, page_count)
        """
        try:
            uploaded_file.seek(0)
            reader = PdfReader(uploaded_file)
            
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(f"[Page {i+1}]\n{page_text}")
            
            return "\n\n".join(text_parts), len(reader.pages)
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def chunk_text(self, text: str, source_name: str = "document") -> List[Document]:
        """
        Split text into chunks for embedding
        
        Args:
            text: Text to chunk
            source_name: Source document name for metadata
            
        Returns:
            List of Document objects
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", ", ", " ", ""]
        )
        
        chunks = splitter.split_text(text)
        
        documents = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": source_name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "is_beginning": i < 3,  # Mark first 3 chunks as document beginning
                }
            )
            documents.append(doc)
        
        return documents
    
    def process_pdfs(self, uploaded_files: list) -> Tuple[bool, int, List[str]]:
        """
        Process multiple PDF files and add to vector store
        
        Args:
            uploaded_files: List of Streamlit uploaded file objects
            
        Returns:
            (success, docs_processed, errors)
        """
        if not uploaded_files:
            return False, 0, ["No files provided"]
        
        errors = []
        all_documents = []
        processed_count = 0
        
        for uploaded_file in uploaded_files:
            # Validate
            is_valid, error_msg = self.validate_pdf(uploaded_file)
            if not is_valid:
                errors.append(error_msg)
                continue
            
            try:
                # Extract text
                text, page_count = self.extract_text_from_pdf(uploaded_file)
                
                # Chunk
                docs = self.chunk_text(text, source_name=uploaded_file.name)
                all_documents.extend(docs)
                
                # Store document summary (first chunks) for quick reference
                first_chunk_texts = [doc.page_content for doc in docs[:3]]
                self.store_document_summary(uploaded_file.name, first_chunk_texts)
                
                processed_count += 1
                logger.info(f"Processed '{uploaded_file.name}': {page_count} pages, {len(docs)} chunks")
                
            except Exception as e:
                errors.append(f"Error processing '{uploaded_file.name}': {str(e)}")
                logger.error(f"Error processing {uploaded_file.name}: {e}")
        
        if all_documents:
            try:
                # Create or update vector store
                self._vector_store = Chroma.from_documents(
                    documents=all_documents,
                    embedding=self.embeddings,
                    persist_directory=self._persist_directory,
                    collection_name="medbook_docs"
                )
                logger.info(f"Added {len(all_documents)} chunks to vector store")
                
            except Exception as e:
                errors.append(f"Error creating vector store: {str(e)}")
                logger.error(f"Error creating vector store: {e}")
                return False, 0, errors
        
        return processed_count > 0, processed_count, errors
    
    def query(self, question: str, use_context_memory: bool = True) -> Tuple[Optional[str], List[str]]:
        """
        Query the RAG system with improved context handling
        
        Args:
            question: User's question
            use_context_memory: Whether to use previously retrieved context for follow-ups
            
        Returns:
            (context, source_documents) or (None, []) if no relevant docs
        """
        if self.vector_store is None:
            return None, ["No documents"]
        
        question_lower = question.lower()
        
        # Check for document overview questions
        is_overview_question = any(phrase in question_lower for phrase in [
            "what is this document", "what is the document", "what is the pdf",
            "summarize", "summary", "overview", "about this document",
            "what does the document", "what does this pdf", "tell me about the document"
        ])
        
        # For overview questions, retrieve document beginnings
        if is_overview_question and 'document_summaries' in st.session_state:
            summaries = st.session_state.document_summaries
            if summaries:
                combined_summary = "\n\n---\n\n".join([
                    f"**{name}:**\n{summary}" 
                    for name, summary in summaries.items()
                ])
                sources = list(summaries.keys())
                
                # Store in session for follow-ups
                st.session_state.last_rag_context = combined_summary
                st.session_state.last_rag_sources = sources
                
                return combined_summary, sources
        
        try:
            # Search for relevant documents with more results
            results = self.vector_store.similarity_search_with_relevance_scores(
                question,
                k=TOP_K_RESULTS
            )
            
            if not results:
                # Try using last context for follow-up questions
                if use_context_memory:
                    last_context = self.get_last_context()
                    if last_context:
                        return last_context, self.get_last_sources()
                return None, ["No relevant information found"]
            
            # Filter by relevance score (lower threshold now)
            relevant_docs = [(doc, score) for doc, score in results if score >= MIN_RELEVANCE_SCORE]
            
            if not relevant_docs:
                # Try using last context for follow-up questions
                if use_context_memory:
                    last_context = self.get_last_context()
                    if last_context:
                        logger.info("Using last context for follow-up question")
                        return last_context, self.get_last_sources()
                return None, ["No sufficiently relevant information found"]
            
            # Sort by relevance (highest first)
            relevant_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Prepare context from relevant documents
            context_parts = []
            sources = set()
            
            for doc, score in relevant_docs:
                context_parts.append(doc.page_content)
                sources.add(doc.metadata.get("source", "Unknown"))
                logger.debug(f"Retrieved chunk (score={score:.3f}): {doc.page_content[:100]}...")
            
            context = "\n\n---\n\n".join(context_parts)
            source_list = list(sources)
            
            # Store in session for follow-up questions
            st.session_state.last_rag_context = context
            st.session_state.last_rag_sources = source_list
            
            return context, source_list
            
        except Exception as e:
            logger.error(f"Error querying RAG: {e}")
            return None, [f"Error: {str(e)}"]
    
    def get_all_document_names(self) -> List[str]:
        """Get list of all uploaded document names"""
        if 'document_summaries' in st.session_state:
            return list(st.session_state.document_summaries.keys())
        return []
    
    def clear(self):
        """Clear the vector store"""
        try:
            if self._vector_store is not None:
                self._vector_store.delete_collection()
                self._vector_store = None
            
            # Remove persist directory
            import shutil
            if os.path.exists(self._persist_directory):
                shutil.rmtree(self._persist_directory)
            
            # Clear session state
            if 'document_summaries' in st.session_state:
                del st.session_state.document_summaries
            if 'last_rag_context' in st.session_state:
                del st.session_state.last_rag_context
            if 'last_rag_sources' in st.session_state:
                del st.session_state.last_rag_sources
            
            logger.info("Vector store cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get the number of documents in the vector store"""
        if self.vector_store is None:
            return 0
        try:
            return self.vector_store._collection.count()
        except Exception:
            return 0


# Session-based singleton (for Streamlit)
def get_rag_pipeline() -> RAGPipeline:
    """Get or create RAG pipeline instance from session state"""
    if 'rag_pipeline' not in st.session_state:
        st.session_state.rag_pipeline = RAGPipeline()
    return st.session_state.rag_pipeline
