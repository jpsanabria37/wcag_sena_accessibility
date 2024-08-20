import requests
import pymongo

# Configuración de MongoDB
mongo_uri = "mongodb://localhost:27017/"  # Reemplaza con tu URI de MongoDB si es diferente
client = pymongo.MongoClient(mongo_uri)
db = client["accessibility_db"]  # Reemplaza con el nombre de tu base de datos
collection = db["wave_analysis"]

# URL de la API de WAVE
wave_api_url = "https://wave.webaim.org/api/request"
api_key = "n8Dnhrpn4006"  # Reemplaza con tu clave de API de WAVE
page_url = "https://www.google.com/"  # Reemplaza con la URL de la página que quieres analizar

# Hacer la solicitud a la API de WAVE
response = requests.post(wave_api_url, data={'url': page_url, 'key': api_key})
if response.status_code == 200:
    wave_results = response.json()
    print("Resultados de WAVE obtenidos.")
else:
    print(f"Error en la solicitud a WAVE: {response.status_code}")
    print(response.text)
    exit()

# Insertar los datos de WAVE en la colección de MongoDB
result = collection.insert_one(wave_results)
print(f"Datos de WAVE insertados con el ID: {result.inserted_id}")
