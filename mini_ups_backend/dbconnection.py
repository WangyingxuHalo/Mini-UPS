import psycopg2

def connectDB():
    try:
        conn = psycopg2.connect("dbname=postgres user=postgres password=a159753654 host=localhost port=5432")
        print("Connect to DB success")
        return conn
    except:
        print("Conncect to DB failed")

#-------------------!!not used&finished
def emptyDB():
    conn = connectDB()
    cur = conn.cur()
    print("Emptying databse.")
    cur.execute('TRUNCATE TABLE Truck')
    #cur.execute('T')
    print("Finished emptying database")
    cur.close()

def closeDB(conn):
    if conn is not None:
        conn.close()
        print("Database connection closed.")