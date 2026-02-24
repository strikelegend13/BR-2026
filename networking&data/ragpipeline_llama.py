# rag pipeline, free, via llama 3
#  PDFs, plain text, JPG/PNG images, Word documents 
# run this in terminal first:
# pip install llama-index llama-index-llms-ollama llama-index-embeddings-ollama
# pip install python-docx pytesseract pillow pdf2image
# pip install chromadb
# unfinished, though it still should run locally
# also need Ollama installed on your machine

import os
import glob
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core import StorageContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.node_parser import SentenceSplitter
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

# ── pytesseract for OCR on images
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import docx
# folder where your documents live
DOCUMENTS_DIR = "./documents"
# folder where the vector store is saved so you don't re-embed every run
VECTOR_STORE_DIR = "./chroma_db_llama"
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# type of extraction
def extract_text_from_file(filepath):
    """Takes any supported file and returns its text as a string."""
    ext = os.path.splitext(filepath)[1].lower()
  # txts - just read directly
    if ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    # word - use python-docx to read paragraphs
    elif ext == ".docx":
        doc = docx.Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])
    # jpg,jpeg,png - use OCR to extract text from the image
    elif ext in [".jpg", ".jpeg", ".png"]:
        image = Image.open(filepath)
        return pytesseract.image_to_string(image, lang='eng')
    # PDF convert each page to an image then OCR it
    elif ext == ".pdf":
        images = convert_from_path(filepath, dpi=300)
        alltext = []
        for i, image in enumerate(images):
            print("  OCR page ", i+1, "/", len(images), "...")
            text = pytesseract.image_to_string(image, lang='eng')
            alltext.append("--- Page " + str(i+1) + " ---\n" + text)
        return "\n".join(alltext)

    else:
        print("Unsupported file type: ", ext, " — skipping ", filepath)
        return ""

                  #loops through files in documents folder and extracts text
def load_all_documents(directory):
    """Loops through all files in the documents folder and extracts text."""
    # supported file types
    extensions = ["*.txt", "*.pdf", "*.docx", "*.jpg", "*.jpeg", "*.png"]
    docs = []
    for ext in extensions:
        for filepath in glob.glob(os.path.join(directory, ext)):
            print("Loading: ", filepath)
            text = extract_text_from_file(filepath)
            if text.strip():
                # store as a dict with the text and source filename
                docs.append({"text": text, "source": os.path.basename(filepath)})

    print("Loaded ", len(docs), " document(s).\n")
    return docs

# splitting documents into chunks to retrieve more accurately
def chunkdocuments(docs, chunk_size=512, chunk_overlap=50):
    """
    Splits documents into smaller chunks.
    chunk_size: how many words per chunk (smaller = more precise retrieval)
    chunk_overlap: how many words overlap between chunks so context isn't lost
    """
    chunks = []
    for doc in docs:
        text = doc["text"]
        words = text.split()
        # slide a window across the words
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append({"text": chunk, "source": doc["source"]})
    print("Created ", len(chunks), " chunks.\n")
    return chunks

# emedding vector store
def vectorstore(chunks):
    """
    Converts each chunk into an embedding (vector of numbers)
    and stores them in ChromaDB for fast similarity search.
    Uses Ollama's local embedding model so nothing leaves your machine.
    """
    # connect to local ChromaDB
    client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)
    collection = client.get_or_create_collection("rag_documents")

    # set up local embedding model via Ollama
    EMBED_MODEL = OllamaEmbedding(model_name="llama3")

    print("Embedding chunks into vector store...")
    for i, chunk in enumerate(chunks):
        # convert the chunk text into a vector (list of numbers)
        embedding = EMBED_MODEL.get_text_embedding(chunk["text"])
        # store the vector, the original text, and the source filename
        collection.add(
            ids=[str(i)],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[{"source": chunk["source"]}]
        )
        if (i + 1) % 10 == 0:
            print("  Embedded ", i+1, "/", len(chunks), " chunks...")

    print("Vector store built and saved to ", VECTOR_STORE_DIR, "\n")
    return collection


def load_vector_store():
    """Loads an existing vector store from disk so you don't re-embed every time."""
    client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)
    collection = client.get_or_create_collection("rag_documents")
    return collection

# retrieval of relevant chunks
def retrieve(query, collection, top_k=5):
    """
    Takes a question, converts it to an embedding,
    and finds the top_k most similar chunks in the vector store.
    top_k=5 means it returns the 5 most relevant chunks.
    """
    EMBED_MODEL = OllamaEmbedding(model_name="llama3")
    query_embedding = EMBED_MODEL.get_text_embedding(query)

    # search the vector store for similar chunks
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    # return the actual text chunks and their sources
    chunks = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    return chunks, sources

# return
def ask(query, collection):
    """
    Full RAG flow:
    1. Retrieve relevant chunks from vector store
    2. Build a prompt combining the question + retrieved context
    3. Send to LLaMA 3 running locally via Ollama
    4. Return the answer + sources
    """
    print("\nSearching documents for: ", query)
    chunks, sources = retrieve(query, collection)

    # chunk context
    context = "\n\n".join(chunks)
# rag prompt
prompt = (
        f"You are a helpful assistant. Answer the question below using ONLY "
        f"the context provided. If the answer is not in the context, say "
        f"'I could not find this in the provided documents.'\n\n"
        f"context?:\n{context}\n\n"
        f"question?: {query}\n\n"
        f"Answer:"
    )

    # call LLaMA 3 running locally via Ollama
    llm = Ollama(model="llama3", request_timeout=120.0)
    response = llm.complete(prompt)

    print("\n--- ANSWER ---")
    print(response.text)
    print("\n--- SOURCES ---")
    for source in set(sources):
        print("  - ", source)
    print("-" * 40)

    return response.text, sources

#  MAIN 
if __name__ == "__main__":
    # check if vector store already has data so we skip re-embedding
    client = chromadb.PersistentClient(path=VECTOR_STORE_DIR)
    collection = client.get_or_create_collection("rag_documents")
    if collection.count() == 0:
        # first run - load, chunk, embed everything
        print("No existing vector store found. Building from scratch...\n")
        docs = load_all_documents(DOCUMENTS_DIR)
        if not docs:
            print("No documents found in ", DOCUMENTS_DIR)
            print("Add some PDFs, text files, images, or Word docs and run again.")
            exit()
        chunks = chunkdocuments(docs)
        collection = vectorstore(chunks)
    else:
        # vector store already exists, just load it
        print("Loading existing vector store (", collection.count(), " chunks).\n")
        collection = load_vector_store()

    #  question loop
    print("Type your question or enter quit/exit/q to quit\n")
    while True:
        query = input("Your question: ").strip()
        if query.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        if query:
            ask(query, collection)
