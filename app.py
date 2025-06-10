"""
Aplicación Flask que simula un carrito de compras con integración de pago mediante Mercado Pago.

Esta aplicación permite a los usuarios:
- Ver una lista de productos
- Agregar productos a un carrito almacenado en sesión
- Ver el contenido del carrito
- Realizar el pago usando la pasarela de Mercado Pago

Requerimientos:
- Flask
- Mercado Pago SDK
"""

from flask import Flask, render_template, request, redirect, url_for, session
import mercadopago
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

#from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Reemplazar con una clave segura en producción

# Inicializar el SDK de Mercado Pago con el token de acceso
# Token de prueba de Mercado Pago (modo sandbox)
acceso = "APP_USR-218618312072752-060915-538210917ad09d14afd2bd92534d7ce2-1401112199"

from functools import wraps
from flask import flash

def requiere_signup(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('signup_completado'):
            return redirect(url_for('signup'))
        return f(*args, **kwargs)
    return decorated_function

# Catálogo de productos de ejemplo (en una app real vendría de una base de datos)
PRODUCTOS = [
    {"id": 1, "nombre": "Zapatillas", "precio": 23400.00},
    {"id": 2, "nombre": "Harina", "precio": 1500.00},
    {"id": 3, "nombre": "Pepe", "precio": 1.00},
]

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Página de registro de usuario. Guarda el email y contraseña en sesión y marca signup completado.
    Nota: La contraseña debe ser hasheada en producción.
    """
    if request.method == 'POST':
        import re
        email = request.form.get('email')
        password = request.form.get('password')
        if email and password:
            # Validar complejidad de la contraseña
            if (len(password) >= 8 and
                re.search(r'[A-Z]', password) and
                re.search(r'[0-9]', password) and
                re.search(r'[\W_]', password)):
                # Aquí se debería hashear la contraseña antes de guardar (no implementado)
                session['signup_completado'] = True
                session['email_usuario'] = email
                session['password_usuario'] = password  # Guardar contraseña en sesión (sin hash, solo demo)
                return redirect(url_for('inicio'))
            else:
                error_msg = ("La contraseña debe tener al menos 8 caracteres, "
                             "una mayúscula, un número y un carácter especial.")
                return render_template('signup.html', error=error_msg)
        else:
            return render_template('signup.html', error="Por favor ingrese email y contraseña válidos.")
    return render_template('signup.html')

@app.route('/')
@requiere_signup
def inicio():
    """
    Muestra la lista de productos disponibles para la compra.
    """
    return render_template('index.html', productos=PRODUCTOS)

@app.route('/agregar_al_carrito/<int:id_producto>')
def agregar_al_carrito(id_producto):
    """
    Agrega un producto al carrito de compras almacenado en la sesión.
    """
    # Inicializar el carrito en sesión si no existe
    if 'carrito' not in session:
        session['carrito'] = {}

    carrito = session['carrito']

    # Agregar o actualizar la cantidad del producto en el carrito
    if str(id_producto) in carrito:
        carrito[str(id_producto)] += 1
    else:
        carrito[str(id_producto)] = 1

    session['carrito'] = carrito
    return redirect(url_for('ver_carrito'))


@app.route('/carrito')
def ver_carrito():
    """
    Muestra el contenido actual del carrito con productos y cantidades.
    """
    carrito = session.get('carrito', {})
    items_carrito = []

    # Construir la lista de items con detalles y cantidad
    for id_producto, cantidad in carrito.items():
        producto = next((p for p in PRODUCTOS if p['id'] == int(id_producto)), None)
        if producto:
            item = {
                "id": producto['id'],
                "nombre": producto['nombre'],
                "precio": producto['precio'],
                "cantidad": cantidad,
                "precio_total": producto['precio'] * cantidad
            }
            items_carrito.append(item)

    # Calcular el monto total
    monto_total = sum(item['precio_total'] for item in items_carrito)

    return render_template('cart.html', items_carrito=items_carrito, monto_total=monto_total)

@app.route('/carrito/eliminar/<int:id_producto>', methods=['POST'])
def eliminar_del_carrito(id_producto):
    """
    Elimina un producto del carrito de compras almacenado en la sesión.
    """
    carrito = session.get('carrito', {})

    if str(id_producto) in carrito:
        del carrito[str(id_producto)]
        session['carrito'] = carrito

    return redirect(url_for('ver_carrito'))

@app.route('/carrito/actualizar/<int:id_producto>', methods=['POST'])
def actualizar_cantidad_carrito(id_producto):
    """
    Actualiza la cantidad de un producto en el carrito de compras.
    """
    carrito = session.get('carrito', {})
    cantidad_nueva = request.form.get('cantidad', type=int)

    if cantidad_nueva is not None and cantidad_nueva > 0:
        carrito[str(id_producto)] = cantidad_nueva
    elif cantidad_nueva == 0:
        # Si la cantidad es 0, eliminar el producto del carrito
        if str(id_producto) in carrito:
            del carrito[str(id_producto)]

    session['carrito'] = carrito
    return redirect(url_for('ver_carrito'))

@app.route('/pago', methods=['POST'])
def pago():
    mp = mercadopago.SDK(acceso)

    datos_preferencia = {
        "items": [
            {
                "id": "paquete-turistico-001",
                "title": "Paquete turístico ficticio",
                "description": "Tour de prueba por la ciudad",
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": 1
            }
        ],
        "payer": {
            "name": "Juan",
            "surname": "Perez",
            "email": "test_user_123456@testuser.com"  # ¡Correo de test válido!
        },
        "back_urls": {
        "success": "https://test-jzbx.onrender.com/success",
        "failure": "https://test-jzbx.onrender.com/failure",
        "pending": "https://test-jzbx.onrender.com/pending"
        },
        # Esta línea fue comentada para poder utilizar el código en entorno local. Debe ser descomentada al subirse al servidor. 
        "auto_return": "approved"
    }

    respuesta = mp.preference().create(datos_preferencia)
    print("Respuesta completa:", respuesta)

    if "response" in respuesta:
        # Usar init_point (producción)
        return redirect(respuesta["response"]["init_point"])
    else:
        mensaje = respuesta.get("response", {}).get("message", "Error desconocido")
        return f"Error al crear la preferencia de pago: {mensaje}", 500

@app.route('/pending')
def pendiente():
    return "Tu pago está pendiente. Te avisaremos cuando se confirme."



@app.route('/success')
def exito():
    payment_id = request.args.get('payment_id')
    status = request.args.get('status')
    
    # Por ejemplo, guardar en la sesión (podés usar una base de datos también)

    return f"""
        <h1>¡Pago {status}!</h1>
        <p>Guardá este ID para verificar el estado después: <strong>{payment_id}</strong></p>
        <a href="/estado_pago?payment_id={payment_id}">Ver estado ahora</a>
    """

@app.route('/failure')
def fracaso():
    return redirect(url_for('ver_carrito'))

@app.route('/test')
def formulario():
    return '''
        <h2>Consultar estado de pago</h2>
        <form action="/estado_pago" method="get">
            <input type="text" name="payment_id" placeholder="Ingresá el Payment ID" required>
            <button type="submit">Consultar</button>
        </form>
    '''

@app.route('/estado_pago_form')
def estado_pago_form():
    return '''
        <h2>Consultar estado de pago</h2>
        <form action="/estado_pago" method="get">
            <label for="payment_id">Payment ID:</label><br>
            <input type="text" id="payment_id" name="payment_id" required>
            <br><br>
            <button type="submit">Consultar</button>
        </form>
    '''
    
@app.route('/estado_pago')
def estado_pago():
    payment_id = request.args.get('payment_id')
    
    if not payment_id:
        return "Falta el Payment ID. <a href='/estado_pago_form'>Volver</a>"
    
    try:
        mp = mercadopago.SDK(acceso)
        pago = mp.payment().get(payment_id)
        info = pago["response"]

        estado = info.get("status", "desconocido").upper()
        monto = info.get("transaction_amount", "no disponible")
        metodo = info.get("payment_method_id", "no disponible")
        fecha = info.get("date_created", "no disponible")
        email = info.get("payer", {}).get("email", "no disponible")

        return f"""
            <h3>Estado del pago</h3>
            <p><strong>ID:</strong> {payment_id}</p>
            <p><strong>Estado:</strong> {estado}</p>
            <p><strong>Monto:</strong> ${monto}</p>
            <p><strong>Método de pago:</strong> {metodo}</p>
            <p><strong>Fecha:</strong> {fecha}</p>
            <p><strong>Email del pagador:</strong> {email}</p>
            <br><a href="/estado_pago_form">Consultar otro</a>
        """
    except Exception as e:
        return f"Error al consultar el estado: {str(e)} <br><a href='/estado_pago_form'>Volver</a>"



@app.route('/compra')
def compra():
    """
    Ruta alternativa para compra sin usar Mercado Pago.
    Envía un email con los productos y cantidades al correo destinatario.
    """
    carrito = session.get('carrito', {})
    if not carrito:
        return redirect(url_for('inicio'))

    # Configuración del correo
    remitente = "notfc.noreply@gmail.com"  # Reemplazar con el correo remitente
    contraseña = "soop gyga qsta jfmp"  # Reemplazar con la contraseña o token SMTP
    destinatario = "danielfreccero09@gmail.com"  # Reemplazar con el correo destinatario

    # Construir el cuerpo del mensaje con los productos y cantidades
    cuerpo = "Detalle de la compra sin Mercado Pago:\n\n"
    for id_producto, cantidad in carrito.items():
        producto = next((p for p in PRODUCTOS if p['id'] == int(id_producto)), None)
        if producto:
            cuerpo += f"- {producto['nombre']}: {cantidad} unidad(es)\n"

    # Crear el mensaje MIME
    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = destinatario
    mensaje['Subject'] = "Nueva compra sin Mercado Pago"
    mensaje.attach(MIMEText(cuerpo, 'plain'))

    try:
        # Conectar al servidor SMTP de Gmail
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, contraseña)
        servidor.sendmail(remitente, destinatario, mensaje.as_string())
        servidor.quit()
    except Exception as e:
        return f"Error al enviar el correo: {str(e)}"

    # Limpiar carrito después de enviar el correo
    session.pop('carrito', None)
    return '''
        Compra realizada sin Mercado Pago. Se ha enviado un correo con el detalle de la compra.
        <br><br>
        <a href="{}">Seguir Comprando</a>
    '''.format(url_for('inicio'))

if __name__ == '__main__':
    # Ejecutar la aplicación Flask en modo debug
    app.run(debug=True)