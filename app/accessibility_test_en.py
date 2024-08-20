from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from axe_selenium_python import Axe
from pymongo import MongoClient
from urllib.parse import urlparse
import google.auth
from google.cloud import aiplatform
import os
import uuid
import openai
import json

# Configurar la clave API de OpenAI
openai.api_key = 'sk-proj-DJI0Z0ZaSpI4MdDC7oinT3BlbkFJbK33jK0yIk5MCre28Fon'

# Configurar Flask
app = Flask(__name__)

# Configurar MongoDB
client = MongoClient('mongodb://localhost:27017/')  # Cambia la URI si usas MongoDB Atlas
db = client.accessibility_db
collection = db.reports

# Ruta al ChromeDriver
driver_path = './drivers/chromedriver.exe'  # Asegúrate de tener el ChromeDriver en esta ruta

# Configurar Google Vertex AI
google_credentials, _ = google.auth.default()
aiplatform.init(project="editorial-migration", location="us-central1")
def translate_results(results):
    try:
        results_json = json.dumps(results)
        prompt = f"Traduce el siguiente texto JSON al español:\n\n{results_json}"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048
        )
        translated_json = response.choices[0].message['content'].strip()
        translated_results = json.loads(translated_json)
        return translated_results
    except Exception as e:
        print(f"Error translating results: {e}")
        return results  # Return the original results if there's an error

def translate_violations(violations):
    try:
        # Convertir las violaciones a JSON
        violations_json = json.dumps(violations)
        prompt = f"Traduce el siguiente texto JSON al español:\n\n{violations_json[:2000]}"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500
        )
        translated_json = response.choices[0].message['content'].strip()
        translated_violations = json.loads(translated_json)
        return translated_violations
    except Exception as e:
        print(f"Error translating violations: {e}")
        return violations

def translate_text_with_vertex(text):
    try:
        model = aiplatform.TextGenerationModel.from_pretrained("projects/editorial-migration/locations/us-central1/models/gemini-1.5-flash-001")
        response = model.predict(text)
        return response.text
    except Exception as e:
        print(f"Error translating text with Vertex AI: {e}")
        return text  # Return the original text if there's an error
def translate_violations(violations):
    try:
        violations_json = json.dumps(violations)
        prompt = f"Traduce el siguiente texto JSON al español:\n\n{violations_json[:2000]}"

        translated_json = translate_text_with_vertex(prompt)
        translated_violations = json.loads(translated_json)
        return translated_violations
    except Exception as e:
        print(f"Error translating violations: {e}")
        return violations



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

            # Inicializar Axe
            axe = Axe(driver)

            # Inyectar Axe en la página web
            axe.inject()

            # Ejecutar el análisis de accesibilidad
            results = axe.run()

            # Obtener el dominio de la URL para el nombre del archivo
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Generar un nombre de archivo único basado en el dominio y un UUID
            unique_id = str(uuid.uuid4())
            filename = f"{domain}_{unique_id}_accessibility_results.json"
            results_path = os.path.join('./results', filename)  # Carpeta 'results' debe existir
            #axe.write_results(results, results_path)


            # Traducir solo las violaciones
            violations = results.get('violations', [])
            translated_violations = translate_violations(violations)

            translated_results = translate_results(results)
            #guardar los resultados en mongo
            result_record = {
                "url": url,
                "domain": domain,
                "unique_id": unique_id,
                "results_path": results_path,
                "results":  {
                    **translated_results,
                    "violations": translated_violations
                },
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
