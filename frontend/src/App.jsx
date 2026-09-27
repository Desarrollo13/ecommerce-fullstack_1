import { useEffect, useState } from 'react'
import './App.css'

const accessTokenKey = 'ecommerce-access-token'

async function api(path, options = {}, token = '') {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (response.status === 204) return null

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const message = data.detail || Object.values(data).flat().join(' ')
    throw new Error(message || 'No se pudo completar la solicitud.')
  }
  return data
}

function formatPrice(value) {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
  }).format(value)
}

function App() {
  const [products, setProducts] = useState([])
  const [cart, setCart] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem(accessTokenKey) || '')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [shippingAddress, setShippingAddress] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('card')
  const [orders, setOrders] = useState([])
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    api('/products/')
      .then(setProducts)
      .catch((error) => setMessage(error.message))
  }, [])

  useEffect(() => {
    if (!token) return

    api('/cart/', {}, token)
      .then(setCart)
      .catch((error) => {
        localStorage.removeItem(accessTokenKey)
        setToken('')
        setMessage(error.message)
      })
  }, [token])

  useEffect(() => {
    if (window.location.pathname !== '/payment-result' || !token) return

    api('/orders/', {}, token)
      .then(setOrders)
      .catch((error) => setMessage(error.message))
  }, [token])

  async function login(event) {
    event.preventDefault()
    setIsLoading(true)
    setMessage('')
    try {
      const session = await api('/auth/token/', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      localStorage.setItem(accessTokenKey, session.access)
      setToken(session.access)
      setPassword('')
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function addToCart(productId) {
    if (!token) {
      setMessage('Iniciá sesión para agregar productos al carrito.')
      return
    }
    setIsLoading(true)
    setMessage('')
    try {
      await api('/cart/items/', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId, quantity: 1 }),
      }, token)
      setCart(await api('/cart/', {}, token))
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function updateQuantity(itemId, quantity) {
    if (quantity < 1) return removeFromCart(itemId)
    setIsLoading(true)
    setMessage('')
    try {
      await api(`/cart/items/${itemId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ quantity }),
      }, token)
      setCart(await api('/cart/', {}, token))
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function removeFromCart(itemId) {
    setIsLoading(true)
    setMessage('')
    try {
      await api(`/cart/items/${itemId}/`, { method: 'DELETE' }, token)
      setCart(await api('/cart/', {}, token))
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function checkout(event) {
    event.preventDefault()
    setIsLoading(true)
    setMessage('')
    try {
      const order = await api('/orders/', {
        method: 'POST',
        body: JSON.stringify({
          shipping_address: shippingAddress,
          payment_method: paymentMethod,
        }),
      }, token)

      if (paymentMethod === 'cash_on_delivery') {
        setCart(await api('/cart/', {}, token))
        setMessage(`Pedido #${order.id} creado. Pagarás al recibirlo.`)
        return
      }

      const preference = await api(`/orders/${order.id}/payment-preference/`, {
        method: 'POST',
      }, token)
      const checkoutUrl = preference.sandbox_init_point || preference.init_point
      if (!checkoutUrl) throw new Error('Mercado Pago no devolvió una URL de pago.')
      window.location.assign(checkoutUrl)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  const items = cart?.items || []
  const total = items.reduce(
    (sum, item) => sum + Number(item.product.price) * item.quantity,
    0,
  )

  if (window.location.pathname === '/payment-result') {
    return (
      <main className="payment-result">
        <p className="eyebrow">PAGO RECIBIDO</p>
        <h1>Estamos verificando tu pago.</h1>
        <p>Mercado Pago confirma el resultado mediante el webhook. Este listado muestra el estado real de tus pedidos.</p>
        {!token && <p className="notice">Iniciá sesión en la tienda para consultar tu pedido.</p>}
        {token && orders.length === 0 && <p className="muted">Cargando tus pedidos...</p>}
        {orders.map((order) => (
          <article className="order-card" key={order.id}>
            <div><span>Pedido #{order.id}</span><strong>{formatPrice(order.total)}</strong></div>
            <p>Pago: <b>{order.payment_status}</b> · Pedido: <b>{order.status}</b></p>
          </article>
        ))}
        <a className="button" href="/">Volver a la tienda</a>
      </main>
    )
  }

  return (
    <main className="storefront">
      <header className="topbar">
        <div>
          <p className="eyebrow">TIENDA ONLINE</p>
          <h1>Mercado local, compra simple.</h1>
        </div>
        {token ? (
          <button
            className="button secondary"
            type="button"
            onClick={() => {
              localStorage.removeItem(accessTokenKey)
              setToken('')
              setCart(null)
              setMessage('Sesión cerrada.')
            }}
          >
            Cerrar sesión
          </button>
        ) : (
          <form className="login" onSubmit={login}>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Email"
              required
            />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Contraseña"
              required
            />
            <button className="button" disabled={isLoading}>Ingresar</button>
          </form>
        )}
      </header>

      {message && <p className="notice" role="status">{message}</p>}

      <div className="content">
        <section className="catalog" aria-labelledby="catalog-title">
          <div className="section-heading">
            <p className="eyebrow">CATÁLOGO</p>
            <h2 id="catalog-title">Productos disponibles</h2>
          </div>
          <div className="product-grid">
            {products.map((product) => (
              <article className="product-card" key={product.id}>
                <div className="product-image">
                  {product.image ? <img src={product.image} alt={product.name} /> : product.name.slice(0, 1)}
                </div>
                <h3>{product.name}</h3>
                <p>{product.description || 'Producto seleccionado para tu compra.'}</p>
                <div className="product-footer">
                  <strong>{formatPrice(product.price)}</strong>
                  <button className="button small" onClick={() => addToCart(product.id)} disabled={isLoading}>
                    Agregar
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="checkout-panel" aria-labelledby="checkout-title">
          <p className="eyebrow">TU COMPRA</p>
          <h2 id="checkout-title">Carrito</h2>
          {!token && <p className="muted">Iniciá sesión para armar tu pedido.</p>}
          {token && items.length === 0 && <p className="muted">Tu carrito está vacío.</p>}
          {items.map((item) => (
            <div className="cart-item" key={item.id}>
              <div>
                <strong>{item.product.name}</strong>
                <span>{formatPrice(item.product.price)}</span>
              </div>
              <div className="quantity">
                <button aria-label={`Quitar una unidad de ${item.product.name}`} onClick={() => updateQuantity(item.id, item.quantity - 1)} disabled={isLoading}>-</button>
                <span>{item.quantity}</span>
                <button aria-label={`Agregar una unidad de ${item.product.name}`} onClick={() => updateQuantity(item.id, item.quantity + 1)} disabled={isLoading}>+</button>
              </div>
            </div>
          ))}

          {token && items.length > 0 && (
            <form className="checkout-form" onSubmit={checkout}>
              <div className="total"><span>Total</span><strong>{formatPrice(total)}</strong></div>
              <label>
                Dirección de envío
                <textarea
                  value={shippingAddress}
                  onChange={(event) => setShippingAddress(event.target.value)}
                  placeholder="Calle, número, ciudad y provincia"
                  required
                />
              </label>
              <label>
                Medio de pago
                <select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}>
                  <option value="card">Mercado Pago: tarjeta</option>
                  <option value="bank_transfer">Mercado Pago: transferencia</option>
                  <option value="cash_on_delivery">Efectivo al recibir</option>
                </select>
              </label>
              <button className="button checkout-button" disabled={isLoading}>
                {isLoading ? 'Procesando...' : paymentMethod === 'cash_on_delivery' ? 'Confirmar pedido' : 'Ir a Mercado Pago'}
              </button>
            </form>
          )}
        </aside>
      </div>
    </main>
  )
}

export default App
