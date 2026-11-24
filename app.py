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

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=3000)
