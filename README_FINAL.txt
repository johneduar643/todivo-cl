TODIVO CL - VERSION FINAL DE PREPARACION

Esta version deja lista la tienda para pruebas y para publicar en Render.

INICIO LOCAL:
1. Ejecuta INICIAR_TODIVO_LOCAL.bat.
2. Se abrira la tienda en http://127.0.0.1:5000/.
3. Administracion: http://127.0.0.1:5000/login.html

RENDER:
- DATABASE_URL: URL privada de PostgreSQL de Render.
- ADMIN_PASSWORD: contraseña privada del administrador.
- ADMIN_SESSION_SECRET: secreto aleatorio privado recomendado.
- MERCADOPAGO_ACCESS_TOKEN: opcional; la integracion de pago real debe activarse despues de que el adulto responsable tenga las credenciales oficiales.

ADMINISTRACION:
- Productos: crear, editar y eliminar.
- Pedidos: ver, cambiar estado y eliminar.
- Inventario: stock bajo y unidades.
- Ventas: resumen y productos vendidos.
- Exportacion CSV de pedidos.
- Configuracion y estado del sistema.

SEO:
- /robots.txt
- /sitemap.xml dinamico
- Meta description y estructura base para buscadores.

PAGO:
El checkout sigue siendo de prueba. No solicita ni almacena numeros de tarjeta. No habilites cobros reales hasta configurar una pasarela oficial y probarla con el adulto responsable.

IMPORTANTE:
La contraseña incluida en el BAT es solo para pruebas locales. No subas el BAT a GitHub. En produccion usa ADMIN_PASSWORD y ADMIN_SESSION_SECRET en Render.
