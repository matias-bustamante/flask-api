from flask import jsonify, send_file
from io import BytesIO
import pandas as pd 


def procesar_exportacion(df, pregunta): 
    """Genera el binario de Excel y lo prepara para la descarga"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Epiron')
    output.seek(0)

    # Nota: Para Power BI, podrías necesitar devolver un JSON con un link 
    # o usar send_file si el visual lo soporta directamente.
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name="Reporte_Epiron.xlsx"
    )