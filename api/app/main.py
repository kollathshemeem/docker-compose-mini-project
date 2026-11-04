from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Docker Compose 3-Tier API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Connect to PostgreSQL
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


# Request data format
class Item(BaseModel):
    name: str


# Create database table when API starts
@app.on_event("startup")
def startup():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


# Health check
@app.get("/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Read all items
@app.get("/items")
def get_items():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM items ORDER BY id")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [{"id": row[0], "name": row[1]} for row in rows]


# Add an item
@app.post("/items")
def create_item(item: Item):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO items (name) VALUES (%s) RETURNING id",
        (item.name,),
    )

    item_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return {"id": item_id, "name": item.name}


# Delete an item
@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM items WHERE id = %s RETURNING id",
        (item_id,),
    )

    deleted = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    if deleted is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"message": "Item deleted", "id": item_id}
