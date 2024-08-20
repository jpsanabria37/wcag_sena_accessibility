from flask import Flask, request, jsonify
from selenium_service import SeleniumService
from db_service import MongoService
from datetime import datetime
import os
import concurrent.futures
import threading

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


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    urls = data.get('urls')

    if not urls or not isinstance(urls, list):
        return jsonify({"status": "error", "message": "URLs should be a list"}), 400

    results_summary = []

    def process_url(url):
        try:
            results, domain, unique_id, results_path = selenium_service.analyze_url(url)

            # Guardar los resultados en MongoDB
            result_record = {
                "url": url,
                "domain": domain,
                "unique_id": unique_id,
                "results_path": results_path,
                "results": results,
                "date": datetime.now().isoformat()
            }
            inserted_id = mongo_service.insert_result(result_record)

            # Agregar resultado al resumen
            return {
                "url": url,
                "unique_id": unique_id,
                "_id": str(inserted_id),
                "results_file": results_path,
                "date": result_record["date"]
            }
        except Exception as e:
            return {"url": url, "error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_url, url) for url in urls]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results_summary.append(result)

    return jsonify({
        "status": "success",
        "message": "Analysis completed",
        "data": results_summary
    }), 200


if __name__ == '__main__':
    app.run(debug=True)
