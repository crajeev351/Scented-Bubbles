/**
 * Scented Bubbles Admin Portal Core JavaScript
 * Secure, modular, and nonced/externalized for strict CSP compliance.
 */
(function() {
  'use strict';

  // 1. Destructive Action Confirmation Helper
  function confirmAction(formId, promptMessage) {
    if (confirm(promptMessage || 'Are you sure you want to perform this action?')) {
      var f = document.getElementById(formId);
      if (f) f.submit();
    }
  }
  window.confirmAction = confirmAction;

  // 2. Sensitive Customer Data Reveal / Mask Toggle
  function toggleReveal(id, btn) {
    var el = document.getElementById(id);
    if (!el) return;
    var isMasked = el.textContent.trim() === (el.dataset.masked || '').trim();
    if (isMasked) {
      el.textContent = el.dataset.full;
      if (btn) {
        btn.textContent = "🔒 Hide";
        btn.style.color = "var(--color-danger)";
      }
    } else {
      el.textContent = el.dataset.masked;
      if (btn) {
        btn.textContent = "👁 Reveal";
        btn.style.color = "var(--text-muted)";
      }
    }
  }
  window.toggleReveal = toggleReveal;

  // 3. 2FA Setup Key Clipboard Copy Helper
  function copySetupKey(text, btn) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function() {
        if (btn) {
          var original = btn.textContent;
          btn.textContent = "✓ Copied to Clipboard!";
          setTimeout(function() { btn.textContent = original; }, 2000);
        }
      });
    } else {
      prompt("Copy your setup key:", text);
    }
  }
  window.copySetupKey = copySetupKey;

  // 4. Responsive Sidebar Toggle & Mobile Off-Canvas Drawer
  function initSidebar() {
    var sidebar = document.getElementById('adminSidebar');
    var toggleBtn = document.getElementById('sidebarToggle');
    var closeBtn = document.getElementById('sidebarCloseBtn');
    var overlay = document.getElementById('adminSidebarOverlay');

    function openMobileSidebar() {
      if (sidebar) sidebar.classList.add('show-mobile');
      if (overlay) overlay.classList.add('active');
      document.body.classList.add('admin-drawer-open');
    }

    function closeMobileSidebar() {
      if (sidebar) sidebar.classList.remove('show-mobile');
      if (overlay) overlay.classList.remove('active');
      document.body.classList.remove('admin-drawer-open');
    }

    if (toggleBtn && sidebar) {
      if (window.innerWidth > 992 && localStorage.getItem('sb_admin_sidebar_collapsed') === 'true') {
        sidebar.classList.add('collapsed');
      }
      toggleBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (window.innerWidth <= 992) {
          if (sidebar.classList.contains('show-mobile')) {
            closeMobileSidebar();
          } else {
            openMobileSidebar();
          }
        } else {
          sidebar.classList.toggle('collapsed');
          localStorage.setItem('sb_admin_sidebar_collapsed', sidebar.classList.contains('collapsed'));
        }
      });
    }

    if (closeBtn) closeBtn.addEventListener('click', closeMobileSidebar);
    if (overlay) overlay.addEventListener('click', closeMobileSidebar);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && window.innerWidth <= 992) {
        closeMobileSidebar();
      }
    });

    // Auto-close drawer when nav item clicked on mobile
    document.querySelectorAll('.admin-nav-item a').forEach(function(link) {
      link.addEventListener('click', function() {
        if (window.innerWidth <= 992) {
          closeMobileSidebar();
        }
      });
    });
  }

  // 5. Global Event Delegation (removes inline onclick / onchange)
  function initEventDelegation() {
    // Click delegation
    document.addEventListener('click', function(e) {
      // Data-confirm
      var confirmBtn = e.target.closest('[data-confirm]');
      if (confirmBtn) {
        e.preventDefault();
        var formId = confirmBtn.getAttribute('data-confirm');
        var promptMsg = confirmBtn.getAttribute('data-confirm-prompt') || 'Are you sure you want to perform this action?';
        confirmAction(formId, promptMsg);
        return;
      }

      // Data-toggle-reveal
      var revealBtn = e.target.closest('[data-toggle-reveal]');
      if (revealBtn) {
        e.preventDefault();
        var targetId = revealBtn.getAttribute('data-toggle-reveal');
        toggleReveal(targetId, revealBtn);
        return;
      }

      // Disabled action alert
      var alertBtn = e.target.closest('[data-disabled-alert]');
      if (alertBtn) {
        e.preventDefault();
        alert(alertBtn.getAttribute('data-disabled-alert'));
        return;
      }

      // Copy key button
      var copyBtn = e.target.closest('[data-copy-key]');
      if (copyBtn) {
        e.preventDefault();
        copySetupKey(copyBtn.getAttribute('data-copy-key'), copyBtn);
        return;
      }
    });

    // Change delegation for auto-submitting filters
    document.addEventListener('change', function(e) {
      if (e.target && e.target.hasAttribute('data-auto-submit')) {
        if (e.target.form) {
          e.target.form.submit();
        }
      }
    });
  }

  // 6. Product Form Helpers
  function initProductForm() {
    var categoryCheckboxes = document.querySelectorAll('input[name="category_ids"]');
    function updatePill(cb) {
      var label = cb.closest('.category-pill-label');
      if (!label) return;
      if (cb.checked) {
        label.style.background = 'rgba(197, 160, 89, 0.14)';
        label.style.borderColor = 'var(--gold-primary, #C5A059)';
        label.style.fontWeight = '600';
        label.style.color = '#2A241E';
      } else {
        label.style.background = '#FFFFFF';
        label.style.borderColor = 'var(--border-light, #E2D9CC)';
        label.style.fontWeight = '500';
        label.style.color = 'var(--text-main, #333)';
      }
    }
    window.toggleCategoryPill = updatePill;

    categoryCheckboxes.forEach(function(cb) {
      cb.addEventListener('change', function() { updatePill(this); });
      updatePill(cb);
    });

    var productForm = document.querySelector('form.admin-card');
    if (productForm && categoryCheckboxes.length > 0) {
      productForm.addEventListener('submit', function(e) {
        var checked = document.querySelectorAll('input[name="category_ids"]:checked');
        if (checked.length === 0) {
          e.preventDefault();
          alert('Please select at least one Category for this product.');
          return false;
        }
      });
    }
  }

  // 7. Combo Form Helpers
  function initComboForm() {
    var wrapper = document.getElementById('combo-items-wrapper');
    if (!wrapper) return;

    function reindexComboItems() {
      var rows = wrapper.querySelectorAll('.combo-item-row');
      var countBadge = document.getElementById('items-count-badge');
      if (countBadge) {
        countBadge.textContent = rows.length + (rows.length === 1 ? ' Fragrance' : ' Fragrances');
      }

      rows.forEach(function(row, idx) {
        var badge = row.querySelector('.item-badge');
        if (badge) badge.textContent = 'Item #' + (idx + 1);

        var removeBtn = row.querySelector('.remove-item-btn');
        if (removeBtn) {
          removeBtn.style.visibility = (rows.length > 1) ? 'visible' : 'hidden';
        }
      });

      updatePriceCalculations();
    }
    window.reindexComboItems = reindexComboItems;

    function addComboItemRow() {
      var template = document.getElementById('combo-item-template');
      if (!template) return;
      var clone = template.content.cloneNode(true);
      wrapper.appendChild(clone);
      reindexComboItems();
    }
    window.addComboItemRow = addComboItemRow;

    function updatePriceCalculations() {
      var retailSum = 0;
      var rows = wrapper.querySelectorAll('.combo-item-row');

      rows.forEach(function(row) {
        var select = row.querySelector('.combo-variant-select');
        var qtyInput = row.querySelector('.combo-qty-input');
        if (select && select.value) {
          var selectedOpt = select.options[select.selectedIndex];
          var price = parseFloat(selectedOpt.getAttribute('data-price')) || 0;
          var qty = parseInt(qtyInput ? qtyInput.value : 1) || 1;
          retailSum += (price * qty);
        }
      });

      var comboPriceInput = document.getElementById('combo_price');
      var comboPrice = comboPriceInput ? (parseFloat(comboPriceInput.value) || 0) : 0;
      var savings = retailSum > comboPrice ? (retailSum - comboPrice) : 0;
      var savingsPercent = retailSum > 0 ? Math.round((savings / retailSum) * 100) : 0;

      var calcRetail = document.getElementById('calc-retail-sum');
      var calcCombo = document.getElementById('calc-combo-price');
      var calcSavings = document.getElementById('calc-savings');
      var calcBadge = document.getElementById('calc-savings-badge');

      if (calcRetail) calcRetail.textContent = '₹' + retailSum.toFixed(2);
      if (calcCombo) calcCombo.textContent = '₹' + comboPrice.toFixed(2);
      if (calcSavings) calcSavings.textContent = '₹' + savings.toFixed(2);

      if (calcBadge) {
        if (savings > 0) {
          calcBadge.textContent = savingsPercent + '% Customer Savings';
          calcBadge.style.background = '#2E7D32';
        } else {
          calcBadge.textContent = 'Standard Pricing';
          calcBadge.style.background = '#8C6D23';
        }
      }
    }
    window.updatePriceCalculations = updatePriceCalculations;

    var addBtn = document.getElementById('add-combo-item-btn');
    if (addBtn) {
      addBtn.addEventListener('click', function(e) {
        e.preventDefault();
        addComboItemRow();
      });
    }

    wrapper.addEventListener('click', function(e) {
      if (e.target && e.target.closest('.remove-item-btn')) {
        e.preventDefault();
        var rows = wrapper.querySelectorAll('.combo-item-row');
        if (rows.length > 1) {
          var row = e.target.closest('.combo-item-row');
          if (row) row.remove();
          reindexComboItems();
        }
      }
    });

    wrapper.addEventListener('change', function(e) {
      if (e.target && (e.target.matches('.combo-variant-select') || e.target.matches('.combo-qty-input'))) {
        updatePriceCalculations();
      }
    });

    var comboPriceField = document.getElementById('combo_price');
    if (comboPriceField) {
      comboPriceField.addEventListener('input', updatePriceCalculations);
    }

    reindexComboItems();
  }

  // 8. Banner Form Helpers
  function initBannerForm() {
    var radioGroup = document.querySelectorAll('input[name="target_type"]');
    if (radioGroup.length === 0) return;

    function toggleTargetFields() {
      var selected = document.querySelector('input[name="target_type"]:checked');
      var val = selected ? selected.value : 'custom';

      var pGroup = document.getElementById('target-product-group');
      var cGroup = document.getElementById('target-combo-group');
      var catGroup = document.getElementById('target-category-group');
      var customGroup = document.getElementById('target-custom-group');

      if (pGroup) pGroup.style.display = (val === 'product') ? 'block' : 'none';
      if (cGroup) cGroup.style.display = (val === 'combo') ? 'block' : 'none';
      if (catGroup) catGroup.style.display = (val === 'category') ? 'block' : 'none';
      if (customGroup) customGroup.style.display = (val === 'custom') ? 'block' : 'none';
    }
    window.toggleTargetFields = toggleTargetFields;

    radioGroup.forEach(function(r) {
      r.addEventListener('change', toggleTargetFields);
    });

    var secBtnInput = document.getElementById('secondary_button_text');
    if (secBtnInput) {
      secBtnInput.addEventListener('input', function() {
        var secGroup = document.getElementById('secondary-link-group');
        if (secGroup) {
          secGroup.style.display = this.value.trim().length > 0 ? 'block' : 'none';
        }
      });
    }

    toggleTargetFields();
  }

  // Document Ready Initialization
  document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initEventDelegation();
    initProductForm();
    initComboForm();
    initBannerForm();
  });
})();
