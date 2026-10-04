import sqlite3
from werkzeug.security import generate_password_hash

def crear_nuevo_admin(usuario, password_plana):
    conexion = sqlite3.connect('usuarios.db')
    cursor = conexion.cursor()
    
    # Crear la tabla de administradores si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    password_cifrada = generate_password_hash(password_plana)
    
    try:
        cursor.execute("INSERT INTO admins (usuario, password) VALUES (?, ?)", (usuario, password_cifrada))
        conexion.commit()
        print(f"¡Administrador '{usuario}' creado con éxito!")
    except sqlite3.IntegrityError:
        print(f"El administrador '{usuario}' ya existe en la base de datos.")
    finally:
        conexion.close()

if __name__ == '__main__':
    # Aquí puedes agregar los administradores que quieras
    crear_nuevo_admin("Diego Funez", "admindiego2026")
    