import sqlite3
from werkzeug.security import generate_password_hash

def crear_nuevo_usuario(nombre, password_plana):
    conexion = sqlite3.connect('usuarios.db')
    cursor = conexion.cursor()
    
    # Crear la tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_jefe TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    password_cifrada = generate_password_hash(password_plana)
    
    try:
        cursor.execute("INSERT INTO usuarios (nombre_jefe, password) VALUES (?, ?)", (nombre, password_cifrada))
        conexion.commit()
        print(f"Usuario '{nombre}' creado con éxito.")
    except sqlite3.IntegrityError:
        print("El usuario ya existe.")
        
    conexion.close()

if __name__ == '__main__':
    # Aquí puedes cambiar el nombre y la contraseña que les darás a tus trabajadores
    crear_nuevo_usuario("Juan Carlos", "PasswordSegura123")
    crear_nuevo_usuario("cuadrilla",  "lopez2026")