from flask import Blueprint, jsonify, request, abort, send_file  
import numpy as np 
import pandas as pd 
from io import BytesIO
from utils.validar_token import validar_token 
from utils.exportar_excel import procesar_exportacion
import google.generativeai as genai
from google.generativeai import embed_content 
from decouple import config
from database.db import get_connection 
import hashlib



gemini_ai=Blueprint("gemini_ai", __name__)

def obtener_embedding(pregunta): 
    resultado=embed_content(
        model="models/gemini-embedding-001", 
        content=pregunta, 
        task_type="retrieval_query"
    )
    return resultado["embedding"]

def calcular_similitud(v1, v2):
     # Similitud de Coseno: 1.0 es idéntico, 0.0 es nada que ver
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)) 
     

@gemini_ai.route("/api/<pregunta>", methods=['GET'])
def inicio(pregunta): 
    clave=request.headers.get('X-API-KEY')
    historial_previo=request.args.get('historial', '')
    conn=get_connection() 
    cursor=conn.cursor() 
    
    auth_key=validar_token(clave, 'CDG_Movistar_Reports')
    if (auth_key==False): 
        return jsonify({"status":"Error", "message":"Error de autenticación de clave"})
    
    genai.configure(api_key=config('API_KEY'))
    model = genai.GenerativeModel('models/gemini-flash-latest')

    esquema_db=""" 
                    Tabla 'CDG_Movistar_Reports.dbo.epiron': columnas[Fecha,empresa, unidad_negocio, centro_atencion, empleado, documento_empleado, inicio_vigencia_un, usuario_epiron, usuario_vigente_actualidad, instancia, cantidad_inicio_sesion_rango, ultimo_inicio_sesion_rango_fecha_filtradas, id_meucci, lider, jefe, cuenta, area, servicio, sucursal, site, ausente, franco, LP, ausentismo_motivo, cargo_nombre, usuario_baja, Ausente_Texto, FechaBajaReal, estado_vigencia, estado_usuario]
                    Metadata: Fecha: Corresponde a la fecha del registro 
                            Empresa: Indica la entidad organizacional en la cual opera el representante
                            unidad_negocio: Indica la unidad de negocio que opera un representante
                            centro_atencion: Corresponde desde que ubicación atienden los representantes. 
                            empleado: Es el nombre del representante o también puede ser el nombre del lider en caso que el lider se logue a la herramienta de epiron. 
                            documento_empleado: En el DNI del empleado. 
                            inicio_vigencia_un: Es la fecha en la cual el representante esta operativo en la unidad de negocio
                            fin_vigencia_un: Es la fecha de finalización de vigencia del representante en la unidad de negocio, en caso que la fecha sea NULL significa que sigue activo en dicha unidad de negocio. 
                            usuario_epiron: Es el usuario que se utiliza para acceder a la herramienta de epiron. 
                            usuario_vigente_actualidad: Indica si el usuario se encuentra vigente o no se encuentra vigente, tiene dos valores SI y NO. 
                            instancia: Indican las distintas licencias que incorpora la herramienta epiron. 
                            cantidad_inicio_sesion_rango: Indica la cantidad de veces que se logueo el representante en el día. 
                            ultimo_inicio_sesion_rango_fecha_filtradas: Indica cual fuel la ultima vez que el representante inicio sesión, en caso de no iniciar sesion se establece "Sin Inicio Sesión". 
                            id_meucci: Es el ID que se registra en meucci, es unico por cada empleado de la compañia. 
                            lider: Indica el nombre del lider, se obtiene de meucci. 
                            jefe: Indica el nombre del jefe, se obtiene de meucci. 
                            cuenta: Indica la cuenta en la cual se encuentran registrado los representantes en meucci.
                            area: Es el área que se encuentra registrado en meucci. 
                            servicio: Indica el servicio de atención, si el servicio es NULL o esta vacio significa que no esta registrado en meucci o bien se trata de un área de staff. 
                            sucursal: Indica la provincia
                            Site: Indica cual es el site que se encuentran registrado los empleados. 
                            ausente: indica si el representante estuvo ausente, 1 significa ausente 0 significa presente. 
                            franco: Indica si el representante estuvo de franco, 1 significa que estuvo de franco y 0 no tuvo franco. 
                            LP: Indica si el empleado tiene Licencia prolongada, los valores son los siguientes SI, NO y S/D 
                            ausentismo_motivo: Es la descripción del motivo de ausentismo. 
                            cargo_nombre: Indica el cargo de los empleados. 
                            usuario_baja: Indica el estado del usuario, puede ser que este ACTIVO, NO VIGENTE y NO ACTIVO
                            ausente_texto: Indica en forma textual si el empleado estuvo ausente o presente. 
                            fechabajareal: Indica la fecha de baja efectiva del usuario de epiron. 
                            estado_vigencia: Indica si el usuario de epiron sigue activo o ha sido marcado como inactivo pero no se han registrado la fecha de baja del usuario. 

                            REGLAS DE NEGOCIO IMPORTANTES:
                            1. 'instancia' y 'licencia' son SINÓNIMOS. Si el usuario pregunta por licencias, 
                                se refiere a la columna 'instancia'.
                            2. Los nombres de las instancias/licencias son: Configurador, Gestor, Sin Instancia y Reportes Web.
                             """
    
    embeding=obtener_embedding(pregunta)
    vector=str(embeding)

    cursor.execute("SELECT id, sql_generado, vector FROM CDG_Movistar_Reports.dbo.Gemini_Cache_SQL")
    filas = cursor.fetchall()

    mejor_match=None 
    umbral=0.90 

    for id, sql_generado, vector_string in filas: 
         if vector_string: 
              try: 
                    
                    resultado_np = np.array([float(x) for x in vector_string.strip("[]").split(",")], dtype=float)
                    similitud=calcular_similitud(embeding, resultado_np)

                    if similitud>=umbral: 
                         mejor_match=sql_generado

                    
                    
              except Exception as e: 
                   print(f"Error al procesar el ID {id}: {e}")
                   return jsonify({
                    "status": "success",
                    "pregunta": pregunta,
                    "sql_generado": 'OK',
                    "datos_crudos": 'ok',
                    "respuesta_ia": 'Hubo un error'
                })

    
    if mejor_match: 
         sql_query=sql_generado 

        
    else: 

        prompt_sql = f"""
            Convierte la siguiente pregunta en una instrucción SQL Server: {pregunta}
            Usa este esquema: {esquema_db}
            IMPORTANTE: Devuelve UNICAMENTE el código SQL, sin explicaciones, sin bloques de código markdown, sin texto adicional.
            """
        response = model.generate_content(prompt_sql)
        sql_query = response.text.replace("```sql", "").replace("```", "").strip()
   

    try: 
        
        cursor.execute(sql_query) 
            
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            # 3. GEMINI INTERPRETA LOS RESULTADOS (Opcional)
                # Si quieres que la respuesta sea humana y no solo datos crudos:
        prompt_interpretacion = f"El usuario preguntó '{pregunta}'. La base de datos devolvió estos datos: {results}. Responde de forma natural y breve."
        respuesta_humana = model.generate_content(prompt_interpretacion).text

        if mejor_match is None: 
             
            cursor.execute(""" INSERT INTO CDG_Movistar_Reports.dbo.Gemini_Cache_SQL (vector, pregunta_original, sql_generado)
                       values(?,?,?) """, (vector, pregunta, sql_query ))
            conn.commit()
            
        return jsonify({
                    "status": "success",
                    "pregunta": pregunta,
                    "sql_generado": sql_query,
                    "datos_crudos": results,
                    "respuesta_ia": respuesta_humana
                })
    except Exception as e: 
         prompt=f"""El usuario contesto lo siguiente '{pregunta}'""" 
         response = model.generate_content(prompt).text
         return jsonify({
              "status":"success", 
              "message":response, 
              "respuesta_ia":response
         })
        
    
    
    