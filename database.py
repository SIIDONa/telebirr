import os
import psycopg2

# Render ላይ የምናስገባውን የዳታቤዝ ሊንክ ይቀበላል
DB_URL = os.environ.get("DATABASE_URL")

def get_connection():
    """ከ PostgreSQL ጋር ኮኔክሽን ይፈጥራል"""
    if not DB_URL:
        raise ValueError("DATABASE_URL is not set in environment variables!")
    return psycopg2.connect(DB_URL)

def init_db():
    """ቴብሉን ይፈጥራል (ከሌለ ብቻ)"""
    conn = get_connection()
    c = conn.cursor()
    # PostgreSQL ላይ REAL ን ወደ NUMERIC ወይም DOUBLE PRECISION እንቀይራለን
    c.execute('''CREATE TABLE IF NOT EXISTS receipts
                 (receipt_id TEXT PRIMARY KEY, amount NUMERIC, sender TEXT, date TEXT)''')
    conn.commit()
    c.close()
    conn.close()

def exists(receipt_id):
    """ሪሲፕቱ ከዚህ በፊት ጥቅም ላይ መዋሉን ማረጋገጥ"""
    conn = get_connection()
    c = conn.cursor()
    # PostgreSQL parameters '%s' ይጠቀማል ('?' ን አይደለም)
    c.execute("SELECT receipt_id FROM receipts WHERE receipt_id=%s", (receipt_id,))
    result = c.fetchone()
    c.close()
    conn.close()
    return result is not None

def save(data):
    """አዲሱን ሪሲፕት ወደ ዳታቤዝ ማስቀመጥ"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO receipts (receipt_id, amount, sender, date) VALUES (%s, %s, %s, %s)",
              (data["transactionId"], data["amount"], data["payerName"], data["paymentDate"]))
    conn.commit()
    c.close()
    conn.close()
