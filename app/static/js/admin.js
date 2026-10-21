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

  // 6b. Dynamic Size & Volume Variant Manager
  function initVariantManager() {
    var container = document.getElementById('variants-container');
    var newContainer = document.getElementById('new-variants-container');
    var existingContainer = document.getElementById('existing-variants-container');

    if (!container && !newContainer && !existingContainer) return;

    var nameInput = document.getElementById('name');
    var slugInput = document.getElementById('slug');

    function getProductPrefix() {
      if (slugInput && slugInput.value.trim()) {
        var cleanSlug = slugInput.value.trim().replace(/[^a-zA-Z0-9]/g, '');
        return cleanSlug.substring(0, 4).toUpperCase() || 'PROD';
      }
      if (nameInput && nameInput.value.trim()) {
        var cleanName = nameInput.value.trim().replace(/[^a-zA-Z0-9]/g, '');
        return cleanName.substring(0, 4).toUpperCase() || 'PROD';
      }
      return 'PROD';
    }

    function extractSizeCode(sizeStr) {
      if (!sizeStr) return '';
      var mlMatch = sizeStr.match(/(\d+\s*ml)/i);
      if (mlMatch) {
        return mlMatch[1].replace(/\s+/g, '').toUpperCase();
      }
      var numMatch = sizeStr.match(/(\d+)/);
      if (numMatch) {
        return numMatch[1] + 'ML';
      }
      var clean = sizeStr.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
      return clean.substring(0, 5) || 'VAR';
    }

    function autoSuggestSku(row) {
      var labelInput = row.querySelector('.variant-label-input');
      var skuInput = row.querySelector('.variant-sku-input');
      if (!labelInput || !skuInput) return;

      var labelVal = labelInput.value.trim();
      if (labelVal && !skuInput.value.trim()) {
        var prefix = getProductPrefix();
        var code = extractSizeCode(labelVal);
        skuInput.value = prefix + '-' + code;
      }
    }

    function attachRowListeners(row) {
      var labelInput = row.querySelector('.variant-label-input');
      if (labelInput) {
        labelInput.addEventListener('blur', function() {
          autoSuggestSku(row);
        });
        labelInput.addEventListener('change', function() {
          autoSuggestSku(row);
        });
      }
    }

    // Attach listeners to all existing variant rows
    document.querySelectorAll('.variant-row, .variant-edit-row').forEach(function(r) {
      attachRowListeners(r);
    });

    // Create a new variant row element
    function createVariantRowElement(isNewMode, defaultLabel) {
      var row = document.createElement('div');
      row.className = 'variant-row';
      var prefix = isNewMode ? 'variant' : 'new_variant';

      var labelFieldName = prefix + '_label[]';
      var skuFieldName = prefix + '_sku[]';
      var priceFieldName = prefix + '_price[]';
      var discPriceFieldName = prefix + '_discounted_price[]';
      var stockFieldName = prefix + '_stock[]';

      row.innerHTML = 
        '<div>' +
          '<label class="variant-field-label">Size / ML:</label>' +
          '<input type="text" name="' + labelFieldName + '" value="' + (defaultLabel || '') + '" list="ml-size-suggestions" required placeholder="e.g. 50ml EDP, 30ml" class="form-control variant-label-input">' +
        '</div>' +
        '<div>' +
          '<label class="variant-field-label">SKU:</label>' +
          '<input type="text" name="' + skuFieldName + '" placeholder="SKU (Auto if blank)" class="form-control variant-sku-input">' +
        '</div>' +
        '<div>' +
          '<label class="variant-field-label">Price (₹) *:</label>' +
          '<input type="number" step="0.01" name="' + priceFieldName + '" required placeholder="Price (₹)" class="form-control variant-price-input">' +
        '</div>' +
        '<div>' +
          '<label class="variant-field-label">Sale Price (₹):</label>' +
          '<input type="number" step="0.01" name="' + discPriceFieldName + '" placeholder="Sale Price (₹)" class="form-control variant-disc-price-input">' +
        '</div>' +
        '<div>' +
          '<label class="variant-field-label">Stock *:</label>' +
          '<input type="number" name="' + stockFieldName + '" value="20" required placeholder="Stock" class="form-control variant-stock-input">' +
        '</div>' +
        '<div class="variant-cell-action" style="text-align: center;">' +
          '<button type="button" class="btn-remove-variant" title="Remove this variant" aria-label="Remove variant">' +
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
              '<polyline points="3 6 5 6 21 6"></polyline>' +
              '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>' +
              '<line x1="10" y1="11" x2="10" y2="17"></line>' +
              '<line x1="14" y1="11" x2="14" y2="17"></line>' +
            '</svg>' +
          '</button>' +
        '</div>';

      attachRowListeners(row);
      return row;
    }

    // Quick ML Preset Buttons
    document.querySelectorAll('.btn-ml-preset').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var presetVal = this.getAttribute('data-preset');
        if (!presetVal) return;

        if (container) {
          // In creation mode: check if an existing row has an empty label
          var rows = container.querySelectorAll('.variant-row');
          var targetRow = null;
          rows.forEach(function(r) {
            var lbl = r.querySelector('.variant-label-input');
            if (lbl && !lbl.value.trim() && !targetRow) {
              targetRow = r;
            }
          });

          if (targetRow) {
            var lblInp = targetRow.querySelector('.variant-label-input');
            lblInp.value = presetVal;
            autoSuggestSku(targetRow);
            var prInp = targetRow.querySelector('.variant-price-input');
            if (prInp) prInp.focus();
            return;
          }

          var newRow = createVariantRowElement(true, presetVal);
          container.appendChild(newRow);
          autoSuggestSku(newRow);
          var pr = newRow.querySelector('.variant-price-input');
          if (pr) pr.focus();
        } else if (newContainer) {
          // In edit mode: add to new-variants-container
          var editRow = createVariantRowElement(false, presetVal);
          newContainer.appendChild(editRow);
          autoSuggestSku(editRow);
          var editPrice = editRow.querySelector('.variant-price-input');
          if (editPrice) editPrice.focus();
        }
      });
    });

    // Add Variant Button
    var addBtn = document.getElementById('btn-add-variant');
    if (addBtn) {
      addBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (container) {
          var r = createVariantRowElement(true, '');
          container.appendChild(r);
          var lbl = r.querySelector('.variant-label-input');
          if (lbl) lbl.focus();
        } else if (newContainer) {
          var nr = createVariantRowElement(false, '');
          newContainer.appendChild(nr);
          var nlbl = nr.querySelector('.variant-label-input');
          if (nlbl) nlbl.focus();
        }
      });
    }

    // Delegated Remove and Delete/Undo handlers
    document.addEventListener('click', function(e) {
      // 1. Remove button on dynamic new rows
      var removeBtn = e.target.closest('.btn-remove-variant');
      if (removeBtn && !removeBtn.classList.contains('btn-delete-existing-variant')) {
        e.preventDefault();
        var row = removeBtn.closest('.variant-row');
        if (row) {
          var parent = row.parentElement;
          if (parent && parent.id === 'variants-container') {
            var allRows = parent.querySelectorAll('.variant-row');
            if (allRows.length <= 1) {
              alert('A product must have at least one size / volume variant. You can change this variant\'s ML size instead of removing it.');
              return;
            }
          }
          row.style.opacity = '0';
          row.style.transform = 'scale(0.95)';
          row.style.transition = 'all 0.18s ease';
          setTimeout(function() {
            if (row && row.parentNode) row.parentNode.removeChild(row);
          }, 180);
        }
        return;
      }

      // 2. Delete / Undo button on existing variants (edit mode)
      var delExistingBtn = e.target.closest('.btn-delete-existing-variant');
      if (delExistingBtn) {
        e.preventDefault();
        var editRow = delExistingBtn.closest('.variant-edit-row');
        if (!editRow) return;
        var varId = delExistingBtn.getAttribute('data-var-id');

        var isDeleted = editRow.classList.contains('variant-marked-deleted');
        if (!isDeleted) {
          // Mark for deletion
          editRow.classList.add('variant-marked-deleted');
          var hiddenDel = document.createElement('input');
          hiddenDel.type = 'hidden';
          hiddenDel.name = 'delete_var_' + varId;
          hiddenDel.value = '1';
          hiddenDel.className = 'delete-flag-input';
          editRow.appendChild(hiddenDel);
          delExistingBtn.innerHTML = '↶ Undo';
          delExistingBtn.className = 'btn-undo-variant btn-delete-existing-variant';
          delExistingBtn.title = 'Undo removal of this variant';
        } else {
          // Undo deletion
          editRow.classList.remove('variant-marked-deleted');
          var hiddenInput = editRow.querySelector('.delete-flag-input');
          if (hiddenInput) hiddenInput.remove();
          delExistingBtn.innerHTML = 
            '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
              '<polyline points="3 6 5 6 21 6"></polyline>' +
              '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>' +
              '<line x1="10" y1="11" x2="10" y2="17"></line>' +
              '<line x1="14" y1="11" x2="14" y2="17"></line>' +
            '</svg>';
          delExistingBtn.className = 'btn-remove-variant btn-delete-existing-variant';
          delExistingBtn.title = 'Remove this variant';
        }
      }
    });

    // Form submit validation: ensure at least one valid variant
    var formCard = document.querySelector('form.admin-card');
    if (formCard && container) {
      formCard.addEventListener('submit', function(e) {
        var rows = container.querySelectorAll('.variant-row');
        var hasValid = false;
        rows.forEach(function(r) {
          var lbl = r.querySelector('.variant-label-input');
          var pr = r.querySelector('.variant-price-input');
          if (lbl && lbl.value.trim() && pr && pr.value.trim()) {
            hasValid = true;
          }
        });
        if (!hasValid) {
          e.preventDefault();
          alert('Please specify at least one Size / Volume Variant with a Size Label and Price.');
          var firstLbl = container.querySelector('.variant-label-input');
          if (firstLbl) firstLbl.focus();
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

  // 9. Instant Multi-Admin Live Sync Engine
  function initLiveSync() {
    var syncUrl = '/admin/api/live-sync';
    var lastLatestOrderId = null;
    var isInitialSync = true;
    var syncIntervalMs = 15000; // 15 seconds

    function updateBadges(data) {
      // 1. Pending orders badge
      var orderBadge = document.getElementById('pendingOrdersBadge');
      if (orderBadge) {
        var count = parseInt(data.pending_orders, 10) || 0;
        orderBadge.textContent = count;
        orderBadge.style.display = count > 0 ? 'inline-block' : 'none';
      }

      // 2. Low stock badge
      var stockBadge = document.getElementById('lowStockBadge');
      if (stockBadge) {
        var stockCount = parseInt(data.low_stock_count, 10) || 0;
        stockBadge.textContent = stockCount;
        stockBadge.style.display = stockCount > 0 ? 'inline-block' : 'none';
      }

      // 3. Notify when a new order arrives while admin has page open
      if (!isInitialSync && lastLatestOrderId !== null && data.latest_order_id > lastLatestOrderId) {
        showSyncToast('✨ New Order #' + (data.latest_order_number || data.latest_order_id) + ' received!');
      }

      lastLatestOrderId = data.latest_order_id;
      isInitialSync = false;
    }

    function showSyncToast(message) {
      var toast = document.getElementById('adminSyncToast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'adminSyncToast';
        toast.style.cssText = 'position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 99999; background: #1B1815; color: #FAF7F2; border: 1px solid var(--gold-primary, #C5A059); border-radius: 8px; padding: 0.85rem 1.25rem; box-shadow: 0 10px 25px rgba(0,0,0,0.35); display: flex; align-items: center; gap: 0.85rem; font-size: 0.875rem;';
        document.body.appendChild(toast);
      }
      toast.innerHTML = '<span>' + message + '</span>' +
        '<button type="button" style="background: var(--gold-primary, #C5A059); color: #1B1815; border: none; padding: 0.35rem 0.75rem; border-radius: 4px; font-weight: 700; cursor: pointer; font-size: 0.78rem;" onclick="location.reload()">' +
        'Refresh' +
        '</button>' +
        '<button type="button" style="background: transparent; color: #999; border: none; font-size: 1.1rem; cursor: pointer; padding: 0 0.3rem;" onclick="this.parentElement.remove()">&times;</button>';

      setTimeout(function() {
        if (toast && toast.parentElement) toast.remove();
      }, 10000);
    }

    function doSync() {
      fetch(syncUrl, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      })
      .then(function(res) {
        if (res.status === 401) {
          window.location.href = '/admin/login';
          return null;
        }
        if (res.ok) return res.json();
        return null;
      })
      .then(function(data) {
        if (data && data.success) {
          updateBadges(data);
        }
      })
      .catch(function() {
        // Silently tolerate transient offline/network pauses
      });
    }

    // Initial check
    doSync();

    // Background interval sync
    setInterval(doSync, syncIntervalMs);

    // Instant sync when tab/window regains user focus
    window.addEventListener('focus', doSync);
    document.addEventListener('visibilitychange', function() {
      if (!document.hidden) doSync();
    });
  }

  // Document Ready Initialization
  document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initEventDelegation();
    initProductForm();
    initVariantManager();
    initComboForm();
    initBannerForm();
    initLiveSync();
  });
})();
