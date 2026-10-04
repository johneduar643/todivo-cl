TODIVO CL V30 - CENTRO DE ADMINISTRACION REAL

Cambios principales:
- panel.html ahora es un centro unificado con Inicio, Productos, Pedidos, Inventario, Ventas y Configuracion.
- Productos se pueden crear, editar y eliminar desde el centro sin abrir otra pagina.
- Pedidos se consultan desde la API y permiten cambiar estado y eliminar.
- Inventario muestra stock bajo y unidades disponibles.
- Ventas calcula total, pedidos validos, ticket promedio, cancelaciones y productos vendidos.
- pedidos.html ya no usa localStorage: consulta la API y la base de datos del servidor.
- Incluye exportacion CSV de pedidos.
- Mantiene el acceso protegido del servidor.

IMPORTANTE:
Esta version es una base de despliegue. No elimina la V28. Primero prueba V30 en Render.
