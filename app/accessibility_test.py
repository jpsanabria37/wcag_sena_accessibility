from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from pymongo import MongoClient
from urllib.parse import urlparse
import os
import uuid
import json

# Configurar Flask
app = Flask(__name__)

# Configurar MongoDB
client = MongoClient('mongodb://localhost:27017/')  # Cambia la URI si usas MongoDB Atlas
db = client.accessibility_db
collection = db.reports_es

# Ruta al ChromeDriver
driver_path = './drivers/chromedriver.exe'  # Asegúrate de tener el ChromeDriver en esta ruta

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    urls = data.get('urls')

    if not urls:
        return jsonify({
            "status": "error",
            "message": "URLs are required"
        }), 400

    if not isinstance(urls, list):
        return jsonify({
            "status": "error",
            "message": "URLs should be a list"
        }), 400

    results_summary = []

    # Configurar opciones de Chrome para el modo headless
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    # Crear una instancia del Service con la ruta al ChromeDriver
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        for url in urls:
            # Abrir la página web
            driver.get(url)

            # Inyectar Axe en la página web
            with open('axe-core-setup.js', 'r') as file:
                axe_script = file.read()

            driver.execute_script(axe_script)

            # Ejecutar el análisis de accesibilidad
            results = driver.execute_async_script("""
                const callback = arguments[arguments.length - 1];
                axe.run().then(results => {
                    callback(results);
                });
            """)

            # Obtener el dominio de la URL para el nombre del archivo
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Generar un nombre de archivo único basado en el dominio y un UUID
            unique_id = str(uuid.uuid4())
            filename = f"{domain}_{unique_id}_accessibility_results.json"
            results_path = os.path.join('./results', filename)  # Carpeta 'results' debe existir

            # Guardar los resultados en MongoDB
            result_record = {
                "url": url,
                "domain": domain,
                "unique_id": unique_id,
                "results_path": results_path,
                "results": results,
                "date": datetime.now().isoformat()  # Añadir la fecha
            }

            # Insertar el registro en MongoDB
            inserted_id = collection.insert_one(result_record).inserted_id

            # Agregar resultado al resumen
            results_summary.append({
                "url": url,
                "unique_id": unique_id,
                "_id": str(inserted_id),
                "results_file": results_path,
                "date": result_record["date"]  # Añadir la fecha al resumen
            })

        # Cerrar el navegador
        driver.quit()

        return jsonify({
            "status": "success",
            "message": "Analysis successful",
            "data": results_summary
        }), 200

    except Exception as e:
        driver.quit()
        return jsonify({
            "status": "error",
            "message": "An error occurred during the analysis",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
