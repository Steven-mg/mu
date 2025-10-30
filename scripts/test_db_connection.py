import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

from sqlalchemy import text
from config import app, db

def main():
    uri = os.getenv('DATABASE_URI')
    print(f"DATABASE_URI: {uri}")
    try:
        with app.app_context():
            with db.engine.connect() as conn:
                dbname = conn.execute(text('SELECT DATABASE()')).scalar()
                version = conn.execute(text('SELECT VERSION()')).scalar()
                tables = conn.execute(text('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()')).scalar()
                print(f"Conectado a BD: {dbname}")
                print(f"Servidor MySQL versión: {version}")
                print(f"Total de tablas en el esquema: {tables}")
                # Verificación explícita del esquema esperado
                esperado = 'f58_steven'
                print(f"Esquema esperado: {esperado}")
                if dbname == esperado:
                    print("STATUS: OK -> Conexión válida al esquema esperado.")
                else:
                    print("STATUS: WARNING -> Conectado pero el esquema no coincide.")
    except Exception as e:
        print("STATUS: ERROR -> Falló la conexión a la base de datos.")
        print(f"Detalle: {e}")

if __name__ == '__main__':
    main()