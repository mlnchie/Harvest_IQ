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
```

---

## `.env.example`
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///data/farmers_marketplace.db

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-app-password

STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...// --- EXISTING LOGIC ---

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

// --- NEW REGISTRATION LOGIC ---

/**
 * Toggles visibility of password fields
 * @param {string} fieldId - The ID of the input to toggle
 * @param {HTMLElement} btn - The button element clicked
 */
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

/**
 * Handles switching between Buyer and Farmer roles in Registration
 */
function setRole(role) {
  const roleInput = document.getElementById("role");
  if (!roleInput) return;

  roleInput.value = role;

  // Update button visual states
  const btnBuyer = document.getElementById("btn-buyer");
  const btnFarmer = document.getElementById("btn-farmer");

  if (role === 'buyer') {
    btnBuyer?.classList.replace("btn-outline-success", "btn-success");
    btnFarmer?.classList.replace("btn-success", "btn-outline-success");
  } else {
    btnFarmer?.classList.replace("btn-outline-success", "btn-success");
    btnBuyer?.classList.replace("btn-success", "btn-outline-success");
  }

  // Toggle field visibility based on role
  document.querySelectorAll(".role-buyer").forEach(el => 
    el.classList.toggle("d-none", role !== "buyer")
  );
  document.querySelectorAll(".role-farmer").forEach(el => 
    el.classList.toggle("d-none", role !== "farmer")
  );
}

// Global Password Match Validation
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