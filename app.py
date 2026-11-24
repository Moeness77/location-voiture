import os, time
import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"), user=os.getenv("DB_USER", "demo"),
        password=os.getenv("DB_PASSWORD", "demopass"), dbname=os.getenv("DB_NAME", "demodb"))

def query(sql, params=(), fetch=False):
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch:
                return cur.fetchall()
    finally:
        conn.close()

def init_db():
    for _ in range(15):
        try:
            query("""CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY, brand TEXT NOT NULL, model TEXT NOT NULL,
                price_per_day DOUBLE PRECISION NOT NULL, available BOOLEAN DEFAULT TRUE)""")
            query("""CREATE TABLE IF NOT EXISTS rentals (
                id SERIAL PRIMARY KEY, car_id INT REFERENCES cars(id),
                customer TEXT NOT NULL, start_date DATE DEFAULT CURRENT_DATE,
                returned BOOLEAN DEFAULT FALSE)""")
            return
        except psycopg2.OperationalError:
            time.sleep(2)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/cars", methods=["GET"])
def list_cars():
    rows = query("SELECT id, brand, model, price_per_day, available FROM cars ORDER BY id", fetch=True)
    return jsonify([dict(zip(["id", "brand", "model", "price_per_day", "available"], r)) for r in rows])

@app.route("/cars", methods=["POST"])
def add_car():
    d = request.get_json()
    query("INSERT INTO cars (brand, model, price_per_day) VALUES (%s,%s,%s)",
          (d["brand"], d["model"], d["price_per_day"]))
    return jsonify({"message": "voiture ajoutée"}), 201

@app.route("/rentals", methods=["POST"])
def rent():
    d = request.get_json()
    rows = query("SELECT available FROM cars WHERE id=%s", (d["car_id"],), fetch=True)
    if not rows or not rows[0][0]:
        return jsonify({"error": "voiture indisponible"}), 400
    query("INSERT INTO rentals (car_id, customer) VALUES (%s,%s)", (d["car_id"], d["customer"]))
    query("UPDATE cars SET available=FALSE WHERE id=%s", (d["car_id"],))
    return jsonify({"message": "location enregistrée"}), 201

@app.route("/rentals/<int:rental_id>/return", methods=["POST"])
def give_back(rental_id):
    rows = query("SELECT car_id FROM rentals WHERE id=%s AND returned=FALSE", (rental_id,), fetch=True)
    if not rows:
        return jsonify({"error": "location introuvable"}), 404
    query("UPDATE rentals SET returned=TRUE WHERE id=%s", (rental_id,))
    query("UPDATE cars SET available=TRUE WHERE id=%s", (rows[0][0],))
    return jsonify({"message": "voiture rendue"})

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Location Voiture</title>
<style>body{font-family:sans-serif;max-width:720px;margin:40px auto}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ccc;padding:8px;text-align:left}input{margin:4px}</style></head><body>
<h1>Agence de location de voitures</h1>
<h3>Ajouter une voiture</h3>
<input id="brand" placeholder="Marque"><input id="model" placeholder="Modèle"><input id="price" type="number" placeholder="Prix par jour">
<button onclick="addCar()">Ajouter</button>
<h3>Voitures</h3>
<table><thead><tr><th>ID</th><th>Marque</th><th>Modèle</th><th>Prix/jour</th><th>Disponible</th><th></th></tr></thead><tbody id="cars"></tbody></table>
<script>
async function load(){const r=await fetch('/cars');const cars=await r.json();
document.getElementById('cars').innerHTML=cars.map(c=>'<tr><td>'+c.id+'</td><td>'+c.brand+'</td><td>'+c.model+'</td><td>'+c.price_per_day+'</td><td>'+(c.available?'Oui':'Non')+'</td><td>'+(c.available?'<button onclick="rent('+c.id+')">Louer</button>':'')+'</td></tr>').join('');}
async function addCar(){await fetch('/cars',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brand:brand.value,model:model.value,price_per_day:Number(price.value)})});load();}
async function rent(id){const n=prompt('Nom du client ?');if(!n)return;await fetch('/rentals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({car_id:id,customer:n})});load();}
load();
</script></body></html>"""

@app.route("/")
def home():
    return PAGE

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=3000)
