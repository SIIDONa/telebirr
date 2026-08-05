import sqlite3

DB = "receipts.db"


def db():
    return sqlite3.connect(DB)


def init_db():

    conn=db()
    cur=conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS receipts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt TEXT UNIQUE,
        sender TEXT,
        amount TEXT,
        date TEXT,
        status TEXT,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()



def exists(receipt):

    conn=db()
    cur=conn.cursor()

    cur.execute(
        "SELECT receipt FROM receipts WHERE receipt=?",
        (receipt,)
    )

    data=cur.fetchone()

    conn.close()

    return data is not None



def save(data):

    conn=db()
    cur=conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO receipts
    (receipt,sender,amount,date,status)
    VALUES(?,?,?,?,?)
    """,
    (
        data["receipt"],
        data["sender"],
        data["amount"],
        data["date"],
        data["status"]
    ))

    conn.commit()
    conn.close()



def count():

    conn=db()
    cur=conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM receipts"
    )

    result=cur.fetchone()[0]

    conn.close()

    return result
