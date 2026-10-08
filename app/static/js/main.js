/**
 * SCENTED BUBBLES - MAIN CLIENT SCRIPT
 * Debounced live search, mobile menu, variant selector
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Debounced Live Search
  const searchInput = document.getElementById('site-search-input');
  const searchDropdown = document.getElementById('search-results-dropdown');

  if (searchInput && searchDropdown) {
    let debounceTimer = null;

    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim();
      clearTimeout(debounceTimer);

      if (query.length < 2) {
        searchDropdown.style.display = 'none';
        searchDropdown.innerHTML = '';
        return;
      }

      debounceTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/search?q=${encodeURIComponent(query)}`);
          if (!res.ok) return;
          const items = await res.json();

          if (items.length === 0) {
            searchDropdown.innerHTML = '<div style="padding: 12px; font-size: 13px; color: #888; text-align: center;">No fragrances found</div>';
            searchDropdown.style.display = 'block';
            return;
          }

          searchDropdown.innerHTML = items.map(item => `
            <a href="/products/${item.slug}" class="live-search-item">
              <img src="${item.thumbnail}" alt="${item.name}">
              <div>
                <div style="font-weight: 600; font-size: 14px; color: #222;">${item.name}</div>
                ${item.inspired_by ? `<div style="font-size: 11px; color: #8C6D23; font-weight: 600;">✨ ${item.inspired_by.toLowerCase().startsWith('inspired') ? item.inspired_by : 'Inspired by ' + item.inspired_by}</div>` : ''}
                <div style="font-size: 13px; color: #C5A059;">₹${item.price.toFixed(2)}</div>
              </div>
            </a>
          `).join('');
          searchDropdown.style.display = 'block';
        } catch (err) {
          console.error('Search error:', err);
        }
      }, 300); // 300ms debounce as specified in performance rules
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (query) {
          window.location.href = `/products?q=${encodeURIComponent(query)}`;
        }
      }
    });

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
        searchDropdown.style.display = 'none';
      }
    });
  }

  // 2. Mobile Side Panel Navigation Drawer
  const mobileToggleBtn = document.getElementById('mobile-menu-toggle');
  const mobileDrawer = document.getElementById('mobile-drawer');
  const drawerOverlay = document.getElementById('mobile-drawer-overlay');
  const drawerCloseBtn = document.getElementById('mobile-drawer-close');

  function openMobileDrawer() {
    if (mobileDrawer && drawerOverlay) {
      mobileDrawer.classList.add('active');
      drawerOverlay.classList.add('active');
      mobileDrawer.setAttribute('aria-hidden', 'false');
      drawerOverlay.setAttribute('aria-hidden', 'false');
      if (mobileToggleBtn) mobileToggleBtn.setAttribute('aria-expanded', 'true');
      document.body.classList.add('drawer-open');
    }
  }

  function closeMobileDrawer() {
    if (mobileDrawer && drawerOverlay) {
      mobileDrawer.classList.remove('active');
      drawerOverlay.classList.remove('active');
      mobileDrawer.setAttribute('aria-hidden', 'true');
      drawerOverlay.setAttribute('aria-hidden', 'true');
      if (mobileToggleBtn) mobileToggleBtn.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('drawer-open');
    }
  }

  if (mobileToggleBtn) {
    mobileToggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      openMobileDrawer();
    });
  }

  if (drawerCloseBtn) {
    drawerCloseBtn.addEventListener('click', closeMobileDrawer);
  }

  if (drawerOverlay) {
    drawerOverlay.addEventListener('click', closeMobileDrawer);
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMobileDrawer();
  });

  // 3. Floating Smart Header (Hide on scroll down, reveal on scroll up for mobile, iPad, & all screens)
  const siteHeader = document.getElementById('site-header') || document.querySelector('.site-header');
  const headerWrapper = document.getElementById('header-wrapper');
  if (siteHeader) {
    let lastScrollY = Math.max(0, window.pageYOffset || document.documentElement.scrollTop);
    let ticking = false;
    const SCROLL_THRESHOLD = 8; // min delta px to avoid micro-jitter
    const TOP_OFFSET = 60; // offset before hide/reveal activates

    function updateHeaderOnScroll() {
      const currentScrollY = Math.max(0, window.pageYOffset || document.documentElement.scrollTop);
      const maxScrollY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);

      // Guard: do not hide header if mobile drawer is open, search is focused, or search dropdown is open
      const isDrawerOpen = document.body.classList.contains('drawer-open') || 
                           (mobileDrawer && mobileDrawer.classList.contains('active'));
      const isSearchFocused = searchInput && document.activeElement === searchInput;
      const isSearchOpen = searchDropdown && searchDropdown.style.display === 'block';

      if (isDrawerOpen || isSearchFocused || isSearchOpen) {
        lastScrollY = currentScrollY;
        ticking = false;
        return;
      }

      // Near top of page: restore default non-floating flow
      if (currentScrollY <= 15) {
        siteHeader.classList.remove('header-hidden');
        siteHeader.classList.remove('header-floating');
        if (headerWrapper) headerWrapper.style.minHeight = '';
        lastScrollY = currentScrollY;
        ticking = false;
        return;
      }

      // Avoid edge bouncing at page bottom
      if (currentScrollY >= maxScrollY - 20) {
        lastScrollY = currentScrollY;
        ticking = false;
        return;
      }

      const delta = currentScrollY - lastScrollY;

      // Lock wrapper height once scrolled to prevent page layout jump
      if (headerWrapper && (!headerWrapper.style.minHeight || headerWrapper.style.minHeight === '0px')) {
        headerWrapper.style.minHeight = siteHeader.offsetHeight + 'px';
      }

      // Check threshold to avoid micro-scroll jitter
      if (Math.abs(delta) >= SCROLL_THRESHOLD) {
        if (delta > 0 && currentScrollY > TOP_OFFSET) {
          // Scrolling DOWN -> smoothly hide header
          siteHeader.classList.add('header-hidden');
          siteHeader.classList.remove('header-floating');
        } else if (delta < 0) {
          // Scrolling UP -> smoothly reveal floating header
          siteHeader.classList.remove('header-hidden');
          siteHeader.classList.add('header-floating');
        }
        lastScrollY = currentScrollY;
      }

      ticking = false;
    }

    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(updateHeaderOnScroll);
        ticking = true;
      }
    }, { passive: true });
  }

  // Gallery thumbnail selection and carousel
  window.selectProductImage = function(thumbEl, imageUrl, imageSrcset) {
    const mainImg = document.getElementById('main-product-img');
    if (mainImg) {
      mainImg.src = imageUrl;
      if (imageSrcset) mainImg.srcset = imageSrcset;
    }
    const thumbs = document.querySelectorAll('.gallery-thumb-item');
    thumbs.forEach(t => t.classList.remove('active'));
    if (thumbEl) thumbEl.classList.add('active');
  };

  const thumbPrevBtn = document.getElementById('gallery-prev-btn');
  const thumbNextBtn = document.getElementById('gallery-next-btn');
  const thumbsContainer = document.getElementById('gallery-thumbs-container');
  if (thumbPrevBtn && thumbsContainer) {
    thumbPrevBtn.addEventListener('click', () => {
      thumbsContainer.scrollBy({ left: -80, behavior: 'smooth' });
    });
  }
  if (thumbNextBtn && thumbsContainer) {
    thumbNextBtn.addEventListener('click', () => {
      thumbsContainer.scrollBy({ left: 80, behavior: 'smooth' });
    });
  }

  // 3. Product Detail Variant Selector
  const variantBtns = document.querySelectorAll('.variant-btn');
  const priceDisplay = document.getElementById('product-detail-price');
  const mrpDisplay = document.getElementById('product-detail-mrp');
  const discountDisplay = document.getElementById('product-detail-discount');
  const skuDisplay = document.getElementById('product-detail-sku');
  const addCartBtn = document.getElementById('product-detail-add-cart');
  const buyNowBtn = document.getElementById('product-detail-buy-now');
  const stockNotice = document.getElementById('product-stock-notice');

  variantBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      variantBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const price = btn.getAttribute('data-price');
      const discountedPrice = btn.getAttribute('data-discounted-price');
      const discountPct = btn.getAttribute('data-discount-pct');
      const sku = btn.getAttribute('data-sku');
      const variantId = btn.getAttribute('data-id');
      const stock = parseInt(btn.getAttribute('data-stock'), 10);

      if (priceDisplay) {
        priceDisplay.textContent = `₹${parseFloat(discountedPrice || price).toFixed(2)}`;
      }
      if (mrpDisplay) {
        if (discountedPrice && parseFloat(discountedPrice) < parseFloat(price)) {
          mrpDisplay.textContent = `₹${parseFloat(price).toFixed(2)}`;
          mrpDisplay.style.display = 'inline';
        } else {
          mrpDisplay.style.display = 'none';
        }
      }
      if (discountDisplay) {
        if (discountPct && parseInt(discountPct, 10) > 0) {
          discountDisplay.textContent = `${discountPct}% OFF`;
          discountDisplay.style.display = 'inline-block';
        } else {
          discountDisplay.style.display = 'none';
        }
      }
      if (skuDisplay) skuDisplay.textContent = sku;
      if (addCartBtn) addCartBtn.setAttribute('data-variant-id', variantId);
      if (buyNowBtn) buyNowBtn.setAttribute('data-variant-id', variantId);

      const lowStockAlert = document.getElementById('product-low-stock-alert');
      const lowStockCount = document.getElementById('low-stock-count');
      const outOfStockAlert = document.getElementById('product-out-of-stock-alert');
      const qtyContainer = document.getElementById('product-qty-container');
      const qtyInput = document.getElementById('product-qty-input');

      if (stock === 0) {
        if (stockNotice) {
          stockNotice.innerHTML = '<span style="color: #C62828; font-weight: 700; display: inline-flex; align-items: center; gap: 0.35rem;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #C62828;"></span> Out of Stock (Currently Unavailable)</span>';
        }
        if (lowStockAlert) lowStockAlert.style.display = 'none';
        if (outOfStockAlert) outOfStockAlert.style.display = 'flex';
        if (addCartBtn) {
          addCartBtn.disabled = true;
          addCartBtn.textContent = 'Out of Stock';
        }
        if (buyNowBtn) {
          buyNowBtn.disabled = true;
          buyNowBtn.textContent = 'Sold Out';
        }
        if (qtyContainer) {
          qtyContainer.style.opacity = '0.5';
          qtyContainer.style.pointerEvents = 'none';
        }
      } else if (stock <= 5) {
        if (stockNotice) {
          stockNotice.innerHTML = `<span style="color: #E65100; font-weight: 700; display: inline-flex; align-items: center; gap: 0.35rem;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #E65100; box-shadow: 0 0 6px #E65100;"></span> Low Stock (Only ${stock} remaining &mdash; Grab yours now!)</span>`;
        }
        if (lowStockCount) lowStockCount.textContent = stock;
        if (lowStockAlert) lowStockAlert.style.display = 'flex';
        if (outOfStockAlert) outOfStockAlert.style.display = 'none';
        if (addCartBtn) {
          addCartBtn.disabled = false;
          addCartBtn.textContent = 'Add to Bag';
        }
        if (buyNowBtn) {
          buyNowBtn.disabled = false;
          buyNowBtn.textContent = 'Buy Now';
        }
        if (qtyContainer) {
          qtyContainer.style.opacity = '1';
          qtyContainer.style.pointerEvents = 'auto';
        }
        if (qtyInput) {
          qtyInput.setAttribute('max', Math.min(stock, 10));
          if (parseInt(qtyInput.value, 10) > stock) {
            qtyInput.value = stock;
          }
        }
      } else {
        if (stockNotice) {
          stockNotice.innerHTML = '<span style="color: #2E7D32; font-weight: 600; display: inline-flex; align-items: center; gap: 0.35rem;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #2E7D32;"></span> In Stock (Ready to Dispatch)</span>';
        }
        if (lowStockAlert) lowStockAlert.style.display = 'none';
        if (outOfStockAlert) outOfStockAlert.style.display = 'none';
        if (addCartBtn) {
          addCartBtn.disabled = false;
          addCartBtn.textContent = 'Add to Bag';
        }
        if (buyNowBtn) {
          buyNowBtn.disabled = false;
          buyNowBtn.textContent = 'Buy Now';
        }
        if (qtyContainer) {
          qtyContainer.style.opacity = '1';
          qtyContainer.style.pointerEvents = 'auto';
        }
        if (qtyInput) {
          qtyInput.setAttribute('max', 10);
        }
      }
    });
  });

  // Buy Now Button Handler
  if (buyNowBtn) {
    buyNowBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const variantId = buyNowBtn.getAttribute('data-variant-id');
      const qtyInput = document.querySelector('[data-qty-input]');
      const qty = qtyInput ? parseInt(qtyInput.value, 10) : 1;
      if (variantId) {
        ScentedCart.addItem(variantId, qty);
        window.location.href = '/checkout';
      }
    });
  }

  // 4. Hero Slider Automatic Multi-Slide & Manual Controls
  (function initHeroSlider() {
    const slider = document.getElementById('hero-slider');
    if (!slider) return;

    const slides = slider.querySelectorAll('.hero-slide');
    const dots = slider.querySelectorAll('.hero-dot');
    const prevBtn = document.getElementById('hero-prev');
    const nextBtn = document.getElementById('hero-next');

    if (slides.length <= 1) return;

    let currentIndex = 0;
    let autoplayTimer = null;
    const SLIDE_DURATION = 5000; // 5 seconds per slide

    function showSlide(index) {
      const targetIndex = (index + slides.length) % slides.length;
      if (targetIndex === currentIndex) return;

      slides[currentIndex].classList.remove('active');
      if (dots[currentIndex]) {
        dots[currentIndex].classList.remove('active');
      }

      currentIndex = targetIndex;

      slides[currentIndex].classList.add('active');
      if (dots[currentIndex]) {
        dots[currentIndex].classList.add('active');
      }
    }

    function nextSlide() {
      showSlide(currentIndex + 1);
    }

    function prevSlide() {
      showSlide(currentIndex - 1);
    }

    function startTimer() {
      stopTimer();
      autoplayTimer = setInterval(nextSlide, SLIDE_DURATION);
    }

    function stopTimer() {
      if (autoplayTimer) {
        clearInterval(autoplayTimer);
        autoplayTimer = null;
      }
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', (e) => {
        e.preventDefault();
        nextSlide();
        startTimer();
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', (e) => {
        e.preventDefault();
        prevSlide();
        startTimer();
      });
    }

    dots.forEach((dot) => {
      dot.addEventListener('click', (e) => {
        e.preventDefault();
        const targetIndex = parseInt(dot.getAttribute('data-index'), 10);
        showSlide(targetIndex);
        startTimer();
      });
    });

    // Pause auto-sliding only when actively hovering over navigation controls (arrows/dots)
    const controls = [prevBtn, nextBtn, document.getElementById('hero-dots')].filter(Boolean);
    controls.forEach(ctrl => {
      ctrl.addEventListener('mouseenter', stopTimer);
      ctrl.addEventListener('mouseleave', startTimer);
    });

    // Pause when browser tab is hidden, resume when active
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        stopTimer();
      } else {
        startTimer();
      }
    });

    // Mobile Touch Swipe with angle detection to distinguish horizontal swipe from vertical scroll
    let startX = 0;
    let startY = 0;
    slider.addEventListener('touchstart', (e) => {
      startX = e.changedTouches[0].screenX;
      startY = e.changedTouches[0].screenY;
      stopTimer();
    }, { passive: true });

    slider.addEventListener('touchend', (e) => {
      const endX = e.changedTouches[0].screenX;
      const endY = e.changedTouches[0].screenY;
      const diffX = startX - endX;
      const diffY = startY - endY;
      if (Math.abs(diffX) > 35 && Math.abs(diffX) > Math.abs(diffY)) {
        if (diffX > 0) {
          nextSlide();
        } else {
          prevSlide();
        }
      }
      startTimer();
    }, { passive: true });

    // Start auto-rotation (strictly 5 seconds)
    startTimer();
  })();

  // =========================================================================
  // 6. Instant Intent Prefetching & Silky Navigation Progress
  // Pre-caches pages on link hover/touch so clicks load instantly (0ms latency)
  // =========================================================================
  (function initInstantNavigation() {
    const navLoader = document.getElementById('page-nav-loader');
    const prefetchedUrls = new Set();
    const isSaveData = navigator.connection && (navigator.connection.saveData || /2g/.test(navigator.connection.effectiveType));

    if (isSaveData) return;

    function canPrefetch(url) {
      if (!url) return false;
      try {
        const parsed = new URL(url, window.location.href);
        if (parsed.origin !== window.location.origin) return false;
        if (parsed.pathname === window.location.pathname && parsed.search === window.location.search) return false;
        const path = parsed.pathname;
        if (
          path.startsWith('/admin') ||
          path.startsWith('/checkout') ||
          path.startsWith('/account/logout') ||
          path.startsWith('/cart/add') ||
          path.startsWith('/cart/remove') ||
          path.startsWith('/api') ||
          path.endsWith('.pdf') ||
          path.endsWith('.zip')
        ) return false;

        return !prefetchedUrls.has(parsed.href);
      } catch {
        return false;
      }
    }

    function prefetchUrl(url) {
      try {
        const fullUrl = new URL(url, window.location.href).href;
        if (prefetchedUrls.has(fullUrl)) return;
        prefetchedUrls.add(fullUrl);

        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = fullUrl;
        link.as = 'document';
        document.head.appendChild(link);
      } catch {}
    }

    let hoverTimer = null;
    document.addEventListener('mouseover', (e) => {
      const anchor = e.target.closest('a[href]');
      if (!anchor) return;
      const href = anchor.getAttribute('href');
      if (!canPrefetch(href)) return;

      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => {
        prefetchUrl(href);
      }, 65);
    }, { passive: true });

    document.addEventListener('mouseout', (e) => {
      if (e.target.closest('a[href]')) {
        clearTimeout(hoverTimer);
      }
    }, { passive: true });

    document.addEventListener('touchstart', (e) => {
      const anchor = e.target.closest('a[href]');
      if (anchor) {
        const href = anchor.getAttribute('href');
        if (canPrefetch(href)) prefetchUrl(href);
      }
    }, { passive: true });

    document.addEventListener('click', (e) => {
      const anchor = e.target.closest('a[href]');
      if (!anchor || anchor.target === '_blank' || e.metaKey || e.ctrlKey || e.shiftKey || e.defaultPrevented) return;
      const href = anchor.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

      try {
        const parsed = new URL(href, window.location.href);
        if (parsed.origin === window.location.origin && parsed.pathname !== window.location.pathname) {
          if (navLoader) {
            navLoader.classList.remove('finishing');
            navLoader.classList.add('loading');
          }
        }
      } catch {}
    });

    window.addEventListener('pageshow', () => {
      if (navLoader && navLoader.classList.contains('loading')) {
        navLoader.classList.remove('loading');
        navLoader.classList.add('finishing');
        setTimeout(() => {
          navLoader.classList.remove('finishing');
        }, 300);
      }
    });
  })();
});

