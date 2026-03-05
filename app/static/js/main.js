/* =========================================================
    1. EXISTING LOGIC 
    (Alerts, Cart Validation, Image Fallbacks, etc.)
========================================================= */

// Auto-dismiss alerts after 4 seconds
document.querySelectorAll('.alert-dismissible').forEach(alert => {
  setTimeout(() => {
    const bsAlert = new bootstrap.Alert(alert);
    if (bsAlert) bsAlert.close();
  }, 4000);
});

// Quantity input validation in cart
document.querySelectorAll('.qty-input').forEach(input => {
  input.addEventListener('change', function() {
    const min = parseInt(this.min) || 1;
    const max = parseInt(this.max) || 9999;
    let val = parseInt(this.value) || min;
    this.value = Math.min(Math.max(val, min), max);
  });
});

// Product image error fallback
document.querySelectorAll('img[data-fallback]').forEach(img => {
  img.addEventListener('error', function() {
    this.src = this.dataset.fallback;
  });
});

// Confirm delete actions
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', function(e) {
    if (!confirm(this.dataset.confirm)) e.preventDefault();
  });
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
  });
});


/* =========================================================
    2. REGISTRATION LOGIC 
    (Password Toggles, Role Switching, Match Validation)
========================================================= */

function togglePassword(fieldId, btn) {
  const field = document.getElementById(fieldId);
  if (!field) return;

  if (field.type === "password") {
    field.type = "text";
    btn.textContent = "Hide";
  } else {
    field.type = "password";
    btn.textContent = "Show";
  }
}

function setRole(role) {
  const roleInput = document.getElementById("role");
  if (!roleInput) return;

  roleInput.value = role;

  const btnBuyer = document.getElementById("btn-buyer");
  const btnFarmer = document.getElementById("btn-farmer");

  if (role === 'buyer') {
    btnBuyer?.classList.replace("btn-outline-success", "btn-success");
    btnFarmer?.classList.replace("btn-success", "btn-outline-success");
  } else {
    btnFarmer?.classList.replace("btn-outline-success", "btn-success");
    btnBuyer?.classList.replace("btn-success", "btn-outline-success");
  }

  document.querySelectorAll(".role-buyer").forEach(el => 
    el.classList.toggle("d-none", role !== "buyer")
  );
  document.querySelectorAll(".role-farmer").forEach(el => 
    el.classList.toggle("d-none", role !== "farmer")
  );
}

const regForm = document.getElementById("registrationForm");
if (regForm) {
  regForm.onsubmit = function(e) {
    const pass = document.getElementById("password").value;
    const confirmPass = document.getElementById("confirm_password").value;
    const errorMsg = document.getElementById("passwordError");

    if (pass !== confirmPass) {
      e.preventDefault();
      errorMsg?.classList.remove("d-none");
      return false;
    }
    errorMsg?.classList.add("d-none");
  };
}


/* =========================================================
    3. 🚨 SMART SEARCH OVERLAY FIX (AI POWERED) 🚨
    Inaayos ang overlapping at transparency issue gamit ang OpenAI.
========================================================= */

// DEBOUNCE FUNCTION: Pinipigilan ang sabay-sabay na API calls para hindi mag-lag.
function debounce(func, timeout = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => { func.apply(this, args); }, timeout);
  };
}

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('input[name="q"]');
    const suggestionsContainer = document.getElementById('search-suggestions');

    if (searchInput && suggestionsContainer) {
        
        // 🟢 FIX 1: Pilitin ang container na magkaroon ng SOLID style sa JS level
        suggestionsContainer.style.cssText = `
            position: absolute !important;
            z-index: 999999 !important;
            background-color: #ffffff !important;
            width: 100%;
            display: none;
            border-radius: 0 0 15px 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        `;

        const performSearch = async (query) => {
            if (query.length < 2) { 
                suggestionsContainer.innerHTML = ''; 
                suggestionsContainer.style.display = 'none';
                return; 
            }

            try {
                // 🟢 LOADING STATE: Nagpapakita ng "thinking" icon para sa AI
                suggestionsContainer.innerHTML = '<div class="list-group-item text-muted small"><i class="fas fa-brain fa-pulse text-primary me-2"></i>HarvestIQ AI is thinking...</div>';
                suggestionsContainer.style.display = 'block';

                const response = await fetch(`/search-suggestions?q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data.length > 0) {
                    // 🟢 RENDERING LOGIC: Dinagdagan ng support para sa AI items
                    suggestionsContainer.innerHTML = data.map(item => `
                        <a href="/search?q=${encodeURIComponent(item.text)}" 
                           class="list-group-item list-group-item-action py-3 border-bottom suggestion-item"
                           style="background-color: #ffffff !important; z-index: 1000000 !important; position: relative; opacity: 1 !important; display: block !important; pointer-events: auto !important;">
                            <div class="d-flex justify-content-between align-items-center">
                                <div style="color: #2d3748 !important; font-weight: 600;">
                                    <i class="fas ${item.icon || 'fa-seedling'} ${item.type === 'ai-suggestion' ? 'text-primary' : 'text-success'} me-2"></i>
                                    ${item.text}
                                </div>
                                ${item.subtext ? `
                                    <span class="badge ${item.type === 'ai-suggestion' ? 'bg-soft-primary text-primary' : 'bg-light text-dark'} border small shadow-sm">
                                        ${item.subtext}
                                    </span>` : ''}
                            </div>
                        </a>`).join('');
                } else { 
                    suggestionsContainer.innerHTML = '<div class="list-group-item text-muted small">Walang nahanap ang AI para sa request mo.</div>';
                }
            } catch (err) { 
                console.error("HarvestIQ Fetch Error:", err); 
            }
        };

        // Gamitin ang Debounce para smooth ang typing experience sa dashboard.
        const debouncedSearch = debounce((e) => performSearch(e.target.value.trim()));
        searchInput.addEventListener('input', debouncedSearch);

        // Isara ang suggestions kapag nag-click sa labas
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
                suggestionsContainer.innerHTML = '';
                suggestionsContainer.style.display = 'none';
            }
        });
    }
});