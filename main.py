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
async def get_all_expenses():
    """Retrieve all expenses from the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "SELECT id, date, amount, category, subcategory, note FROM expenses ORDER BY date ASC"
            )
            rows = await cur.fetchall()
            cols = [description[0] for description in cur.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
async def list_expenses_by_date(start_date, end_date):
    """List expenses within a date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "SELECT id, date, amount, category, subcategory, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date ASC",
                (start_date, end_date)
            )
            rows = await cur.fetchall()
            cols = [description[0] for description in cur.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses by date: {str(e)}"}


@mcp.tool()
async def summarize(start_date, end_date, category=None):
    """Summarize expenses by category within a date range."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            query = (
                "SELECT category, SUM(amount) as total_amount "
                "FROM expenses "
                "WHERE date BETWEEN ? AND ?"
            )
            params = [start_date, end_date]

            if category:
                query += " AND category=?"
                params.append(category)

            query += " GROUP BY category ORDER BY category ASC"

            cur = await c.execute(query, params)
            rows = await cur.fetchall()
            cols = [description[0] for description in cur.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses by date: {str(e)}"}


@mcp.tool()
async def delete_expense_by_id_catogery(catogery, expense_id):
    """Delete an expense by ID."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "DELETE FROM expenses WHERE id=? AND category=?",
                (expense_id, catogery)
            )
            await c.commit()
            if cur.rowcount == 0:
                return {"status": "error", "message": "No expense found with the given ID and category."}
            return {"status": "success", "message": "Expense deleted successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Error deleting expense: {str(e)}"}
    

@mcp.tool()
async def delete_expense_by_id(expense_id):
    """Delete an expense by ID."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "DELETE FROM expenses WHERE id=?",
                (expense_id,)
            )
            await c.commit()
            if cur.rowcount == 0:
                return {"status": "error", "message": "No expense found with the given ID."}
            return {"status": "success", "message": "Expense deleted successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Error deleting expense: {str(e)}"}

@mcp.tool()
async def delete_expenses_by_category(category):
    """Delete all expenses in a given category."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "DELETE FROM expenses WHERE category=?",
                (category,)
            )
            await c.commit()
            return {"status": "success", "message": f"Deleted {cur.rowcount} expenses in category '{category}'."}
    except Exception as e:
        return {"status": "error", "message": f"Error deleting expenses by category: {str(e)}"}
    

@mcp.tool()
async def delete_all_expenses():
    """Delete all expenses from the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute("DELETE FROM expenses")
            await c.commit()
            return {"status": "success", "message": f"Deleted all expenses ({cur.rowcount} records)."}
    except Exception as e:
        return {"status": "error", "message": f"Error deleting all expenses: {str(e)}"}
    


@mcp.tool()
async def update_expense(expense_id, date=None, amount=None, category=None, subcategory=None, note=None):
    """Update an existing expense entry."""
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            fields = []
            params = []

            if date is not None:
                fields.append("date=?")
                params.append(date)
            if amount is not None:
                fields.append("amount=?")
                params.append(amount)
            if category is not None:
                fields.append("category=?")
                params.append(category)
            if subcategory is not None:
                fields.append("subcategory=?")
                params.append(subcategory)
            if note is not None:
                fields.append("note=?")
                params.append(note)

            if not fields:
                return {"status": "error", "message": "No fields to update."}

            params.append(expense_id)
            query = f"UPDATE expenses SET {', '.join(fields)} WHERE id=?"
            cur = await c.execute(query, params)
            await c.commit()

            if cur.rowcount == 0:
                return {"status": "error", "message": "No expense found with the given ID."}
            return {"status": "success", "message": "Expense updated successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Error updating expense: {str(e)}"}
    

    

@mcp.resource("expense:///categories", mime_type="application/json")  # Changed: expense:// → expense:///
def categories():
    try:
        # Provide default categories if file doesn't exist
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }
        
        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            import json
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=5000)
