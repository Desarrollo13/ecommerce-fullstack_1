# E-commerce Full Stack

Tienda online construida con Django REST Framework y React. El backend administra el catalogo, carrito, pedidos, pagos con Mercado Pago e imagenes de productos en Cloudinary. El storefront se sirve desde Django en produccion.

Produccion: `https://ecommerce-api-rysy.onrender.com`

## Flujo Operativo

### Catalogo

1. Un administrador crea categorias y productos desde Django admin.
2. Las imagenes de productos se almacenan en Cloudinary, no en el disco temporal de Render.
3. El catalogo y sus imagenes son publicos en la tienda.

### Compra Y Pago

1. El cliente se registra o inicia sesion.
2. Agrega productos al carrito y confirma direccion y medio de pago.
3. El backend valida el stock en una transaccion, crea el pedido, descuenta el stock y reserva el pedido online durante 30 minutos.
4. Para tarjeta o transferencia, se crea una preferencia de Mercado Pago y el cliente es redirigido a su checkout.
5. Mercado Pago notifica el resultado mediante un webhook validado por el backend.
6. Solo un pago aprobado con referencia e importe coincidentes cambia el estado de pago a `paid`.

### Pagos Rechazados Y Reservas Vencidas

- Un webhook de Mercado Pago con estado `rejected` o `cancelled` cambia el pago a `failed`; el cliente ve el resultado y puede volver a la tienda para intentarlo nuevamente.
- El stock queda reservado durante 30 minutos para pagos con tarjeta o transferencia. Si no se acredita un pago, `expire_payment_reservations` cancela el pedido pendiente y devuelve las unidades al stock.
- Para validar este caso en sandbox, completar un checkout con un pago rechazado o cancelado y confirmar en `/admin/` que el pedido conserva estado `pending` y pago `failed`. Para comprobar la reposicion de stock sin esperar, se puede usar un pedido de prueba con una reserva vencida en un entorno local.

### Preparacion Y Entrega

El pago se confirma automaticamente, pero la logistica se actualiza manualmente desde Django admin. Esto evita marcar un pedido como preparado o enviado sin que haya ocurrido fisicamente.

Estados del pedido:

```text
pending -> processing -> shipped -> delivered
```

- `pending`: pedido creado, a la espera de pago o de inicio de preparacion.
- `processing`: pago acreditado y pedido en preparacion.
- `shipped`: pedido despachado.
- `delivered`: pedido entregado.
- `cancelled`: pedido cancelado. Un pedido pagado requiere reembolso previo antes de cancelarse.

Los administradores deben cambiar estos estados desde `/admin/`. El sistema solo permite pasar a `processing` si el pago figura como `paid`.

### Notificaciones Por Email

El sistema notifica al cliente cuando crea su cuenta, se acredita un pago y el pedido es despachado o entregado. Para entregarlas en produccion se debe configurar un proveedor SMTP mediante las variables documentadas en `backend/.env.example` y `backend/DEPLOYMENT.md`. Si `EMAIL_HOST` no esta configurado, los emails solo se imprimen en los logs locales o de Render.

## Ejecucion Local

Backend, desde `backend/`:

```powershell
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver
```

Frontend, desde `frontend/`:

```powershell
npm.cmd run dev
```

El servidor de Vite redirige `/api` al backend local. Para las variables necesarias en desarrollo y produccion, consultar `backend/.env.example` y `backend/DEPLOYMENT.md`. Nunca se deben versionar credenciales, secretos de Mercado Pago ni credenciales de Cloudinary.

## Verificacion

```powershell
# Desde backend/
..\venv\Scripts\python.exe manage.py test users cart orders products

# Desde frontend/
npm.cmd run lint
npm.cmd run build
```
