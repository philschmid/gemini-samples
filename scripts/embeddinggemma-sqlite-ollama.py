# To run this script, you need to install the following packages:
# uv pip install ollama sqlite-vec numpy
#
# Please make sure Ollama is running and you have pulled the 'embeddinggemma:latest' model, `ollama pull embeddinggemma:latest`.

import sqlite3
import sqlite_vec
from sqlite_vec import serialize_float32
import ollama
import numpy as np
import sys

# Configuration
DB_FILE = "gemma_embeddings.db"
MODEL_NAME = "embeddinggemma:latest"
EMBEDDING_DIM = 768
SAMPLE_TEXTS = [
    "The sky is blue because of Rayleigh scattering.",
    "Photosynthesis is the process used by plants to convert light energy into chemical energy.",
    "The Roman Empire was the post-Republican period of ancient Rome.",
    "Artificial intelligence is intelligence demonstrated by machines.",
    "Climate change is a long-term change in the average weather patterns.",
]


def get_db_connection():
    """Establishes a connection to the SQLite database and loads the sqlite-vec extension."""
    db = sqlite3.connect(DB_FILE)
    # The following two lines are essential for loading the sqlite-vec extension
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    version_info = db.execute("select vec_version()").fetchone()[0]
    print(f"Using sqlite-vec version: {version_info}")
    return db


def setup_database(db):
    """Sets up the database tables and populates them with sample data embeddings if the database is empty."""
    try:
        count = db.execute("SELECT COUNT(*) FROM vec_items").fetchone()[0]
        if count > 0:
            print("Database already contains data. Skipping setup.")
            return
    except sqlite3.OperationalError:
        # This error means the table doesn't exist, so we proceed with setup
        pass

    print("Setting up a new database...")
    # Create the necessary tables
    db.execute(
        f"CREATE VIRTUAL TABLE vec_items USING vec0(embedding float[{EMBEDDING_DIM}], content TEXT)"
    )

    print("Embedding and storing sample texts...")
    embeddings_response = ollama.embed(model=MODEL_NAME, input=SAMPLE_TEXTS)
    # Use a transaction to insert all data at once for efficiency
    with db:
        for text, embedding in zip(SAMPLE_TEXTS, embeddings_response.embeddings):
            # Convert the embedding to a NumPy array of 32-bit floats for sqlite-vec
            db.execute(
                "INSERT INTO vec_items(embedding, content) VALUES (?, ?)",
                (serialize_float32(embedding), text),
            )
    print("Database setup complete.")


def main():
    """Main function to run the interactive semantic search script."""
    db = get_db_connection()
    setup_database(db)
    print("Enter a query to find the most similar text from the database.")

    try:
        while True:
            query = input("\nEnter a search query (or 'exit' to quit): ")
            if query.lower() == "exit":
                break
            if not query.strip():
                continue

            query_embedding_response = ollama.embed(model=MODEL_NAME, input=query)
            # Perform the vector search
            rows = db.execute(
                """
                SELECT
                    content,
                    distance
                FROM vec_items
                WHERE embedding MATCH ?
                AND k = 3
                ORDER BY distance
                """,
                [serialize_float32(query_embedding_response.embeddings[0])],
            ).fetchall()

            # Display the results
            print("\nTop 3 most similar texts:")
            print("Lower distance is means, closer together, more similar.")
            for i, (content, distance) in enumerate(rows):
                print(f"{i+1}. {content} (distance: {distance:.4f})")

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        db.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
