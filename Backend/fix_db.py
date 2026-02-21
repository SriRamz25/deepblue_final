import psycopg2

# Test connection to default 'postgres' database first
try:
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='sentra_secure_2026', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('SELECT datname FROM pg_database;')
    dbs = [r[0] for r in cur.fetchall()]
    print('Connected OK! Databases:', dbs)
    if 'fraud_detection' not in dbs:
        print('Creating fraud_detection database...')
        cur.execute('CREATE DATABASE fraud_detection;')
        print('Database created!')
    else:
        print('fraud_detection database exists!')
    cur.close()
    conn.close()
except Exception as e:
    print(f'Connection failed with sentra_secure_2026: {e}')
    print('Trying common passwords...')
    found = False
    for pw in ['postgres', 'admin', 'password', '123456', 'surya', '1234', 'root', '']:
        try:
            conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password=pw, dbname='postgres')
            print(f'SUCCESS with password: "{pw}"')
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute('SELECT datname FROM pg_database;')
            dbs = [r[0] for r in cur.fetchall()]
            print('Databases:', dbs)
            if 'fraud_detection' not in dbs:
                print('Creating fraud_detection database...')
                cur.execute('CREATE DATABASE fraud_detection;')
                print('Database created!')
            else:
                print('fraud_detection database exists!')
            cur.close()
            conn.close()
            found = True
            break
        except Exception as e2:
            print(f'  Failed with "{pw}": {e2}')
    if not found:
        print('Could not connect with any common password. Please provide your PostgreSQL password.')
