/**
 * SCENTED BUBBLES - CLIENT-SIDE CART MANAGER
 * Architecture Rule: Cart is stored in localStorage as [{variant_id, qty}] ONLY.
 * No prices or discounts are stored in browser storage.
 * Pricing, stocks, and totals are fetched strictly from POST /cart/summary.
 */

const ScentedCart = (function() {
  const STORAGE_KEY = 'sb_guest_cart_v1';

  function getCart() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed
          .filter(item => item && item.variant_id && item.qty > 0)
          .map(item => ({ variant_id: parseInt(item.variant_id, 10), qty: parseInt(item.qty, 10) }));
      }
      return [];
    } catch (e) {
      console.warn('Error reading cart from localStorage:', e);
      return [];
    }
  }

  function saveCart(items) {
    try {
      const sanitized = items
        .filter(item => item && item.variant_id && item.qty > 0)
        .map(item => ({ variant_id: parseInt(item.variant_id, 10), qty: parseInt(item.qty, 10) }));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized));
      updateBadge();
    } catch (e) {
      console.error('Error saving cart:', e);
    }
  }

  function addItem(variantId, qty = 1) {
    const vid = parseInt(variantId, 10);
    const quantity = parseInt(qty, 10) || 1;
    if (!vid || quantity <= 0) return;

    const cart = getCart();
    const existing = cart.find(item => item.variant_id === vid);
    if (existing) {
      existing.qty += quantity;
    } else {
      cart.push({ variant_id: vid, qty: quantity });
    }
    saveCart(cart);
    showToast('Added to bag');
  }

  function updateItemQty(variantId, newQty) {
    const vid = parseInt(variantId, 10);
    const quantity = parseInt(newQty, 10);
    let cart = getCart();

    if (quantity <= 0) {
      cart = cart.filter(item => item.variant_id !== vid);
    } else {
      const target = cart.find(item => item.variant_id === vid);
      if (target) {
        target.qty = quantity;
      }
    }
    saveCart(cart);
  }

  function removeItem(variantId) {
    const vid = parseInt(variantId, 10);
    let cart = getCart();
    cart = cart.filter(item => item.variant_id !== vid);
    saveCart(cart);
  }

  function clearCart() {
    localStorage.removeItem(STORAGE_KEY);
    updateBadge();
  }

  function getTotalCount() {
    const cart = getCart();
    return cart.reduce((sum, item) => sum + item.qty, 0);
  }

  function updateBadge() {
    const badges = document.querySelectorAll('.cart-badge');
    const count = getTotalCount();
    badges.forEach(b => {
      b.textContent = count;
      b.style.display = count > 0 ? 'flex' : 'none';
    });
  }

  async function fetchSummary() {
    const cart = getCart();
    if (!cart.length) {
      return {
        lines: [],
        subtotal: '0.00',
        delivery_charge: '0.00',
        total: '0.00',
        is_valid: false,
        item_count: 0
      };
    }

    try {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      const response = await fetch('/cart/summary', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken || ''
        },
        body: JSON.stringify({ items: cart })
      });
      if (!response.ok) throw new Error('Failed to fetch cart summary');
      return await response.json();
    } catch (err) {
      console.error('Cart summary error:', err);
      return null;
    }
  }

  function showToast(message) {
    let toast = document.getElementById('sb-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'sb-toast';
      toast.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        background: #242220;
        color: #FAF8F5;
        padding: 12px 20px;
        border-radius: 9999px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        z-index: 9999;
        transition: opacity 0.3s ease, transform 0.3s ease;
        opacity: 0;
        transform: translateY(10px);
        border: 1px solid #C5A059;
      `;
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
    }, 2400);
  }

  // Auto-initialize badge on page load
  document.addEventListener('DOMContentLoaded', () => {
    updateBadge();

    // Delegate "Add to Cart" button clicks
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-add-cart]');
      if (btn) {
        e.preventDefault();
        const variantId = btn.getAttribute('data-variant-id');
        const qtyInput = document.querySelector('[data-qty-input]');
        const qty = qtyInput ? parseInt(qtyInput.value, 10) : 1;
        if (variantId) {
          addItem(variantId, qty);
        }
      }
    });
  });

  return {
    getCart,
    addItem,
    updateItemQty,
    removeItem,
    clearCart,
    getTotalCount,
    updateBadge,
    fetchSummary,
    showToast
  };
})();
