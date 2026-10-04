from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from pathlib import Path
import os, sqlite3, json, uuid
from datetime import datetime

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

BASE = Path(__file__).resolve().parent
SQLITE_DB = BASE / 'todivo.db'
DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
USE_POSTGRES = bool(DATABASE_URL)
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '').strip()
ADMIN_SESSION_SECRET = os.getenv('ADMIN_SESSION_SECRET', '').strip()
app = Flask(__name__, static_folder=None)
if not ADMIN_SESSION_SECRET:
    ADMIN_SESSION_SECRET = os.urandom(32).hex()
app.secret_key = ADMIN_SESSION_SECRET
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=True, PERMANENT_SESSION_LIFETIME=3600)

DEFAULT_PRODUCTS = [
('audifonos-bluetooth','Audífonos Bluetooth Inalámbricos','Tecnología',29990,39990,25,'Oferta','assets/producto_1.svg','Audífonos inalámbricos con conexión Bluetooth y estuche de carga.'),
('smartwatch-active','Smartwatch Active','Tecnología',34990,44990,18,'Oferta','assets/producto_2.svg','Smartwatch para actividades diarias con pantalla digital.'),
('control-gamer-wireless','Control Gamer Wireless','Gaming',24990,31990,14,'Oferta','assets/producto_3.svg','Control inalámbrico para disfrutar tus juegos con comodidad.'),
('mini-proyector-hd','Mini Proyector HD','Tecnología',49990,59990,9,'Oferta','assets/producto_4.svg','Mini proyector compacto para entretenimiento en casa.'),
('teclado-mecanico-rgb','Teclado Mecánico RGB','Gaming',39990,49990,12,'Oferta','assets/producto_5.svg','Teclado mecánico con iluminación RGB para gaming y trabajo.'),
('mouse-gamer-pro','Mouse Gamer Pro','Gaming',19990,27990,20,'Oferta','assets/producto_6.svg','Mouse gamer preciso para sesiones de juego y trabajo.'),
('lampara-led-smart','Lámpara LED Smart','Hogar',16990,22990,30,'Oferta','assets/producto_7.svg','Lámpara LED moderna para escritorio y dormitorio.'),
('mochila-urbana','Mochila Urbana','Moda',27990,34990,16,'Oferta','assets/producto_8.svg','Mochila práctica para uso diario.'),
('parlante-bluetooth','Parlante Bluetooth','Tecnología',25990,32990,21,'Oferta','assets/producto_9.svg','Parlante portátil para música y entretenimiento.'),
('organizador-multiuso','Organizador Multiuso','Hogar',12990,17990,35,'Oferta','assets/producto_10.svg','Organizador práctico para mantener tus espacios ordenados.')]

def db():
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError('Falta psycopg. Revisa requirements.txt.')
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    con = sqlite3.connect(SQLITE_DB)
    con.row_factory = sqlite3.Row
    return con

def ph():
    return '%s' if USE_POSTGRES else '?'

def init_db():
    con = db()
    if USE_POSTGRES:
        con.execute('''CREATE TABLE IF NOT EXISTS products(
            id TEXT PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,
            price INTEGER NOT NULL DEFAULT 0,old_price INTEGER NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,tag TEXT DEFAULT '',image TEXT DEFAULT '',
            description TEXT DEFAULT '',features TEXT DEFAULT '[]',created_at TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS orders(
            id TEXT PRIMARY KEY,code TEXT UNIQUE NOT NULL,customer_name TEXT NOT NULL,
            email TEXT NOT NULL,phone TEXT NOT NULL,region TEXT NOT NULL,commune TEXT NOT NULL,
            address TEXT NOT NULL,detail TEXT DEFAULT '',shipping TEXT NOT NULL,
            shipping_price INTEGER NOT NULL DEFAULT 0,payment TEXT NOT NULL,
            subtotal INTEGER NOT NULL DEFAULT 0,total INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Pendiente',items TEXT NOT NULL DEFAULT '[]',created_at TEXT NOT NULL)''')
        count = con.execute('SELECT COUNT(*) AS n FROM products').fetchone()['n']
        if count == 0:
            now = datetime.now().isoformat()
            for p in DEFAULT_PRODUCTS:
                con.execute('''INSERT INTO products
                    (id,name,category,price,old_price,stock,tag,image,description,features,created_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''', tuple(p) + ('[]', now))
    else:
        con.executescript('''CREATE TABLE IF NOT EXISTS products(
            id TEXT PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,
            price INTEGER NOT NULL DEFAULT 0,old_price INTEGER NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,tag TEXT DEFAULT '',image TEXT DEFAULT '',
            description TEXT DEFAULT '',features TEXT DEFAULT '[]',created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders(
            id TEXT PRIMARY KEY,code TEXT UNIQUE NOT NULL,customer_name TEXT NOT NULL,
            email TEXT NOT NULL,phone TEXT NOT NULL,region TEXT NOT NULL,commune TEXT NOT NULL,
            address TEXT NOT NULL,detail TEXT DEFAULT '',shipping TEXT NOT NULL,
            shipping_price INTEGER NOT NULL DEFAULT 0,payment TEXT NOT NULL,
            subtotal INTEGER NOT NULL DEFAULT 0,total INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Pendiente',items TEXT NOT NULL DEFAULT '[]',created_at TEXT NOT NULL);''')
        count = con.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat()
            for p in DEFAULT_PRODUCTS:
                con.execute('''INSERT INTO products
                    (id,name,category,price,old_price,stock,tag,image,description,features,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)''', tuple(p) + ('[]', now))
    con.commit(); con.close()

def json_load(v):
    try: return json.loads(v or '[]')
    except Exception: return []

@app.get('/login.html')
def login_page():
    return send_from_directory(BASE, 'login.html')

@app.post('/api/login')
def login():
    if not ADMIN_PASSWORD:
        return jsonify({'error':'El acceso de administrador no está configurado. Agrega ADMIN_PASSWORD en Render.'}), 503
    data = request.get_json(silent=True) or {}
    if data.get('password','') != ADMIN_PASSWORD:
        return jsonify({'error':'Contraseña incorrecta'}), 401
    session.clear()
    session['admin_authenticated'] = True
    session.permanent = True
    return jsonify({'ok':True})

@app.post('/api/logout')
def logout():
    session.clear()
    return jsonify({'ok':True})

def admin_required():
    return bool(session.get('admin_authenticated'))

def protected_api():
    if not admin_required():
        return jsonify({'error':'No autorizado'}), 401
    return None

def admin_page(filename):
    if not admin_required():
        return redirect(url_for('login_page', next=filename))
    return send_from_directory(BASE, filename)

@app.get('/panel.html')
def panel_page(): return admin_page('panel.html')

@app.get('/admin.html')
def admin_catalog_page(): return admin_page('admin.html')

@app.get('/pedidos.html')
def pedidos_page(): return admin_page('pedidos.html')

@app.get('/api/health')
def health():
    try:
        con=db(); con.execute('SELECT 1').fetchone(); con.close()
        return jsonify({'ok':True,'service':'TODIVO CL API','database':'PostgreSQL' if USE_POSTGRES else 'SQLite'})
    except Exception as e:
        return jsonify({'ok':False,'service':'TODIVO CL API','error':str(e)}),500

@app.get('/api/products')
def get_products():
    con=db(); rows=con.execute('SELECT * FROM products ORDER BY created_at DESC').fetchall(); con.close()
    out=[]
    for r in rows:
        x=dict(r); x['oldPrice']=x.pop('old_price'); x['features']=json_load(x.pop('features')); out.append(x)
    return jsonify(out)

@app.post('/api/products')
def create_product():
    auth = protected_api()
    if auth:
        return auth
    data=request.get_json(force=True); required=['name','category','price','stock']
    if any(data.get(k) in (None,'') for k in required): return jsonify({'error':'Faltan campos obligatorios'}),400
    pid=data.get('id') or uuid.uuid4().hex[:12]; con=db(); p=ph()
    con.execute(f'''INSERT INTO products(id,name,category,price,old_price,stock,tag,image,description,features,created_at)
        VALUES({','.join([p]*11)})''',(pid,str(data['name']),str(data['category']),int(data.get('price',0)),int(data.get('oldPrice',0)),int(data.get('stock',0)),str(data.get('tag','')),str(data.get('image','')),str(data.get('description','')),json.dumps(data.get('features',[]),ensure_ascii=False),datetime.now().isoformat()))
    con.commit(); con.close(); return jsonify({'ok':True,'id':pid}),201

@app.put('/api/products/<pid>')
def update_product(pid):
    auth = protected_api()
    if auth:
        return auth
    data=request.get_json(force=True); con=db(); p=ph()
    cur=con.execute(f'''UPDATE products SET name={p},category={p},price={p},old_price={p},stock={p},tag={p},image={p},description={p},features={p} WHERE id={p}''',(str(data.get('name','')),str(data.get('category','')),int(data.get('price',0)),int(data.get('oldPrice',0)),int(data.get('stock',0)),str(data.get('tag','')),str(data.get('image','')),str(data.get('description','')),json.dumps(data.get('features',[]),ensure_ascii=False),pid))
    con.commit(); changed=cur.rowcount; con.close(); return jsonify({'ok':True}) if changed else (jsonify({'error':'Producto no encontrado'}),404)

@app.delete('/api/products/<pid>')
def delete_product(pid):
    auth = protected_api()
    if auth:
        return auth
    con=db(); p=ph(); cur=con.execute(f'DELETE FROM products WHERE id={p}',(pid,)); con.commit(); changed=cur.rowcount; con.close(); return jsonify({'ok':changed>0})

@app.get('/api/orders')
def get_orders():
    auth = protected_api()
    if auth:
        return auth
    con=db(); rows=con.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall(); con.close(); out=[]
    for r in rows:
        x=dict(r); x['items']=json_load(x['items']); out.append(x)
    return jsonify(out)

@app.post('/api/orders')
def create_order():
    data=request.get_json(force=True); customer=data.get('customer') or {}; items=data.get('items') or []
    for k in ('name','email','phone','region','commune','address'):
        if not str(customer.get(k,'')).strip(): return jsonify({'error':f'Falta {k}'}),400
    if not items: return jsonify({'error':'El pedido no tiene productos'}),400
    oid=uuid.uuid4().hex; code='TDV-'+datetime.now().strftime('%Y%m%d')+'-'+uuid.uuid4().hex[:5].upper(); con=db(); p=ph()
    try:
        if not USE_POSTGRES: con.execute('BEGIN IMMEDIATE')
        normalized=[]
        for item in items:
            pid=str(item.get('id','')); qty=max(1,int(item.get('qty',item.get('quantity',1))))
            if USE_POSTGRES:
                row=con.execute(f'SELECT id,name,price,stock,image FROM products WHERE id={p} FOR UPDATE',(pid,)).fetchone()
            else:
                row=con.execute(f'SELECT id,name,price,stock,image FROM products WHERE id={p}',(pid,)).fetchone()
            if not row:
                con.rollback(); con.close(); return jsonify({'error':f'Producto no encontrado: {pid}'}),400
            if int(row['stock'])<qty:
                con.rollback(); con.close(); return jsonify({'error':f'Stock insuficiente para {row["name"]}'}),409
            normalized.append({'id':row['id'],'name':row['name'],'price':int(row['price']),'qty':qty,'image':row['image']})
        subtotal_real=sum(x['price']*x['qty'] for x in normalized); shipping_price=int(data.get('shippingPrice',0)); total_real=subtotal_real+shipping_price
        vals=[oid,code,customer['name'],customer['email'],customer['phone'],customer['region'],customer['commune'],customer['address'],customer.get('detail',''),data.get('shipping','standard'),shipping_price,data.get('payment','demo'),subtotal_real,total_real,'Pendiente',json.dumps(normalized,ensure_ascii=False),datetime.now().isoformat()]
        con.execute(f'''INSERT INTO orders(id,code,customer_name,email,phone,region,commune,address,detail,shipping,shipping_price,payment,subtotal,total,status,items,created_at)
            VALUES({','.join([p]*17)})''',vals)
        for x in normalized: con.execute(f'UPDATE products SET stock=stock-{p} WHERE id={p}',(x['qty'],x['id']))
        con.commit(); con.close(); return jsonify({'ok':True,'id':oid,'code':code,'subtotal':subtotal_real,'total':total_real}),201
    except Exception as e:
        try: con.rollback(); con.close()
        except Exception: pass
        return jsonify({'error':str(e)}),500

@app.patch('/api/orders/<oid>')
def update_order(oid):
    auth = protected_api()
    if auth:
        return auth
    status=(request.get_json(force=True) or {}).get('status'); allowed={'Pendiente','Confirmado','Enviado','Entregado','Cancelado'}
    if status not in allowed: return jsonify({'error':'Estado inválido'}),400
    con=db(); p=ph(); cur=con.execute(f'UPDATE orders SET status={p} WHERE id={p}',(status,oid)); con.commit(); changed=cur.rowcount; con.close(); return jsonify({'ok':True}) if changed else (jsonify({'error':'Pedido no encontrado'}),404)

@app.delete('/api/orders/<oid>')
def delete_order(oid):
    auth = protected_api()
    if auth:
        return auth
    con=db(); p=ph(); cur=con.execute(f'DELETE FROM orders WHERE id={p}',(oid,)); con.commit(); changed=cur.rowcount; con.close(); return jsonify({'ok':changed>0})

@app.get('/')
def home(): return send_from_directory(BASE,'index.html')

PUBLIC_FILES = {'index.html','producto.html','checkout.html','api.html','catalog.js','login.html','googleff57496071cffa50.html','sitemap.xml'}

@app.get('/<path:filename>')
def public_files(filename):
    if filename.startswith('assets/') or filename in PUBLIC_FILES:
        path = BASE / filename
        if path.is_file():
            return send_from_directory(BASE, filename)
    return jsonify({'error':'No encontrado'}), 404

try:
    init_db()
    print('TODIVO CL DB:', 'PostgreSQL' if USE_POSTGRES else 'SQLite')
except Exception as e:
    print('ERROR inicializando base de datos:',repr(e))

if __name__=='__main__':
    print('TODIVO CL API: http://127.0.0.1:5000'); app.run(host='127.0.0.1',port=5000,debug=True)
