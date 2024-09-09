from flask import Flask, request, jsonify
from flasgger import Swagger
from selenium_service import SeleniumService
from db_service import MongoService
from openai_service import generate_suggestions
from datetime import datetime
import os
import concurrent.futures

# Leer configuraciones desde variables de entorno
mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
db_name = os.getenv('DB_NAME', 'accessibility_db')
collection_name = os.getenv('COLLECTION_NAME', 'reports')
driver_path = os.getenv('DRIVER_PATH', './drivers/chromedriver.exe')
max_workers = int(os.getenv('MAX_WORKERS', '5'))

# Instanciar servicios
selenium_service = SeleniumService(driver_path)
mongo_service = MongoService(mongo_uri, db_name, collection_name)

app = Flask(__name__)
swagger = Swagger(app)


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Analiza múltiples URLs para la evaluación de accesibilidad.
    ---
    parameters:
      - name: urls
        in: body
        type: array
        items:
          type: string
        required: true
        description: Una lista de URLs para analizar.
    responses:
      200:
        description: Resultados del análisis de accesibilidad.
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            message:
              type: string
              example: Análisis completado
            data:
              type: array
              items:
                type: object
                properties:
                  url:
                    type: string
                    description: La URL que fue analizada.
                    example: "https://ejemplo.com"
                  unique_id:
                    type: string
                    description: ID único generado para el análisis.
                    example: "abc123"
                  _id:
                    type: string
                    description: ID del registro insertado en la base de datos.
                    example: "60c72b2f9e7b4a001c8e4e9b"
                  date:
                    type: string
                    description: Fecha en la que se realizó el análisis.
                    example: "2023-08-27T12:34:56Z"
                  suggestions:
                    type: object
                    description: Sugerencias generadas a partir del análisis.
                    example: {"suggestion1": "Consider revising the alt text for images.", "suggestion2": "Ensure that all form fields are labeled."}
      400:
        description: Datos de entrada no válidos.
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: "URLs should be a list"
      500:
        description: Error en el servidor durante el análisis.
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: "Error al realizar el análisis"
    """
    data = request.json
    urls = data.get('urls')

    if not urls or not isinstance(urls, list):
        return jsonify({"status": "error", "message": "URLs should be a list"}), 400

    results_summary = []

    def process_url(url):
        try:
            # Realizar el análisis de accesibilidad
            results, domain, unique_id, results_path = selenium_service.analyze_url(url)

            # Extraer solo la clave 'violations'
            violations = results.get('violations', [])

            # Generar sugerencias en español usando OpenAI solo con 'violations'
            suggestions_json = generate_suggestions(violations)

            # Crear el registro de resultados para MongoDB
            result_record = {
                "url": url,
                "domain": domain,
                "unique_id": unique_id,
                "results_path": results_path,
                "results": results,  # Guardamos los resultados originales
                "suggestions": suggestions_json,  # Guardamos las sugerencias de OpenAI en JSON
                "date": datetime.now().isoformat()
            }

            # Insertar el registro en MongoDB
            inserted_id = mongo_service.insert_result(result_record)

            # Agregar el resultado al resumen
            return {
                "url": url,
                "unique_id": unique_id,
                "_id": str(inserted_id),
                "date": result_record["date"],
                "suggestions": suggestions_json  # Añadir las sugerencias al resultado
            }

        except Exception as e:
            return {"url": url, "error": str(e)}

    # Procesar URLs en paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_url, url) for url in urls]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results_summary.append(result)

    return jsonify({
        "status": "success",
        "message": "Análisis completado",
        "data": results_summary
    }), 200

# Nuevo Endpoint: Obtener el histórico de todas las páginas analizadas
@app.route('/history', methods=['GET'])
def get_history():
    """
       Obtener el histórico de todas las páginas analizadas.
       ---
       responses:
         200:
           description: Lista de todas las páginas analizadas.
           schema:
             type: object
             properties:
               status:
                 type: string
                 example: success
               data:
                 type: array
                 items:
                   type: object
                   properties:
                     _id:
                       type: string
                       example: "60c72b2f9e7b4a001c8e4e9b"
                     url:
                       type: string
                       example: "https://ejemplo.com"
                     domain:
                       type: string
                       example: "ejemplo.com"
                     date:
                       type: string
                       example: "2023-08-01"
         500:
           description: Error al obtener el historial.
           schema:
             type: object
             properties:
               status:
                 type: string
                 example: error
               message:
                 type: string
                 example: "Error al obtener el historial"
       """
    try:
        # Obtener todos los documentos de la colección
        records = mongo_service.get_all_records()
        history = []

        for record in records:
            # Usar el campo 'date' si está presente, de lo contrario manejar la ausencia
            date = record.get('date', 'Fecha no disponible')

            history.append({
                "_id": str(record['_id']),
                "url": record.get('url', 'URL no disponible'),
                "domain": record.get('domain', 'Desconocido'),
                "date": date
            })

        return jsonify({
            "status": "success",
            "data": history
        }), 200
    except Exception as e:
        print(f"Error al obtener el historial: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Este endpoint permitirá obtener todos los detalles de un análisis específico al proporcionar su id.
@app.route('/history/<string:record_id>', methods=['GET'])
def get_analysis_detail(record_id):
    """
      Obtener detalles de un análisis específico.
      ---
      parameters:
        - name: record_id
          in: path
          type: string
          required: true
          description: ID del registro a consultar
      responses:
        200:
          description: Detalles del análisis encontrado
          schema:
            type: object
            properties:
              status:
                type: string
                example: success
              data:
                type: object
                properties:
                  _id:
                    type: string
                    example: "60c72b2f9e7b4a001c8e4e9b"
                  url:
                    type: string
                    example: "https://ejemplo.com"
                  domain:
                    type: string
                    example: "ejemplo.com"
                  date:
                    type: string
                    example: "2023-08-01"
                  # Añade aquí cualquier otro campo relevante en el análisis
        404:
          description: Registro no encontrado
          schema:
            type: object
            properties:
              status:
                type: string
                example: error
              message:
                type: string
                example: "Registro no encontrado"
        500:
          description: Error al obtener los detalles del análisis
          schema:
            type: object
            properties:
              status:
                type: string
                example: error
              message:
                type: string
                example: "Error al obtener el detalle del análisis"
      """
    try:
        # Buscar el documento por su _id
        record = mongo_service.get_record_by_id(record_id)
        if not record:
            return jsonify({"status": "error", "message": "Registro no encontrado"}), 404

        # Convertir ObjectId a string para ser serializado en JSON
        record['_id'] = str(record['_id'])

        return jsonify({
            "status": "success",
            "data": record
        }), 200
    except Exception as e:
        print(f"Error al obtener el detalle del análisis: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Este endpoint permitirá obtener todas las URLs y análisis realizados para un dominio específico.
@app.route('/history/domain/<string:domain>', methods=['GET'])
def get_domain_history(domain):
    """
    Obtener todas las URLs y análisis realizados para un dominio específico.
    ---
    parameters:
      - name: domain
        in: path
        type: string
        required: true
        description: El dominio para el cual se desean obtener los registros
    responses:
      200:
        description: Lista de todos los análisis realizados para el dominio especificado.
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: array
              items:
                type: object
                properties:
                  _id:
                    type: string
                    example: "60c72b2f9e7b4a001c8e4e9b"
                  url:
                    type: string
                    example: "https://ejemplo.com"
                  domain:
                    type: string
                    example: "ejemplo.com"
                  date:
                    type: string
                    example: "2023-08-01"
      500:
        description: Error al obtener el historial del dominio
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            message:
              type: string
              example: "Error al obtener el historial del dominio"
    """
    try:
        # Buscar todos los registros que coincidan con el dominio
        records = mongo_service.get_records_by_domain(domain)
        history = []
        for record in records:
            history.append({
                "_id": str(record['_id']),
                "url": record.get('url', 'URL no disponible'),
                "domain": record.get('domain', 'Desconocido'),
                "date": record.get('date', 'Fecha no disponible')
            })
        return jsonify({
            "status": "success",
            "data": history
        }), 200
    except Exception as e:
        print(f"Error al obtener el historial del dominio: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True)
