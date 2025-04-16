import os # Added for potential API key loading
# import hashlib # No longer needed for IDs
import chromadb # Added for client operations
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Consider adding: from dotenv import load_dotenv
# Consider adding: load_dotenv() # Load environment variables for API keys

# Initialize embeddings
# Ensure OPENAI_API_KEY is set as an environment variable
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Define Chroma settings
persist_directory = "./chroma_langchain_db"
collection_name = "wto_texts"

# Define the metadata extraction function
def metadata_func(record: dict, metadata: dict) -> dict:
    metadata["document"] = record.get("document")
    metadata["title"] = record.get("title")
    metadata["link"] = record.get("link")
    # Add source for context, using link or fallback to filename
    metadata["source"] = record.get("link", json_file_path)
    return metadata

# Load JSON documents
json_file_path = "./wto_links_with_content.json" # Corrected filename

loader = JSONLoader(
    file_path=json_file_path,
    jq_schema='.[] | select(.content != null and .content != "")', # Filter empty content at load time
    content_key="content",
    metadata_func=metadata_func,
    text_content=False # Ensure content is treated as string, not parsed further if it looks like JSON/dict
)

print("Loading documents...")
try:
    data = loader.load()
    print(f"Loaded {len(data)} non-empty documents.")
except FileNotFoundError:
    print(f"Error: JSON file not found at {json_file_path}")
    exit()
except Exception as e:
    print(f"Error loading JSON data: {e}")
    exit()


if not data:
    print("No documents loaded, exiting.")
    exit()

# Split documents into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # chunk size (characters)
    chunk_overlap=200,  # chunk overlap (characters)
    add_start_index=True,  # track index in original document
)
print("Splitting documents...")
all_splits = text_splitter.split_documents(data)
print(f"Split into {len(all_splits)} chunks.")

# Generate unique IDs for each split to prevent duplicates - REMOVED

# Initialize Chroma client to manage collections
print(f"Initializing Chroma client for directory: {persist_directory}")
client = chromadb.PersistentClient(path=persist_directory)

# Check if collection exists and delete it to ensure a fresh start
print(f"Checking for existing collection: {collection_name}")
collection_names = client.list_collections() # Get list of collection names (strings)
if collection_name in collection_names: # Check if the name exists in the list of Collection objects
    print(f"Deleting existing collection: {collection_name}")
    client.delete_collection(name=collection_name)
    print(f"Collection '{collection_name}' deleted.")
else:
    print(f"Collection '{collection_name}' does not exist. A new one will be created.")


# Create the vector store and add documents (will create the collection)
print(f"Creating/Recreating collection '{collection_name}' and adding documents...")
vector_store = Chroma.from_documents(
    documents=all_splits,
    embedding=embeddings,
    # ids=split_ids, # REMOVED IDs parameter
    collection_name=collection_name,
    persist_directory=persist_directory,
)

print(f"Vector database setup complete. Collection '{collection_name}' persisted to '{persist_directory}'.")