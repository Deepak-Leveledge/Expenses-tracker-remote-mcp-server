import sqlite3
from fastmcp import FastMCP
import os
import aiosqlite  # Changed: sqlite3 → aiosqlite
import tempfile
# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("Expenses-tracker")

def init_db():  # Keep as sync for initialization
    try:
        # Use synchronous sqlite3 just for initialization
        import sqlite3
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
            # Test write access
            c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            print("Database initialized successfully with write access")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

# Initialize database synchronously at module load
init_db()

@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):  
    '''Add a new expense entry to the database.'''
    try:
        async with aiosqlite.connect(DB_PATH) as c:  
            cur = await c.execute(  
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            expense_id = cur.lastrowid
            await c.commit()  
            return {"status": "success", "id": expense_id, "message": "Expense added successfully"}
    except Exception as e:  
        if "readonly" in str(e).lower():
            return {"status": "error", "message": "Database is in read-only mode. Check file permissions."}
        return {"status": "error", "message": f"Database error: {str(e)}"}
    


@mcp.tool()
def get_all_expenses():
    """Retrieve all expenses from the database."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("SELECT id ,date,amount,category,subcategory,note FROM expenses ORDER BY date ASC")
        cols = [description[0] for description in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    

@mcp.tool()
def list_expenses_by_date(start_date, end_date):
    """List expenses within a date range."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("SELECT id ,date,amount,category,subcategory,note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC",
                       (start_date, end_date))
        cols = [description[0] for description in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

@mcp.tool()
def summarize(start_date, end_date,category=None):
    """Summarize expenses by category within a date range."""
    with sqlite3.connect(DB_PATH) as c:
        query=(
            """"
            SELECT category, SUM(amount) as total_amount 
            FROM expenses 
            WHERE date BETWEEN ? AND ? 
            """
        )
        params=[start_date,end_date]

        if category:
            query+=" AND category=?"
            params.append(category)

        query+=" GROUP BY category ORDER BY category ASC"

        curr = c.execute(query,params)
        cols = [description[0] for description in curr.description]
        return [dict(zip(cols, row)) for row in curr.fetchall()]
    

@mcp.resource("expenses://categories",mime_type="application/json")
def get_categories():
    """Serve the categories.json file."""
    with open(CATEGORIES_PATH, 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=5000)
