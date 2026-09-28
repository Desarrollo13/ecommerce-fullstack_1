import { useEffect, useEffectEvent, useState } from 'react'
import './App.css'

const accessTokenKey = 'ecommerce-access-token'

async function api(path, options = {}, token = '') {
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: 'same-origin',
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
    const error = new Error(message || 'No se pudo completar la solicitud.')
    error.status = response.status
    throw error
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
  const [paymentOrder, setPaymentOrder] = useState(null)
  const [paymentOrderError, setPaymentOrderError] = useState('')
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function authenticatedApi(path, options = {}) {
    try {
      return await api(path, options, token)
    } catch (error) {
      if (error.status !== 401) throw error

      try {
        const session = await api('/auth/token/refresh/', { method: 'POST' })
        localStorage.setItem(accessTokenKey, session.access)
        setToken(session.access)
        return await api(path, options, session.access)
      } catch (refreshError) {
        localStorage.removeItem(accessTokenKey)
        setToken('')
        setCart(null)
        throw refreshError
      }
    }
  }

  useEffect(() => {
    api('/products/')
      .then(setProducts)
      .catch((error) => setMessage(error.message))
  }, [])

  const loadCart = useEffectEvent(async () => {
    try {
      setCart(await authenticatedApi('/cart/'))
    } catch (error) {
      setMessage(error.message)
    }
  })

  useEffect(() => {
    if (!token) return
    const timerId = window.setTimeout(loadCart, 0)
    return () => window.clearTimeout(timerId)
  }, [token])

  const paymentOrderId = Number(new URLSearchParams(window.location.search).get('order_id'))
  const paymentStatus = paymentOrder?.payment_status

  const loadPaymentOrder = useEffectEvent(async () => {
    try {
      setPaymentOrder(await authenticatedApi(`/orders/${paymentOrderId}/`))
      setPaymentOrderError('')
    } catch (error) {
      setPaymentOrderError(error.message)
    }
  })

  useEffect(() => {
    if (
      window.location.pathname !== '/payment-result'
      || !token
      || !Number.isInteger(paymentOrderId)
      || paymentOrderId < 1
      || (paymentStatus && paymentStatus !== 'pending')
    ) return

    const initialTimerId = window.setTimeout(loadPaymentOrder, 0)
    const intervalId = window.setInterval(loadPaymentOrder, 5000)
    return () => {
      window.clearTimeout(initialTimerId)
      window.clearInterval(intervalId)
    }
  }, [token, paymentOrderId, paymentStatus])

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
      await authenticatedApi('/cart/items/', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId, quantity: 1 }),
      })
      setCart(await authenticatedApi('/cart/'))
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
      await authenticatedApi(`/cart/items/${itemId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ quantity }),
      })
      setCart(await authenticatedApi('/cart/'))
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
      await authenticatedApi(`/cart/items/${itemId}/`, { method: 'DELETE' })
      setCart(await authenticatedApi('/cart/'))
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
      const order = await authenticatedApi('/orders/', {
        method: 'POST',
        body: JSON.stringify({
          shipping_address: shippingAddress,
          payment_method: paymentMethod,
        }),
      })

      if (paymentMethod === 'cash_on_delivery') {
        setCart(await authenticatedApi('/cart/'))
        setMessage(`Pedido #${order.id} creado. Pagarás al recibirlo.`)
        return
      }

      const preference = await authenticatedApi(`/orders/${order.id}/payment-preference/`, {
        method: 'POST',
      })
      const checkoutUrl = preference.checkout_url || preference.sandbox_init_point || preference.init_point
      if (!checkoutUrl) throw new Error('Mercado Pago no devolvió una URL de pago.')
      window.location.assign(checkoutUrl)
    } catch (error) {
      setMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  async function logout() {
    try {
      await api('/auth/logout/', { method: 'POST' })
    } finally {
      localStorage.removeItem(accessTokenKey)
      setToken('')
      setCart(null)
      setMessage('Sesión cerrada.')
    }
  }

  const items = cart?.items || []
  const total = items.reduce(
    (sum, item) => sum + Number(item.product.price) * item.quantity,
    0,
  )

  if (window.location.pathname === '/payment-result') {
    const hasPaymentOrderId = Number.isInteger(paymentOrderId) && paymentOrderId > 0
    const paymentConfirmed = paymentOrder?.payment_status === 'paid'
    return (
      <main className="payment-result">
        <p className="eyebrow">ESTADO DEL PAGO</p>
        <h1>{paymentConfirmed ? 'Tu pago fue confirmado.' : 'Estamos verificando tu pago.'}</h1>
        <p>{paymentConfirmed ? 'Recibimos tu pago y prepararemos tu pedido.' : 'Mercado Pago confirma el resultado mediante el webhook.'}</p>
        {!hasPaymentOrderId && <p className="notice">No encontramos el pedido asociado al pago.</p>}
        {!token && <p className="notice">Iniciá sesión en la tienda para consultar tu pedido.</p>}
        {token && hasPaymentOrderId && !paymentOrder && !paymentOrderError && <p className="muted">Cargando tu pedido...</p>}
        {paymentOrderError && <p className="notice">{paymentOrderError}</p>}
        {paymentOrder && (
          <article className="order-card">
            <div><span>Pedido #{paymentOrder.id}</span><strong>{formatPrice(paymentOrder.total)}</strong></div>
            <p>Pago: <b>{paymentOrder.payment_status}</b> · Estado del pedido: <b>{paymentOrder.status}</b></p>
            {paymentOrder.payment_status === 'pending' && <p className="muted">Actualizamos este estado automáticamente.</p>}
          </article>
        )}
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
            onClick={logout}
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
