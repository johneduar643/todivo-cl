from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, Response
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import os, sqlite3, json, uuid, csv, io, hashlib, secrets, urllib.request, urllib.error

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

BASE=Path(__file__).resolve().parent
SQLITE_DB=BASE/'todivo.db'
DATABASE_URL=os.getenv('DATABASE_URL','').strip()
USE_POSTGRES=bool(DATABASE_URL)
ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD','').strip()
SESSION_SECRET=os.getenv('ADMIN_SESSION_SECRET','').strip() or secrets.token_hex(32)
app=Flask(__name__,static_folder=None)
app.secret_key=SESSION_SECRET
app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=USE_POSTGRES,PERMANENT_SESSION_LIFETIME=timedelta(days=7))

DEFAULT_PRODUCTS=[
('audifonos-bluetooth','Audífonos Bluetooth Inalámbricos','Tecnología',29990,39990,25,'Oferta','assets/producto_1.svg','Audífonos inalámbricos con conexión Bluetooth y estuche de carga.',['Bluetooth','Micrófono integrado','Estuche de carga']),
('smartwatch-active','Smartwatch Active','Tecnología',34990,44990,18,'Oferta','assets/producto_2.svg','Smartwatch para actividades diarias.',['Pantalla digital','Notificaciones','Seguimiento de actividad']),
('control-gamer-wireless','Control Gamer Wireless','Gaming',24990,31990,14,'Oferta','assets/producto_3.svg','Control inalámbrico para disfrutar tus juegos.',['Wireless','Vibración','Diseño ergonómico']),
('mini-proyector-hd','Mini Proyector HD','Tecnología',49990,59990,9,'Oferta','assets/producto_4.svg','Mini proyector compacto para entretenimiento.',['HD','Compacto','Entrada multimedia']),
('teclado-mecanico-rgb','Teclado Mecánico RGB','Gaming',39990,49990,12,'Oferta','assets/producto_5.svg','Teclado mecánico con iluminación RGB.',['RGB','Teclas mecánicas','USB']),
('mouse-gamer-pro','Mouse Gamer Pro','Gaming',19990,27990,20,'Oferta','assets/producto_6.svg','Mouse gamer preciso.',['Alta precisión','Botones configurables','USB']),
('lampara-led-smart','Lámpara LED Smart','Hogar',16990,22990,30,'Oferta','assets/producto_7.svg','Lámpara LED moderna.',['LED','Ahorro de energía','Diseño moderno']),
('mochila-urbana','Mochila Urbana','Moda',27990,34990,16,'Oferta','assets/producto_8.svg','Mochila práctica para uso diario.',['Compartimentos','Uso diario','Diseño urbano']),
('parlante-bluetooth','Parlante Bluetooth','Tecnología',25990,32990,21,'Oferta','assets/producto_9.svg','Parlante portátil.',['Bluetooth','Portátil','Batería recargable']),
('organizador-multiuso','Organizador Multiuso','Hogar',12990,17990,35,'Oferta','assets/producto_10.svg','Organizador práctico.',['Multiuso','Compacto','Fácil de limpiar'])]
STATUSES={'Pendiente','Confirmado','Preparando','Enviado','Entregado','Cancelado'}
SELLER_STATUSES={'pending','approved','rejected','suspended'}


def now(): return datetime.now(timezone.utc).isoformat()
def ph(): return '%s' if USE_POSTGRES else '?'
def placeholders(n): return ','.join([ph()]*n)
def db():
    if USE_POSTGRES:
        if psycopg is None: raise RuntimeError('Falta psycopg[binary].')
        return psycopg.connect(DATABASE_URL,row_factory=dict_row,connect_timeout=10)
    c=sqlite3.connect(SQLITE_DB); c.row_factory=sqlite3.Row; return c

def hash_password(password):
    salt=secrets.token_hex(16); return salt+'$'+hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex()
def verify_password(password,stored):
    try:
        salt,digest=stored.split('$',1); calc=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),180000).hex(); return secrets.compare_digest(calc,digest)
    except Exception:return False
def json_load(v):
    try:return json.loads(v or '[]')
    except Exception:return []
def rowdict(r): return dict(r) if r else None

def init_db():
    c=db();
    stmts=[
    'CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT NOT NULL,phone TEXT DEFAULT \'\',role TEXT NOT NULL DEFAULT \'customer\',created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS sellers(id TEXT PRIMARY KEY,user_id TEXT UNIQUE NOT NULL,store_name TEXT NOT NULL,description TEXT DEFAULT \'\',status TEXT NOT NULL DEFAULT \'pending\',commission_rate INTEGER NOT NULL DEFAULT 10,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,name TEXT NOT NULL,category TEXT NOT NULL,price INTEGER NOT NULL DEFAULT 0,old_price INTEGER NOT NULL DEFAULT 0,stock INTEGER NOT NULL DEFAULT 0,tag TEXT DEFAULT \'\',image TEXT DEFAULT \'\',description TEXT DEFAULT \'\',features TEXT DEFAULT \'[]\',seller_id TEXT,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS addresses(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,label TEXT DEFAULT \'\',region TEXT NOT NULL,commune TEXT NOT NULL,address TEXT NOT NULL,detail TEXT DEFAULT \'\',is_default INTEGER DEFAULT 0,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS favorites(user_id TEXT NOT NULL,product_id TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(user_id,product_id))',
    'CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,title TEXT NOT NULL,message TEXT NOT NULL,read INTEGER DEFAULT 0,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS password_resets(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,token TEXT UNIQUE NOT NULL,expires_at TEXT NOT NULL,used INTEGER DEFAULT 0,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,code TEXT UNIQUE NOT NULL,customer_id TEXT,customer_name TEXT NOT NULL,email TEXT NOT NULL,phone TEXT NOT NULL,region TEXT NOT NULL,commune TEXT NOT NULL,address TEXT NOT NULL,detail TEXT DEFAULT \'\',shipping TEXT NOT NULL,shipping_price INTEGER NOT NULL DEFAULT 0,payment TEXT NOT NULL,payment_status TEXT NOT NULL DEFAULT \'pending\',subtotal INTEGER NOT NULL DEFAULT 0,total INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT \'Pendiente\',items TEXT NOT NULL DEFAULT \'[]\',created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,product_id TEXT NOT NULL,user_id TEXT NOT NULL,rating INTEGER NOT NULL,comment TEXT DEFAULT \'\',created_at TEXT NOT NULL,UNIQUE(product_id,user_id))']
    if USE_POSTGRES:
        for s in stmts:c.execute(s)
        alters=[
          'ALTER TABLE products ADD COLUMN seller_id TEXT',
          'ALTER TABLE orders ADD COLUMN customer_id TEXT',
          'ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT \'pending\'',
          'ALTER TABLE sellers ADD COLUMN commission_rate INTEGER NOT NULL DEFAULT 10']
        for s in alters:
            try:c.execute(s)
            except Exception:pass
        n=c.execute('SELECT COUNT(*) AS n FROM products').fetchone()['n']
        if not n:
            for x in DEFAULT_PRODUCTS:c.execute('INSERT INTO products(id,name,category,price,old_price,stock,tag,image,description,features,created_at,seller_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(*x[:9],json.dumps(x[9],ensure_ascii=False),now(),None))
    else:
        for s in stmts:
            try:c.execute(s)
            except sqlite3.OperationalError:
                pass
        for s in ['ALTER TABLE products ADD COLUMN seller_id TEXT','ALTER TABLE orders ADD COLUMN customer_id TEXT','ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT \'pending\'','ALTER TABLE sellers ADD COLUMN commission_rate INTEGER NOT NULL DEFAULT 10']:
            try:c.execute(s)
            except Exception:pass
        n=c.execute('SELECT COUNT(*) FROM products').fetchone()[0]
        if not n:
            for x in DEFAULT_PRODUCTS:c.execute('INSERT INTO products(id,name,category,price,old_price,stock,tag,image,description,features,created_at,seller_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(*x[:9],json.dumps(x[9],ensure_ascii=False),now(),None))
    c.commit();c.close()

def current_user():
    uid=session.get('user_id')
    if not uid:return None
    c=db();p=ph();r=c.execute(f'SELECT id,email,name,phone,role FROM users WHERE id={p}',(uid,)).fetchone();c.close();return rowdict(r)
def require_user():
    u=current_user()
    return (u,None) if u else (None,(jsonify({'error':'Inicia sesión para continuar'}),401))
def admin_guard():
    return None if session.get('admin_authenticated') else (jsonify({'error':'No autorizado'}),401)
def product_dict(r):
    x=dict(r); x['oldPrice']=x.pop('old_price');x['features']=json_load(x.pop('features')); return x

def notify(user_id,title,message):
    if not user_id:return
    c=db();p=ph();c.execute(f'INSERT INTO notifications(id,user_id,title,message,read,created_at) VALUES({placeholders(6)})',(uuid.uuid4().hex,user_id,title,message,0,now()));c.commit();c.close()

@app.before_request
def boot():
    if not getattr(app,'_db_ready',False):
        try:init_db();app._db_ready=True
        except Exception as e: print('DB:',e,flush=True)

@app.get('/')
def home():return send_from_directory(BASE,'index.html')
@app.get('/login.html')
def login_page():return send_from_directory(BASE,'login.html')
@app.get('/registro.html')
def register_page():return send_from_directory(BASE,'registro.html')
@app.get('/vendedor.html')
def seller_page():return send_from_directory(BASE,'vendedor.html')
@app.get('/recuperar.html')
def recover_page():return send_from_directory(BASE,'recuperar.html')

@app.post('/api/register')
def register():
    d=request.get_json(silent=True) or {};name=str(d.get('name','')).strip();email=str(d.get('email','')).strip().lower();pw=str(d.get('password',''))
    if len(name)<2 or '@' not in email or len(pw)<8:return jsonify({'error':'Nombre, correo válido y contraseña de al menos 8 caracteres'}),400
    c=db();p=ph();uid=uuid.uuid4().hex
    try:c.execute(f'INSERT INTO users(id,email,password_hash,name,phone,role,created_at) VALUES({placeholders(7)})',(uid,email,hash_password(pw),name,str(d.get('phone','')).strip(),'customer',now()));c.commit();session['user_id']=uid;session.permanent=True;return jsonify({'ok':True,'user':{'id':uid,'name':name,'email':email,'role':'customer'}}),201
    except Exception:c.rollback();return jsonify({'error':'Ese correo ya está registrado'}),409
    finally:c.close()

@app.post('/api/customer/login')
def customer_login():
    d=request.get_json(silent=True) or {};email=str(d.get('email','')).strip().lower();pw=str(d.get('password',''));c=db();p=ph();r=c.execute(f'SELECT * FROM users WHERE email={p}',(email,)).fetchone();c.close()
    if not r or not verify_password(pw,r['password_hash']):return jsonify({'error':'Correo o contraseña incorrectos'}),401
    session['user_id']=r['id'];session.permanent=True;return jsonify({'ok':True,'user':{'id':r['id'],'name':r['name'],'email':r['email'],'role':r['role']}})
@app.post('/api/customer/logout')
def customer_logout():session.pop('user_id',None);return jsonify({'ok':True})
@app.get('/api/me')
def me():u=current_user();return jsonify({'authenticated':bool(u),'user':u})

@app.post('/api/password/request')
def password_request():
    d=request.get_json(silent=True) or {};email=str(d.get('email','')).strip().lower();c=db();p=ph();u=c.execute(f'SELECT id FROM users WHERE email={p}',(email,)).fetchone()
    # Always return neutral response. In production email provider should deliver the token.
    if u:
        token=secrets.token_urlsafe(32);expires=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat();c.execute(f'INSERT INTO password_resets(id,user_id,token,expires_at,used,created_at) VALUES({placeholders(6)})',(uuid.uuid4().hex,u['id'],token,expires,0,now()));c.commit()
        if os.getenv('RESET_DEBUG','').lower()=='true':return jsonify({'ok':True,'debugToken':token})
    c.close();return jsonify({'ok':True,'message':'Si el correo existe, recibirás instrucciones para recuperar tu contraseña.'})
@app.post('/api/password/reset')
def password_reset():
    d=request.get_json(silent=True) or {};token=str(d.get('token',''));pw=str(d.get('password',''))
    if len(pw)<8:return jsonify({'error':'La contraseña debe tener al menos 8 caracteres'}),400
    c=db();p=ph();r=c.execute(f'SELECT * FROM password_resets WHERE token={p} AND used=0',(token,)).fetchone()
    if not r or r['expires_at']<now():c.close();return jsonify({'error':'Token inválido o expirado'}),400
    c.execute(f'UPDATE users SET password_hash={p} WHERE id={p}',(hash_password(pw),r['user_id']));c.execute(f'UPDATE password_resets SET used=1 WHERE id={p}',(r['id'],));c.commit();c.close();return jsonify({'ok':True})

@app.post('/api/seller/apply')
def seller_apply():
    u,err=require_user()
    if err:return err
    d=request.get_json(silent=True) or {};store=str(d.get('storeName','')).strip()
    if len(store)<3:return jsonify({'error':'Indica el nombre de tu tienda'}),400
    c=db();p=ph()
    try:
        sid=uuid.uuid4().hex;c.execute(f'INSERT INTO sellers(id,user_id,store_name,description,status,commission_rate,created_at) VALUES({placeholders(6)})',(sid,u['id'],store,str(d.get('description','')).strip(),'pending',10,now()));c.commit();return jsonify({'ok':True,'sellerId':sid,'status':'pending'}),201
    except Exception:c.rollback();return jsonify({'error':'Ya existe una solicitud para este usuario'}),409
    finally:c.close()
@app.get('/api/seller/me')
def seller_me():
    u,err=require_user()
    if err:return err
    c=db();p=ph();r=c.execute(f'SELECT * FROM sellers WHERE user_id={p}',(u['id'],)).fetchone();c.close();return jsonify({'seller':rowdict(r)})

def seller_required():
    u=current_user()
    if not u:return None,(jsonify({'error':'Inicia sesión'}),401)
    c=db();p=ph();s=c.execute(f'SELECT * FROM sellers WHERE user_id={p}',(u['id'],)).fetchone();c.close()
    if not s or s['status']!='approved':return None,(jsonify({'error':'Tu cuenta de vendedor aún no está aprobada'}),403)
    return dict(s),None

@app.get('/api/seller/dashboard')
def seller_dashboard():
    s,err=seller_required()
    if err:return err
    c=db();p=ph();products=c.execute(f'SELECT * FROM products WHERE seller_id={p} ORDER BY created_at DESC',(s['id'],)).fetchall();
    orders=[]
    for r in c.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall():
        items=json_load(r['items']); mine=[i for i in items if i.get('seller_id')==s['id']]
        if mine: orders.append({**dict(r),'items':mine})
    sales=sum(int(i.get('price',0))*int(i.get('qty',1)) for o in orders for i in o['items'] if o.get('seller_id')==s['id'])
    c.close();return jsonify({'seller':s,'products':[product_dict(x) for x in products],'orders':orders,'stats':{'products':len(products),'orders':len(orders),'sales':sales}})
@app.post('/api/seller/products')
def seller_product_create():
    s,err=seller_required()
    if err:return err
    d=request.get_json(force=True) or {};name=str(d.get('name','')).strip();cat=str(d.get('category','')).strip();price=int(d.get('price',0));stock=max(0,int(d.get('stock',0)))
    if len(name)<2 or not cat or price<=0:return jsonify({'error':'Nombre, categoría y precio son obligatorios'}),400
    pid=d.get('id') or uuid.uuid4().hex[:12];c=db();p=ph()
    c.execute(f'INSERT INTO products(id,name,category,price,old_price,stock,tag,image,description,features,seller_id,created_at) VALUES({placeholders(12)})',(pid,name,cat,price,max(0,int(d.get('oldPrice',0))),stock,str(d.get('tag','')).strip(),str(d.get('image','')).strip() or 'assets/producto_1.svg',str(d.get('description','')).strip(),json.dumps(d.get('features',[]),ensure_ascii=False),s['id'],now()));c.commit();c.close();return jsonify({'ok':True,'id':pid}),201
@app.put('/api/seller/products/<pid>')
def seller_product_update(pid):
    s,err=seller_required()
    if err:return err
    d=request.get_json(force=True) or {};c=db();p=ph();cur=c.execute(f'UPDATE products SET name={p},category={p},price={p},old_price={p},stock={p},tag={p},image={p},description={p},features={p} WHERE id={p} AND seller_id={p}',(str(d.get('name','')).strip(),str(d.get('category','')).strip(),max(0,int(d.get('price',0))),max(0,int(d.get('oldPrice',0))),max(0,int(d.get('stock',0))),str(d.get('tag','')).strip(),str(d.get('image','')).strip(),str(d.get('description','')).strip(),json.dumps(d.get('features',[]),ensure_ascii=False),pid,s['id']));c.commit();c.close();return jsonify({'ok':bool(cur.rowcount)})
@app.delete('/api/seller/products/<pid>')
def seller_product_delete(pid):
    s,err=seller_required()
    if err:return err
    c=db();p=ph();cur=c.execute(f'DELETE FROM products WHERE id={p} AND seller_id={p}',(pid,s['id']));c.commit();c.close();return jsonify({'ok':bool(cur.rowcount)})

@app.get('/api/products')
def products():
    c=db();rows=c.execute('SELECT p.*,s.store_name FROM products p LEFT JOIN sellers s ON s.id=p.seller_id WHERE p.stock>=0 ORDER BY p.created_at DESC').fetchall();c.close();return jsonify([product_dict(r) for r in rows])
@app.get('/api/products/<pid>')
def product_one(pid):
    c=db();p=ph();r=c.execute(f'SELECT p.*,s.store_name FROM products p LEFT JOIN sellers s ON s.id=p.seller_id WHERE p.id={p}',(pid,)).fetchone();c.close()
    if not r:return jsonify({'error':'Producto no encontrado'}),404
    x=product_dict(r);return jsonify(x)

@app.post('/api/products')
def admin_create_product():
    if (g:=admin_guard()):return g
    d=request.get_json(force=True) or {};pid=d.get('id') or uuid.uuid4().hex[:12];c=db();p=ph()
    c.execute(f'INSERT INTO products(id,name,category,price,old_price,stock,tag,image,description,features,seller_id,created_at) VALUES({placeholders(12)})',(pid,str(d.get('name','')).strip(),str(d.get('category','')).strip(),int(d.get('price',0)),int(d.get('oldPrice',0)),max(0,int(d.get('stock',0))),str(d.get('tag','')),str(d.get('image','')) or 'assets/producto_1.svg',str(d.get('description','')),json.dumps(d.get('features',[]),ensure_ascii=False),d.get('sellerId'),now()));c.commit();c.close();return jsonify({'ok':True,'id':pid}),201
@app.put('/api/products/<pid>')
def admin_update_product(pid):
    if (g:=admin_guard()):return g
    d=request.get_json(force=True) or {};c=db();p=ph();cur=c.execute(f'UPDATE products SET name={p},category={p},price={p},old_price={p},stock={p},tag={p},image={p},description={p},features={p},seller_id={p} WHERE id={p}',(str(d.get('name','')).strip(),str(d.get('category','')).strip(),int(d.get('price',0)),int(d.get('oldPrice',0)),max(0,int(d.get('stock',0))),str(d.get('tag','')),str(d.get('image','')),str(d.get('description','')),json.dumps(d.get('features',[]),ensure_ascii=False),d.get('sellerId'),pid));c.commit();c.close();return jsonify({'ok':bool(cur.rowcount)})
@app.delete('/api/products/<pid>')
def admin_delete_product(pid):
    if (g:=admin_guard()):return g
    c=db();p=ph();cur=c.execute(f'DELETE FROM products WHERE id={p}',(pid,));c.commit();c.close();return jsonify({'ok':bool(cur.rowcount)})

@app.get('/api/customer/profile')
def profile():
    u,err=require_user()
    if err:return err
    c=db();p=ph();r=c.execute(f'SELECT id,email,name,phone,role FROM users WHERE id={p}',(u['id'],)).fetchone();c.close();return jsonify({'user':rowdict(r)})
@app.put('/api/customer/profile')
def profile_update():
    u,err=require_user()
    if err:return err
    d=request.get_json(silent=True) or {};name=str(d.get('name','')).strip();phone=str(d.get('phone','')).strip()
    if len(name)<2:return jsonify({'error':'Nombre inválido'}),400
    c=db();p=ph();c.execute(f'UPDATE users SET name={p},phone={p} WHERE id={p}',(name,phone,u['id']));c.commit();c.close();return jsonify({'ok':True})
@app.get('/api/customer/addresses')
def addresses():
    u,err=require_user()
    if err:return err
    c=db();p=ph();r=c.execute(f'SELECT * FROM addresses WHERE user_id={p} ORDER BY is_default DESC,created_at DESC',(u['id'],)).fetchall();c.close();return jsonify([dict(x) for x in r])
@app.post('/api/customer/addresses')
def address_add():
    u,err=require_user()
    if err:return err
    d=request.get_json(silent=True) or {};required=('region','commune','address')
    if any(not str(d.get(k,'')).strip() for k in required):return jsonify({'error':'Región, comuna y dirección son obligatorias'}),400
    c=db();p=ph();aid=uuid.uuid4().hex
    if d.get('isDefault'):c.execute(f'UPDATE addresses SET is_default=0 WHERE user_id={p}',(u['id'],))
    c.execute(f'INSERT INTO addresses(id,user_id,label,region,commune,address,detail,is_default,created_at) VALUES({placeholders(9)})',(aid,u['id'],str(d.get('label','')).strip(),str(d['region']).strip(),str(d['commune']).strip(),str(d['address']).strip(),str(d.get('detail','')).strip(),1 if d.get('isDefault') else 0,now()));c.commit();c.close();return jsonify({'ok':True,'id':aid}),201
@app.delete('/api/customer/addresses/<aid>')
def address_delete(aid):
    u,err=require_user()
    if err:return err
    c=db();p=ph();cur=c.execute(f'DELETE FROM addresses WHERE id={p} AND user_id={p}',(aid,u['id']));c.commit();c.close();return jsonify({'ok':bool(cur.rowcount)})

@app.get('/api/customer/favorites')
def favs():
    u,err=require_user()
    if err:return err
    c=db();p=ph();r=c.execute(f'SELECT p.* FROM products p JOIN favorites f ON f.product_id=p.id WHERE f.user_id={p}',(u['id'],)).fetchall();c.close();return jsonify([product_dict(x) for x in r])
@app.post('/api/customer/favorites/<pid>')
def fav_add(pid):
    u,err=require_user()
    if err:return err
    c=db();p=ph()
    try:c.execute(f'INSERT INTO favorites(user_id,product_id,created_at) VALUES({placeholders(3)})',(u['id'],pid,now()));c.commit();return jsonify({'ok':True})
    except Exception:c.rollback();return jsonify({'ok':True})
    finally:c.close()
@app.delete('/api/customer/favorites/<pid>')
def fav_del(pid):
    u,err=require_user()
    if err:return err
    c=db();p=ph();c.execute(f'DELETE FROM favorites WHERE user_id={p} AND product_id={p}',(u['id'],pid));c.commit();c.close();return jsonify({'ok':True})

@app.get('/api/customer/notifications')
def notifications():
    u,err=require_user()
    if err:return err
    c=db();p=ph();r=c.execute(f'SELECT * FROM notifications WHERE user_id={p} ORDER BY created_at DESC',(u['id'],)).fetchall();c.close();return jsonify([dict(x) for x in r])
@app.post('/api/customer/notifications/read')
def notifications_read():
    u,err=require_user()
    if err:return err
    c=db();p=ph();c.execute(f'UPDATE notifications SET read=1 WHERE user_id={p}',(u['id'],));c.commit();c.close();return jsonify({'ok':True})

@app.post('/api/orders')
def create_order():
    d=request.get_json(force=True) or {};customer=d.get('customer') or {};items=d.get('items') or [];u=current_user()
    for k in ('name','email','phone','region','commune','address'):
        if not str(customer.get(k,'')).strip():return jsonify({'error':f'Falta {k}'}),400
    if not items:return jsonify({'error':'El pedido no tiene productos'}),400
    c=db();p=ph();oid=uuid.uuid4().hex;code='TDV-'+datetime.now(timezone.utc).strftime('%Y%m%d')+'-'+uuid.uuid4().hex[:5].upper()
    try:
        if not USE_POSTGRES:c.execute('BEGIN IMMEDIATE')
        norm=[]
        for it in items:
            pid=str(it.get('id',''));qty=max(1,min(99,int(it.get('qty',it.get('quantity',1)))));r=c.execute(f'SELECT id,name,price,stock,image,seller_id FROM products WHERE id={p}'+(' FOR UPDATE' if USE_POSTGRES else ''),(pid,)).fetchone()
            if not r:return jsonify({'error':'Producto no encontrado'}),400
            if int(r['stock'])<qty:return jsonify({'error':f'Stock insuficiente para {r["name"]}'}),409
            norm.append({'id':r['id'],'name':r['name'],'price':int(r['price']),'qty':qty,'image':r['image'],'seller_id':r['seller_id']})
        subtotal=sum(x['price']*x['qty'] for x in norm);ship=max(0,int(d.get('shippingPrice',0)));total=subtotal+ship;payment=str(d.get('payment','pending'))
        vals=[oid,code,u['id'] if u else None,str(customer['name']).strip(),str(customer['email']).strip().lower(),str(customer['phone']).strip(),str(customer['region']).strip(),str(customer['commune']).strip(),str(customer['address']).strip(),str(customer.get('detail','')).strip(),str(d.get('shipping','standard')),ship,payment,'pending',subtotal,total,'Pendiente',json.dumps(norm,ensure_ascii=False),now()]
        c.execute(f'INSERT INTO orders(id,code,customer_id,customer_name,email,phone,region,commune,address,detail,shipping,shipping_price,payment,payment_status,subtotal,total,status,items,created_at) VALUES({placeholders(19)})',vals)
        for x in norm:c.execute(f'UPDATE products SET stock=stock-{p} WHERE id={p}',(x['qty'],x['id']))
        c.commit()
        if u:notify(u['id'],'Pedido recibido',f'Tu pedido {code} fue creado correctamente.')
        return jsonify({'ok':True,'id':oid,'code':code,'subtotal':subtotal,'total':total,'paymentStatus':'pending'}),201
    except Exception as e:
        try:c.rollback()
        except:pass
        return jsonify({'error':str(e)}),500
    finally:c.close()

@app.post('/api/payments/create-preference')
def create_payment_preference():
    token=os.getenv('MERCADOPAGO_ACCESS_TOKEN','').strip()
    if not token:return jsonify({'configured':False,'message':'Proveedor de pagos no configurado.'}),503
    d=request.get_json(silent=True) or {};code=str(d.get('code','')).strip();c=db();p=ph();o=c.execute(f'SELECT * FROM orders WHERE code={p}',(code,)).fetchone();c.close()
    if not o:return jsonify({'error':'Pedido no encontrado'}),404
    items=json_load(o['items'])
    payload={'items':[{'id':str(i['id']),'title':i['name'],'quantity':int(i['qty']),'currency_id':'CLP','unit_price':float(i['price'])} for i in items], 'external_reference':code, 'back_urls':{'success':'https://todivo-cl.onrender.com/checkout.html?payment=success&order='+quote(code),'failure':'https://todivo-cl.onrender.com/checkout.html?payment=failure&order='+quote(code),'pending':'https://todivo-cl.onrender.com/checkout.html?payment=pending&order='+quote(code)},'auto_return':'approved','notification_url':'https://todivo-cl.onrender.com/api/payments/webhook'}
    req=urllib.request.Request('https://api.mercadopago.com/checkout/preferences',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=15) as resp: data=json.loads(resp.read().decode())
        return jsonify({'configured':True,'init_point':data.get('init_point'),'sandbox_init_point':data.get('sandbox_init_point'),'preference_id':data.get('id')})
    except urllib.error.HTTPError as e:
        return jsonify({'error':'Mercado Pago rechazó la solicitud','details':e.read().decode(errors='ignore')[:500]}),502
    except Exception as e:return jsonify({'error':'No se pudo conectar con el proveedor de pagos','details':str(e)}),502

@app.post('/api/payments/webhook')
def payment_webhook():
    # Mercado Pago sends a notification containing a payment id. The server must
    # query Mercado Pago itself before changing the order status.
    token=os.getenv('MERCADOPAGO_ACCESS_TOKEN','').strip()
    data=request.get_json(silent=True) or {}
    payment_id=data.get('data',{}).get('id') if isinstance(data.get('data'),dict) else data.get('id')
    if not token or not payment_id:
        return jsonify({'ok':True})
    req=urllib.request.Request('https://api.mercadopago.com/v1/payments/'+quote(str(payment_id),safe=''),headers={'Authorization':'Bearer '+token},method='GET')
    try:
        with urllib.request.urlopen(req,timeout=10) as resp: payment=json.loads(resp.read().decode())
        code=str(payment.get('external_reference','')).strip()
        status=str(payment.get('status','')).lower()
        mapped={'approved':'approved','authorized':'approved','pending':'pending','in_process':'pending','rejected':'rejected','cancelled':'cancelled'}.get(status)
        if code and mapped:
            c=db();p=ph();c.execute(f'UPDATE orders SET payment_status={p} WHERE code={p}',(mapped,code));c.commit();c.close()
        return jsonify({'ok':True})
    except Exception as e:
        print('Mercado Pago webhook:',e,flush=True)
        return jsonify({'ok':False}),200

@app.post('/api/order-lookup')
def order_lookup():
    d=request.get_json(silent=True) or {}
    code=str(d.get('code','')).strip()
    email=str(d.get('email','')).strip().lower()
    if not code or not email:
        return jsonify({'error':'Ingresa el código y el correo del pedido'}),400
    c=db();p=ph()
    r=c.execute(f'SELECT * FROM orders WHERE code={p} AND lower(email)=lower({p})',(code,email)).fetchone();c.close()
    if not r:
        return jsonify({'error':'No encontramos un pedido con esos datos'}),404
    o=dict(r);o['items']=json_load(o.get('items'));
    return jsonify({'order':o})

@app.get('/api/customer/orders')
def customer_orders():
    u,err=require_user()
    if err:return err
    c=db();p=ph();rs=c.execute(f'SELECT * FROM orders WHERE customer_id={p} OR lower(email)=lower({p}) ORDER BY created_at DESC',(u['id'],u['email'])).fetchall();c.close();out=[]
    for r in rs:
        x=dict(r);x['items']=json_load(x['items']);out.append(x)
    return jsonify(out)
@app.get('/api/orders')
def admin_orders():
    if (g:=admin_guard()):return g
    c=db();rs=c.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall();c.close();return jsonify([{**dict(r),'items':json_load(r['items'])} for r in rs])
@app.patch('/api/orders/<oid>')
def admin_order_status(oid):
    if (g:=admin_guard()):return g
    d=request.get_json(silent=True) or {};status=d.get('status')
    if status not in STATUSES:return jsonify({'error':'Estado inválido'}),400
    c=db();p=ph();r=c.execute(f'SELECT * FROM orders WHERE id={p}',(oid,)).fetchone()
    if not r:c.close();return jsonify({'error':'Pedido no encontrado'}),404
    c.execute(f'UPDATE orders SET status={p} WHERE id={p}',(status,oid));c.commit();c.close()
    if r['customer_id']:notify(r['customer_id'],'Actualización de pedido',f'El pedido {r["code"]} ahora está: {status}.')
    return jsonify({'ok':True})
@app.delete('/api/orders/<oid>')
def admin_delete_order(oid):
    if (g:=admin_guard()):return g
    c=db();p=ph();r=c.execute(f'SELECT * FROM orders WHERE id={p}',(oid,)).fetchone()
    if not r:c.close();return jsonify({'ok':False}),404
    if r['status']!='Cancelado':
        for it in json_load(r['items']):c.execute(f'UPDATE products SET stock=stock+{p} WHERE id={p}',(int(it.get('qty',1)),it['id']))
    c.execute(f'DELETE FROM orders WHERE id={p}',(oid,));c.commit();c.close();return jsonify({'ok':True})

@app.post('/api/reviews')
def review_add():
    u,err=require_user()
    if err:return err
    d=request.get_json(silent=True) or {};rating=int(d.get('rating',0));pid=str(d.get('productId',''));comment=str(d.get('comment','')).strip()
    if rating<1 or rating>5:return jsonify({'error':'Calificación entre 1 y 5'}),400
    c=db();p=ph()
    try:c.execute(f'INSERT INTO reviews(id,product_id,user_id,rating,comment,created_at) VALUES({placeholders(6)})',(uuid.uuid4().hex,pid,u['id'],rating,comment,now()));c.commit();return jsonify({'ok':True}),201
    except Exception:c.rollback();return jsonify({'error':'Ya calificaste este producto'}),409
    finally:c.close()
@app.get('/api/products/<pid>/reviews')
def reviews(pid):
    c=db();p=ph();rs=c.execute(f'SELECT r.rating,r.comment,r.created_at,u.name FROM reviews r JOIN users u ON u.id=r.user_id WHERE r.product_id={p} ORDER BY r.created_at DESC',(pid,)).fetchall();c.close();return jsonify([dict(x) for x in rs])

@app.post('/api/login')
def admin_login():
    if not ADMIN_PASSWORD:return jsonify({'error':'ADMIN_PASSWORD no configurada'}),503
    d=request.get_json(silent=True) or {}
    if d.get('password')!=ADMIN_PASSWORD:return jsonify({'error':'Contraseña incorrecta'}),401
    session.clear();session['admin_authenticated']=True;session.permanent=True;return jsonify({'ok':True})
@app.post('/api/logout')
def admin_logout():session.clear();return jsonify({'ok':True})
@app.get('/panel.html')
def panel():return admin_page('panel.html')
@app.get('/admin.html')
def admin_page_route():return admin_page('admin.html')
@app.get('/pedidos.html')
def pedidos():return admin_page('pedidos.html')
def admin_page(name):
    if not session.get('admin_authenticated'):return redirect(url_for('login_page',next=name))
    return send_from_directory(BASE,name)

@app.get('/api/admin/stats')
def admin_stats():
    if (g:=admin_guard()):return g
    c=db();
    stats={}
    stats['products']=c.execute('SELECT COUNT(*) AS n FROM products').fetchone()['n'] if USE_POSTGRES else c.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    stats['users']=c.execute('SELECT COUNT(*) AS n FROM users').fetchone()['n'] if USE_POSTGRES else c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    stats['sellers']=c.execute('SELECT COUNT(*) AS n FROM sellers').fetchone()['n'] if USE_POSTGRES else c.execute('SELECT COUNT(*) FROM sellers').fetchone()[0]
    stats['orders']=c.execute('SELECT COUNT(*) AS n FROM orders').fetchone()['n'] if USE_POSTGRES else c.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    stats['sales']=c.execute("SELECT COALESCE(SUM(total),0) AS n FROM orders WHERE status!='Cancelado'").fetchone()['n']
    c.close();return jsonify(stats)
@app.get('/api/admin/users')
def admin_users():
    if (g:=admin_guard()):return g
    c=db();rs=c.execute('SELECT id,name,email,phone,role,created_at FROM users ORDER BY created_at DESC').fetchall();c.close();return jsonify([dict(x) for x in rs])
@app.get('/api/admin/sellers')
def admin_sellers():
    if (g:=admin_guard()):return g
    c=db();rs=c.execute('SELECT s.*,u.name,u.email FROM sellers s JOIN users u ON u.id=s.user_id ORDER BY s.created_at DESC').fetchall();c.close();return jsonify([dict(x) for x in rs])
@app.patch('/api/admin/sellers/<sid>')
def admin_seller_status(sid):
    if (g:=admin_guard()):return g
    d=request.get_json(silent=True) or {};status=d.get('status')
    if status not in SELLER_STATUSES:return jsonify({'error':'Estado inválido'}),400
    c=db();p=ph();r=c.execute(f'SELECT user_id FROM sellers WHERE id={p}',(sid,)).fetchone();c.execute(f'UPDATE sellers SET status={p} WHERE id={p}',(status,sid));c.commit();c.close()
    if r:notify(r['user_id'],'Estado de vendedor',f'Tu solicitud de vendedor está: {status}.')
    return jsonify({'ok':True})
@app.get('/api/orders.csv')
def orders_csv():
    if (g:=admin_guard()):return g
    c=db();rs=c.execute('SELECT code,created_at,customer_name,email,phone,region,commune,address,shipping,payment,payment_status,subtotal,total,status FROM orders ORDER BY created_at DESC').fetchall();c.close();out=io.StringIO();w=csv.writer(out);w.writerow(['Pedido','Fecha','Cliente','Email','Teléfono','Región','Comuna','Dirección','Envío','Pago','Estado pago','Subtotal','Total','Estado']);
    for r in rs:w.writerow(list(r))
    return Response('\ufeff'+out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=todivo-pedidos.csv'})

@app.get('/api/health')
def health():
    try:
        c=db();c.execute('SELECT 1').fetchone();c.close();return jsonify({'ok':True,'service':'TODIVO CL API','database':'PostgreSQL' if USE_POSTGRES else 'SQLite','marketplace':'v35','customerAccounts':True,'sellerPortal':True,'adminPortal':True,'reviews':True,'favorites':True,'passwordRecovery':True,'paymentsProviderConfigured':bool(os.getenv('MERCADOPAGO_ACCESS_TOKEN','').strip())})
    except Exception as e:return jsonify({'ok':False,'error':str(e)}),500

@app.get('/api/search')
def search_api():
    q=str(request.args.get('q','')).strip().lower();cat=str(request.args.get('category','')).strip();minp=request.args.get('min',type=int);maxp=request.args.get('max',type=int);c=db();p=ph();conds=['1=1'];args=[]
    if q:conds.append(f'(lower(name) LIKE {p} OR lower(description) LIKE {p} OR lower(category) LIKE {p})');args += [f'%{q}%',f'%{q}%',f'%{q}%']
    if cat:conds.append(f'category={p}');args.append(cat)
    if minp is not None:conds.append(f'price>={p}');args.append(minp)
    if maxp is not None:conds.append(f'price<={p}');args.append(maxp)
    rs=c.execute('SELECT * FROM products WHERE '+' AND '.join(conds)+' ORDER BY created_at DESC',args).fetchall();c.close();return jsonify([product_dict(x) for x in rs])

@app.get('/sitemap.xml')
def sitemap():
    base='https://todivo-cl.onrender.com';urls=[base+'/',base+'/producto.html',base+'/checkout.html',base+'/registro.html',base+'/vendedor.html',base+'/seguimiento.html',base+'/privacy.html',base+'/terms.html',base+'/shipping.html',base+'/contact.html']
    try:
        c=db();rs=c.execute('SELECT id FROM products').fetchall();c.close();urls += [base+'/producto.html?p='+quote(str(x['id'])) for x in rs]
    except:pass
    xml=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']+[f'<url><loc>{u}</loc></url>' for u in dict.fromkeys(urls)]+['</urlset>'];return Response('\n'.join(xml),mimetype='application/xml')
@app.get('/robots.txt')
def robots():return Response('User-agent: *\nAllow: /\nDisallow: /panel.html\nDisallow: /admin.html\nDisallow: /pedidos.html\nDisallow: /api/\nSitemap: https://todivo-cl.onrender.com/sitemap.xml\n',mimetype='text/plain')

PUBLIC={'cuenta.html','index.html','producto.html','checkout.html','api.html','catalog.js','login.html','privacy.html','terms.html','shipping.html','contact.html','seguimiento.html','registro.html','vendedor.html','recuperar.html','googleff57496071cffa50.html','robots.txt','sitemap.xml'}
@app.get('/<path:filename>')
def files(filename):
    if filename.startswith('assets/') or filename in PUBLIC:
        target=BASE/filename
        if target.is_file():
            resp=send_from_directory(BASE,filename)
            if filename.startswith('assets/'):
                resp.headers['Cache-Control']='public, max-age=604800, immutable'
            else:
                resp.headers['Cache-Control']='no-cache'
            return resp
    return jsonify({'error':'No encontrado'}),404

if __name__=='__main__':app.run(host='127.0.0.1',port=5000,debug=True)
