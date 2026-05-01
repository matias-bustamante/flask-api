import pyodbc
from decouple import config 

def get_connection():
    server = config('SERVER')
    database = config('DATABASE')
    username = config('DB_USERNAME')
    password = config('PASSWORD')

    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

    conn = pyodbc.connect(connection_string)
    return conn