import psycopg2

conn = psycopg2.connect(
    "dbname=dcblmalbr3hc29 user=qmtjusahysfbuw password=bf7f88662ef00c9c5e67ed275021c3d698472f04dcf753b77a5a92311ca1f3a6 host=ec2-50-19-86-139.compute-1.amazonaws.com port=5432"
)


def sql(command: str, data=()):
    with conn:
        with conn.cursor() as curs:
            curs.execute(command)
            return curs.fetchall()


def insert(command: str, data=()):
    with conn:
        with conn.cursor() as curs:
            curs.execute(command, data)
            return curs.statusmessage


'''
Example Usage:

status = insert("INSERT INTO test (num, data) VALUES (%s, %s);", (150, "fff"))
print(status)

results = sql("SELECT * from test WHERE id > 3;")
print(results)

'''
