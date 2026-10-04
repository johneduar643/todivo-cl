TODIVO CL — V33 MARKETPLACE

Esta versión amplía la base V32 para dejar una plataforma marketplace funcional y escalable.

Incluye:
- cuentas de clientes, perfil, direcciones, favoritos y notificaciones
- recuperación de contraseña mediante token (requiere proveedor de correo para envío real)
- solicitudes y portal de vendedores aprobados
- catálogo por vendedor y aislamiento de productos del vendedor
- administración de productos, pedidos, clientes y vendedores
- estadísticas administrativas
- pedidos asociados a cuentas cuando el cliente inició sesión
- seguimiento por código y correo existente
- reseñas de productos
- PostgreSQL en producción y SQLite para desarrollo local
- sitemap.xml y robots.txt
- integración preparada para Mercado Pago mediante MERCADOPAGO_ACCESS_TOKEN

IMPORTANTE:
- No se deben colocar credenciales privadas dentro del código ni del navegador.
- Para cobros reales, la cuenta de Mercado Pago y las credenciales deben ser administradas por el adulto responsable del negocio y configuradas como variables privadas en Render.
- La recuperación de contraseña necesita conectar un proveedor de correo para enviar tokens al usuario.
- El webhook de pagos debe validarse con firma del proveedor antes de considerarlo una integración de producción de alto nivel.
- No se garantiza aparecer primero en Google ni ventas: la indexación y el crecimiento dependen de Google, contenido, reputación, vendedores, inventario, precios y marketing.

Publicación recomendada:
1. Revisar esta versión.
2. Subir a GitHub.
3. Deploy en Render.
4. Verificar PostgreSQL, /api/health, catálogo, registro, login, pedidos y portal vendedor.
5. Configurar Mercado Pago y correo con credenciales privadas.
6. Volver a enviar sitemap en Search Console.
