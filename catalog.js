const TODIVO_CATALOG_KEY='todivoCatalog';
const TODIVO_API='/api/products';
const TODIVO_DEFAULT_PRODUCTS=[
{id:'audifonos-bluetooth',name:'Audífonos Bluetooth Inalámbricos',category:'Tecnología',price:29990,oldPrice:39990,stock:25,tag:'Oferta',image:'assets/producto_1.svg',description:'Audífonos inalámbricos con conexión Bluetooth y estuche de carga.',features:['Bluetooth','Micrófono integrado','Estuche de carga']},
{id:'smartwatch-active',name:'Smartwatch Active',category:'Tecnología',price:34990,oldPrice:44990,stock:18,tag:'Oferta',image:'assets/producto_2.svg',description:'Smartwatch para actividades diarias con pantalla digital.',features:['Pantalla digital','Notificaciones','Seguimiento de actividad']},
{id:'control-gamer-wireless',name:'Control Gamer Wireless',category:'Gaming',price:24990,oldPrice:31990,stock:14,tag:'Oferta',image:'assets/producto_3.svg',description:'Control inalámbrico para disfrutar tus juegos con comodidad.',features:['Wireless','Vibración','Diseño ergonómico']},
{id:'mini-proyector-hd',name:'Mini Proyector HD',category:'Tecnología',price:49990,oldPrice:59990,stock:9,tag:'Oferta',image:'assets/producto_4.svg',description:'Mini proyector compacto para entretenimiento en casa.',features:['HD','Compacto','Entrada multimedia']},
{id:'teclado-mecanico-rgb',name:'Teclado Mecánico RGB',category:'Gaming',price:39990,oldPrice:49990,stock:12,tag:'Oferta',image:'assets/producto_5.svg',description:'Teclado mecánico con iluminación RGB para gaming y trabajo.',features:['RGB','Teclas mecánicas','USB']},
{id:'mouse-gamer-pro',name:'Mouse Gamer Pro',category:'Gaming',price:19990,oldPrice:27990,stock:20,tag:'Oferta',image:'assets/producto_6.svg',description:'Mouse gamer preciso para sesiones de juego y trabajo.',features:['Alta precisión','Botones configurables','USB']},
{id:'lampara-led-smart',name:'Lámpara LED Smart',category:'Hogar',price:16990,oldPrice:22990,stock:30,tag:'Oferta',image:'assets/producto_7.svg',description:'Lámpara LED moderna para escritorio y dormitorio.',features:['LED','Ahorro de energía','Diseño moderno']},
{id:'mochila-urbana',name:'Mochila Urbana',category:'Moda',price:27990,oldPrice:34990,stock:16,tag:'Oferta',image:'assets/producto_8.svg',description:'Mochila práctica para uso diario.',features:['Compartimentos','Uso diario','Diseño urbano']},
{id:'parlante-bluetooth',name:'Parlante Bluetooth',category:'Tecnología',price:25990,oldPrice:32990,stock:21,tag:'Oferta',image:'assets/producto_9.svg',description:'Parlante portátil para música y entretenimiento.',features:['Bluetooth','Portátil','Batería recargable']},
{id:'organizador-multiuso',name:'Organizador Multiuso',category:'Hogar',price:12990,oldPrice:17990,stock:35,tag:'Oferta',image:'assets/producto_10.svg',description:'Organizador práctico para mantener tus espacios ordenados.',features:['Multiuso','Compacto','Fácil de limpiar']}];
function todovSlug(name){return String(name).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');}
function todovGetCatalog(){try{const x=JSON.parse(localStorage.getItem(TODIVO_CATALOG_KEY)||'null');if(Array.isArray(x)&&x.length)return x;}catch(e){}return TODIVO_DEFAULT_PRODUCTS.slice();}
function todovSaveCatalog(products){localStorage.setItem(TODIVO_CATALOG_KEY,JSON.stringify(products));}
function todovResetCatalog(){localStorage.removeItem(TODIVO_CATALOG_KEY);return todovGetCatalog();}
function todovMoney(n){return '$'+Number(n||0).toLocaleString('es-CL');}
async function todovApiProducts(){const r=await fetch(TODIVO_API,{cache:'no-store'});if(!r.ok)throw new Error('API products '+r.status);return await r.json();}
async function todovApiCreateProduct(p){const r=await fetch(TODIVO_API,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});const d=await r.json();if(!r.ok)throw new Error(d.error||'No se pudo crear');return d;}
async function todovApiUpdateProduct(id,p){const r=await fetch(TODIVO_API+'/'+encodeURIComponent(id),{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});const d=await r.json();if(!r.ok)throw new Error(d.error||'No se pudo actualizar');return d;}
async function todovApiDeleteProduct(id){const r=await fetch(TODIVO_API+'/'+encodeURIComponent(id),{method:'DELETE'});const d=await r.json();if(!r.ok)throw new Error(d.error||'No se pudo eliminar');return d;}
