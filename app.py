from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta_patron_bacheo_2026'

CARPETA_FOTOS = 'static/uploads'
os.makedirs(CARPETA_FOTOS, exist_ok=True)
app.config['CARPETA_FOTOS'] = CARPETA_FOTOS

baches_registrados = []
cuadrillas_activas = {}

# --- FUNCIÓN PARA CREAR LAS TABLAS AUTOMÁTICAMENTE ---
def inicializar_bd():
    conexion = sqlite3.connect('usuarios.db')
    cursor = conexion.cursor()
    
    # Tabla de usuarios con su columna foto_perfil incluida
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_jefe TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            foto_perfil TEXT
        )
    """)
    
    # Tabla de administradores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # Creamos un usuario de prueba por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        pass_hash = generate_password_hash("1234")
        cursor.execute("INSERT INTO usuarios (nombre_jefe, password, foto_perfil) VALUES (?, ?, ?)", 
                       ("Cuadrilla 1", pass_hash, "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"))
    
    # Creamos un admin por defecto si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM admins")
    if cursor.fetchone()[0] == 0:
        admin_pass_hash = generate_password_hash("admin123")
        cursor.execute("INSERT INTO admins (usuario, password) VALUES (?, ?)", ("admin", admin_pass_hash))
        
    conexion.commit()
    conexion.close()

# Ejecutamos la inicialización al arrancar
inicializar_bd()

@app.route('/')
def login():
    terminos = request.cookies.get('terminos_aceptados')
    if not terminos:
        return redirect(url_for('terminos'))
        
    return render_template('login.html')

@app.route('/terminos')
def terminos():
    return render_template('terminos.html')

@app.route('/aceptar_terminos', methods=['POST'])
def aceptar_terminos():
    respuesta = redirect(url_for('login'))
    respuesta.set_cookie('terminos_aceptados', 'true', max_age=60*60*24*365)
    return respuesta

@app.route('/login', methods=['POST'])
def hacer_login():
    nombre_jefe = request.form.get('nombre').strip()
    password_ingresada = request.form.get('codigo')
    
    conexion = sqlite3.connect('usuarios.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre_jefe, password, foto_perfil FROM usuarios WHERE nombre_jefe = ? COLLATE NOCASE", (nombre_jefe,))
    resultado = cursor.fetchone()
    conexion.close()
    
    if resultado and check_password_hash(resultado[1], password_ingresada):
        session['autenticado'] = True
        session['nombre_operador'] = resultado[0]
        
        avatar_bd = resultado[2]
        session['foto_perfil'] = avatar_bd if avatar_bd else "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
        
        return redirect(url_for('vista_cuadrilla'))
        
    return render_template('login.html', error="Nombre o contraseña incorrectos 🚫")

@app.route('/admin')
def admin_login_page():
    return render_template('login_admin.html')

@app.route('/login_admin', methods=['POST'])
def login_admin():
    usuario = request.form.get('usuario', '').strip()
    codigo_admin = request.form.get('codigo_admin', '')
    
    conexion = sqlite3.connect('usuarios.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT usuario, password FROM admins WHERE usuario = ? COLLATE NOCASE", (usuario,))
    resultado = cursor.fetchone()
    conexion.close()
    
    if resultado and check_password_hash(resultado[1], codigo_admin):
        session['admin_auth'] = True
        session['admin_user'] = resultado[0]
        return redirect(url_for('vista_monitoreo'))
        
    return render_template('login_admin.html', error="Usuario o contraseña incorrectos 🚫")

@app.route('/actualizar_perfil', methods=['POST'])
def actualizar_perfil():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
        
    nombre_actual = session.get('nombre_operador')
    nuevo_nombre = request.form.get('nombre_operador', '').strip()
    foto_perfil = request.files.get('foto_perfil')
    
    ruta_final_foto = session.get('foto_perfil')
    
    if foto_perfil and foto_perfil.filename != '':
        filename = f"perfil_{foto_perfil.filename}"
        path_guardado = os.path.join(app.config['CARPETA_FOTOS'], filename)
        foto_perfil.save(path_guardado)
        ruta_final_foto = f"/{path_guardado}"
        
    conexion = sqlite3.connect('usuarios.db')
    cursor = conexion.cursor()
    cursor.execute("""
        UPDATE usuarios 
        SET nombre_jefe = ?, foto_perfil = ? 
        WHERE nombre_jefe = ?
    """, (nuevo_nombre, ruta_final_foto, nombre_actual))
    conexion.commit()
    conexion.close()
    
    session['nombre_operador'] = nuevo_nombre
    session['foto_perfil'] = ruta_final_foto
        
    return redirect(url_for('vista_cuadrilla'))

@app.route('/cuadrilla')
def vista_cuadrilla():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    nombre = session.get('nombre_operador', 'Cuadrilla de Campo')
    avatar = session.get('foto_perfil', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150')
    
    baches_hoy = [b for b in baches_registrados if b.get('cuadrilla') == nombre]
    
    return render_template('cuadrilla.html', nombre=nombre, avatar=avatar, total_hoy=len(baches_hoy), historial=baches_registrados)

@app.route('/actualizar_posicion', methods=['POST'])
def actualizar_posicion():
    if not session.get('autenticado'):
        return jsonify({"status": "error", "message": "No autenticado"}), 403
        
    nombre_cuadrilla = session.get('nombre_operador', 'Cuadrilla')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    
    if lat and lng:
        cuadrillas_activas[nombre_cuadrilla] = {
            "lat": float(lat),
            "lng": float(lng),
            "estado": "En Ruta (GPS Real)",
            "operador": nombre_cuadrilla
        }
    return jsonify({"status": "ok"})

@app.route('/guardar_bache', methods=['POST'])
def guardar_bache():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
        
    nombre_cuadrilla = session.get('nombre_operador', 'Cuadrilla de Campo')
    folio = request.form.get('folio')
    calle = request.form.get('calle')
    colonia = request.form.get('colonia')
    lat = request.form.get('lat')
    lng = request.form.get('lng')
    
    estado_trabajo = request.form.get('estado_trabajo', 'Quedó pendiente')
    detalle_estatus = request.form.get('detalle_estatus', 'Sin detalles adicionales')
    
    if estado_trabajo == 'Trabajo Concluido':
        detalle_estatus = 'Trabajo totalmente finalizado'

    foto = request.files.get('foto')
    ruta_imagen = "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=300"
    
    if foto and foto.filename != '':
        filename = foto.filename
        path_guardado = os.path.join(app.config['CARPETA_FOTOS'], filename)
        foto.save(path_guardado)
        ruta_imagen = f"/{path_guardado}"
    
    if folio and calle and colonia and lat and lng:
        link_maps = f"https://www.google.com/maps?q={lat},{lng}"
        fecha_actual = datetime.now().strftime('%d/%m/%Y')
        fecha_iso = datetime.now().strftime('%Y-%m-%d')
        
        existente = next((b for b in baches_registrados if b['folio'] == folio), None)
        
        if existente:
            existente['calle'] = calle
            existente['colonia'] = colonia
            existente['lat'] = float(lat)
            existente['lng'] = float(lng)
            existente['estado_trabajo'] = estado_trabajo
            existente['detalle_estatus'] = detalle_estatus
            existente['cuadrilla'] = nombre_cuadrilla
            existente['link_maps'] = link_maps
            if foto and foto.filename != '':
                existente['imagen'] = ruta_imagen
            mensaje_alerta = f"¡Folio #{folio} actualizado ({estado_trabajo})! 🔄"
        else:
            nuevo = {
                "folio": folio,
                "calle": calle,
                "colonia": colonia,
                "lat": float(lat),
                "lng": float(lng),
                "estado_trabajo": estado_trabajo,
                "detalle_estatus": detalle_estatus,
                "cuadrilla": nombre_cuadrilla,
                "imagen": ruta_imagen,
                "link_maps": link_maps,
                "fecha": fecha_actual,
                "fecha_iso": fecha_iso
            }
            baches_registrados.append(nuevo)
            mensaje_alerta = f"¡Folio #{folio} registrado como '{estado_trabajo}' por {nombre_cuadrilla}! ✅"
        
    nombre = session.get('nombre_operador', 'Operador de Campo')
    avatar = session.get('foto_perfil', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150')
    baches_hoy = [b for b in baches_registrados if b.get('cuadrilla') == nombre]
    
    return render_template('cuadrilla.html', nombre=nombre, avatar=avatar, total_hoy=len(baches_hoy), historial=baches_registrados, mensaje=mensaje_alerta)

@app.route('/logout')
def logout():
    nombre_cuadrilla = session.get('nombre_operador')
    if nombre_cuadrilla and nombre_cuadrilla in cuadrillas_activas:
        del cuadrillas_activas[nombre_cuadrilla]
    session.clear()
    return redirect(url_for('login'))

@app.route('/logout_admin')
def logout_admin():
    session.pop('admin_auth', None)
    session.pop('admin_user', None)
    return redirect(url_for('admin_login_page'))

@app.route('/monitoreo')
def vista_monitoreo():
    if not session.get('admin_auth'):
        return redirect(url_for('admin_login_page'))
    return render_template('monitoreo.html')

@app.route('/api/estado_en_vivo')
def api_estado_en_vivo():
    return jsonify({
        "cuadrillas": cuadrillas_activas,
        "baches": baches_registrados
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)