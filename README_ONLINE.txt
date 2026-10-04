TODIVO CL V26 - LISTO PARA PUBLICAR

Esta versión agrega la configuración necesaria para desplegar el backend Flask en Render.

Build:
pip install -r requirements.txt

Start:
gunicorn server:app

IMPORTANTE:
La base de datos actual es SQLite. En un servicio gratuito de Render el sistema de archivos es temporal,
por lo que SQLite NO debe usarse como almacenamiento definitivo de pedidos/productos en producción.
Para una tienda real, el siguiente paso es migrar a PostgreSQL antes de publicar oficialmente.

No incluyas contraseñas, tokens ni claves privadas en el repositorio.
