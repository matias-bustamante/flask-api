from datetime import datetime 
from flask import jsonify 
from database.db import get_connection 

def validar_token(token, cuenta):
    try:
        conn=get_connection() 
        with conn.cursor() as cursor: 
            query="""Select cuenta FROM CDG_Movistar_Reports.dbo.Seguridad_API 
                     where token=? and cuenta = ? and activo=1
            """
            cursor.execute(query,(token,cuenta, ))
            result=cursor.fetchone() 
        if result is None: 
            return False 
        return True 
    except Exception as e: 
        return False 
