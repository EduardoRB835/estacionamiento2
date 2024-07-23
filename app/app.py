from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from flask_wtf.csrf import CSRFProtect
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'mysecretkey'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000 
csrf = CSRFProtect(app)

# Configuración para MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'estacionamiento'

# Función para conectar a la base de datos MySQL
def get_db_connection():
    conn = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/carro')
def carro():
    if 'logged_in' in session:
        nombre = session['nombre']
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Consulta para obtener los carros registrados
            cursor.execute('SELECT * FROM carros')
            carros = cursor.fetchall()

            # Verificar si el usuario es administrador
            cursor.execute('SELECT * FROM admin WHERE nombre = %s', (nombre,))
            admin_user = cursor.fetchone()

            es_admin = admin_user is not None
            
        except Exception as e:
            print(f"Error al obtener los carros: {str(e)}")
            flash('Error al obtener los carros', 'error')
            return redirect(url_for('index'))
        
        finally:
            conn.close()

        return render_template('carros.html', nombre=nombre, carros=carros, es_admin=es_admin)
    else:
        return redirect(url_for('login'))

    

@app.route('/registro_autos', methods=['GET', 'POST'])
def registro_autos():
    if 'logged_in' in session:
        if request.method == 'POST':
            placa = request.form['placa']
            marca = request.form['marca']
            modelo = request.form['modelo']
            color = request.form['color']
            propietario = request.form['propietario']
            precio_pagado = request.form['precio_pagado']
            descripcion = request.form['descripcion']
            
            if 'status_pago' in request.form:
                status_pago = 'Pendiente'
            else:
                status_pago = 'Pagado'

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute('INSERT INTO carros (placa, marca, modelo, color, propietario, precio_pagado, status_pago, descripcion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                               (placa, marca, modelo, color, propietario, precio_pagado, status_pago, descripcion))
                conn.commit()
                flash('Se ha registrado el auto correctamente.', 'success')
                return redirect(url_for('registro_autos'))
            except Exception as e:
                conn.rollback()
                flash(f'Error al registrar el auto: {str(e)}', 'error')
            finally:
                conn.close()

        return render_template('registro_auto.html')
    else:
        return redirect(url_for('login'))

    

@app.route('/registro_empleados', methods=['GET', 'POST'])
def registro_empleados():
    if 'logged_in' in session:
        if request.method == 'POST':
            nombre = request.form['nombre']
            correo = request.form['correo']
            contrasena = request.form['contrasena']
            
            # Conectar a la base de datos
            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                # Insertar el nuevo empleado en la tabla de empleados
                cursor.execute('INSERT INTO empleados (nombre, correo, contrasena) VALUES (%s, %s, %s)',
                               (nombre, correo, contrasena))
                
                # Confirmar la transacción
                conn.commit()
                
                flash('Se ha registrado el empleado correctamente.', 'success')
                return redirect(url_for('registro_empleados'))

            except Exception as e:
                conn.rollback()
                flash(f'Error al registrar el empleado: {str(e)}', 'error')
            
            finally:
                conn.close()

        return render_template('reg_empleados.html')
    else:
        return redirect(url_for('login'))


@app.route('/empleados')
def empleado():
    return render_template('empleados.html')


@app.route('/cartera')
def cartera():
    if 'logged_in' in session:
        nombre = session['nombre']  # Obtén el nombre de usuario de la sesión
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Consulta para obtener todos los carros registrados que no han sido cortados
            cursor.execute('SELECT * FROM carros WHERE cortado = 0')
            carros = cursor.fetchall()
            
            # Calcular el total acumulado de los precios pagados
            total_acumulado = sum(float(carro['precio_pagado']) for carro in carros)
            
        except Exception as e:
            # Manejar el error adecuadamente (por ejemplo, loguearlo)
            print(f"Error al procesar carros: {str(e)}")
            flash('Error al procesar los carros', 'error')
            return redirect(url_for('login'))
        
        finally:
            conn.close()

        return render_template('cartera.html', nombre=nombre, carros=carros, total_acumulado=total_acumulado)
    else:
        return redirect(url_for('login'))


@app.route('/admin')
def admin():
    if 'logged_in' in session:
        nombre = session['nombre']  # Obtén el nombre de usuario de la sesión
        
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Ejecutar la consulta para obtener los carros registrados
        cursor.execute('SELECT * FROM carros')
        carros = cursor.fetchall()
        
        conn.close()

        return render_template('administrador.html', nombre=nombre, carros=carros)
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contraseña']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Buscar en la tabla de administradores
        cursor.execute('SELECT * FROM admin WHERE correo = %s AND contrasena = %s', (correo, contrasena))
        admin_user = cursor.fetchone()

        # Si el usuario es administrador
        if admin_user:
            session['logged_in'] = True
            session['nombre'] = admin_user['nombre']  # Guarda el nombre en la sesión
            conn.close()
            return redirect(url_for('admin'))

        # Buscar en la tabla de empleados
        cursor.execute('SELECT * FROM empleados WHERE correo = %s AND contrasena = %s', (correo, contrasena))
        empleado_user = cursor.fetchone()

        # Si el usuario es empleado
        if empleado_user:
            session['logged_in'] = True
            session['nombre'] = empleado_user['nombre']  # Guarda el nombre en la sesión
            conn.close()
            return redirect(url_for('registro_autos'))

        # Si no se encuentra ningún usuario
        conn.close()
        error = 'Usuario o contraseña incorrectos'
        return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/hacer_corte', methods=['POST'])
def hacer_corte():
    if 'logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            fecha_corte = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Obtener el total del corte
            cursor.execute('SELECT SUM(precio_pagado) as total FROM carros WHERE status_pago = "Pagado" AND cortado = 0')
            total_corte = cursor.fetchone()['total']

            if total_corte is None:
                total_corte = 0.00

            print(f"Fecha del corte: {fecha_corte}, Total del corte: {total_corte}")

            # Insertar el nuevo corte en la tabla cortes_caja
            cursor.execute('INSERT INTO cortes_caja (total, fecha_corte) VALUES (%s, %s)', (total_corte, fecha_corte))

            # Actualizar el estado de los carros
            cursor.execute('UPDATE carros SET cortado = 1 WHERE status_pago = "Pagado" AND cortado = 0')

            # Confirmar la transacción
            conn.commit()

            print("Actualización de carros realizada correctamente.")
            flash('Corte de caja realizado correctamente.', 'success')
            return redirect(url_for('cartera'))

        except Exception as e:
            conn.rollback()
            print(f"Error al realizar el corte de caja: {str(e)}")
            flash(f'Error al realizar el corte de caja: {str(e)}', 'error')
            return redirect(url_for('cartera'))

        finally:
            conn.close()
    else:
        return redirect(url_for('login'))


@app.route('/ver_cortes')
def ver_cortes():
    if 'logged_in' in session:
        # Conectar a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener todos los cortes de caja realizados
        cursor.execute('SELECT * FROM cortes_caja')
        cortes = cursor.fetchall()
        
        # Calcular el total de todos los cortes
        total_cortes = sum(corte['total'] for corte in cortes)
        
        conn.close()

        return render_template('ver_cortes.html', cortes=cortes, total_cortes=total_cortes)
    else:
        return redirect(url_for('login'))
    

@app.route('/editar_pago/<int:carro_id>', methods=['GET', 'POST'])
def editar_pago(carro_id):
    if 'logged_in' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'POST':
            nuevo_status = request.form['status_pago']
            try:
                cursor.execute('UPDATE carros SET status_pago = %s WHERE id = %s', (nuevo_status, carro_id))
                conn.commit()
                flash('El estado de pago ha sido actualizado.', 'success')
                return redirect(url_for('carro'))
            except Exception as e:
                conn.rollback()
                flash(f'Error al actualizar el estado de pago: {str(e)}', 'error')
            finally:
                conn.close()
        
        try:
            cursor.execute('SELECT * FROM carros WHERE id = %s', (carro_id,))
            carro = cursor.fetchone()
        except Exception as e:
            flash(f'Error al obtener los datos del carro: {str(e)}', 'error')
            return redirect(url_for('carro'))
        finally:
            conn.close()

        return render_template('editar_pago.html', carro=carro)
    else:
        return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(debug=True)