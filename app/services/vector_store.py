from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.core.text_splitter import TokenTextSplitter
import logging
from app.config.settings import OPENAI_API_KEY, VECTOR_STORE_CONFIG, DATA_DIR

# Set up logging
logger = logging.getLogger(__name__)

class VectorStoreService:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStoreService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialize()
            self._initialized = True

    def _initialize(self):
        """Initialize the vector store and query engine"""
        logger.info("Initializing vector store service")
        # Set up LlamaIndex
        self.llm = LlamaOpenAI(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY
        )

        # Set global settings
        Settings.llm = self.llm
        Settings.chunk_size = VECTOR_STORE_CONFIG['CHUNK_SIZE']
        Settings.chunk_overlap = VECTOR_STORE_CONFIG['CHUNK_OVERLAP']

        # Initialize text splitter
        self.text_splitter = TokenTextSplitter(
            chunk_size=VECTOR_STORE_CONFIG['CHUNK_SIZE'],
            chunk_overlap=VECTOR_STORE_CONFIG['CHUNK_OVERLAP']
        )

        # Load and index documents
        self.index = self._initialize_index()

        # Set up vector retriever
        self.vector_retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=VECTOR_STORE_CONFIG['TOP_K']
        )

        # Apply reranking
        self.reranker = SentenceTransformerRerank(
            model=VECTOR_STORE_CONFIG['RERANKER_MODEL'],
            top_n=VECTOR_STORE_CONFIG['TOP_N']
        )

        # Create query engine
        self.query_engine = RetrieverQueryEngine(
            retriever=self.vector_retriever,
            node_postprocessors=[self.reranker]
        )
        logger.info("Vector store service initialized successfully")

    def _initialize_index(self):
        """Initialize the document index"""
        try:
            logger.info(f"Loading documents from: {DATA_DIR}")
            # Load documents from the data directory
            documents = SimpleDirectoryReader(DATA_DIR).load_data()
            logger.info(f"Loaded {len(documents)} documents")
            
            # Create index with text splitter
            logger.info("Creating vector index...")
            index = VectorStoreIndex.from_documents(
                documents,
                text_splitter=self.text_splitter,
                show_progress=True
            )
            logger.info("Vector index created successfully")
            return index
        except Exception as e:
            logger.error(f"Error initializing index: {str(e)}")
            raise

    def query(self, query_text: str, conversation_history: list = None) -> str:
        """Process a query and return the response"""
        try:
            logger.info(f"Processing query: {query_text[:50]}...")
            # Get relevant context from the index
            response = self.query_engine.query(query_text)
            
            # Format conversation history if available
            history_context = ""
            if conversation_history:
                logger.info(f"Including conversation history of {len(conversation_history)} messages")
                history_context = "Previous conversation:\n"
                for msg in conversation_history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    history_context += f"{role}: {msg['content']}\n"
                history_context += "\n"
            
            # Construct prompt with retrieved context and conversation history
            augmented_prompt = f"""Based on the following context, conversation history, and your knowledge as an AI assistant, please answer the question.
            If the answer cannot be found in the context, say 'I am not sure, but you can contact our support at 718-971-9914 or newturbony@gmail.com.'
            
            {history_context}
            Context: {response.response}
            
            Question: {query_text}
            """
            
            return augmented_prompt
            
        except Exception as e:
            logger.error(f"Error in query processing: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again." 