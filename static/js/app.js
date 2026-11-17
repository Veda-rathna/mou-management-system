// MOU Management System Frontend Utilities & Theme Engine

// 1. Theme Engine (Light / Dark Mode)
(function () {
  const getStoredTheme = () => localStorage.getItem('mou_theme');
  const setStoredTheme = theme => localStorage.setItem('mou_theme', theme);

  const getPreferredTheme = () => {
    const storedTheme = getStoredTheme();
    if (storedTheme) {
      return storedTheme;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };

  const setTheme = function (theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    const themeIcon = document.getElementById('themeToggleIcon');
    if (themeIcon) {
      if (theme === 'dark') {
        themeIcon.classList.remove('bi-moon-stars-fill');
        themeIcon.classList.add('bi-sun-fill');
      } else {
        themeIcon.classList.remove('bi-sun-fill');
        themeIcon.classList.add('bi-moon-stars-fill');
      }
    }
  };

  // Set initial theme immediately
  setTheme(getPreferredTheme());

  window.addEventListener('DOMContentLoaded', () => {
    setTheme(getPreferredTheme());

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        setStoredTheme(newTheme);
        setTheme(newTheme);
      });
    }
  });
})();

document.addEventListener('DOMContentLoaded', function () {
  // Initialize tooltips if Bootstrap is available
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  // 1-Click Copy Link with Feedback
  const copyButtons = document.querySelectorAll('.btn-copy-link');
  copyButtons.forEach(button => {
    button.addEventListener('click', function () {
      const targetInput = document.querySelector(this.getAttribute('data-target'));
      const textToCopy = targetInput ? targetInput.value : this.getAttribute('data-url');

      if (textToCopy) {
        navigator.clipboard.writeText(textToCopy).then(() => {
          const originalText = this.innerHTML;
          this.innerHTML = '<i class="bi bi-check2"></i> Copied!';
          this.classList.remove('btn-outline-primary', 'btn-primary');
          this.classList.add('btn-success');

          setTimeout(() => {
            this.innerHTML = originalText;
            this.classList.remove('btn-success');
            this.classList.add('btn-outline-primary');
          }, 2000);
        }).catch(err => {
          console.error('Clipboard copy failed:', err);
        });
      }
    });
  });

  // Clause Category Filter in MOU Detail
  const categoryFilters = document.querySelectorAll('.clause-filter-btn');
  const clauseCards = document.querySelectorAll('.clause-card');

  categoryFilters.forEach(btn => {
    btn.addEventListener('click', function () {
      categoryFilters.forEach(b => b.classList.remove('active', 'btn-primary'));
      categoryFilters.forEach(b => b.classList.add('btn-outline-secondary'));

      this.classList.add('active', 'btn-primary');
      this.classList.remove('btn-outline-secondary');

      const selectedCategory = this.getAttribute('data-category');

      clauseCards.forEach(card => {
        if (selectedCategory === 'all' || card.getAttribute('data-category') === selectedCategory) {
          card.style.display = 'block';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  // Creation Mode Switcher on /mous/create/
  const modeRadios = document.querySelectorAll('input[name="creation_mode"]');
  const documentSection = document.getElementById('documentUploadSection');
  const submitBtnText = document.getElementById('submitBtnText');
  const partnerInviteAlert = document.getElementById('partnerInviteAlert');

  if (modeRadios.length > 0) {
    modeRadios.forEach(radio => {
      radio.addEventListener('change', function () {
        document.querySelectorAll('.mode-card').forEach(card => card.classList.remove('active'));
        const parentCard = this.closest('.mode-card');
        if (parentCard) parentCard.classList.add('active');

        if (this.value === 'invite_partner') {
          if (documentSection) documentSection.style.display = 'none';
          if (partnerInviteAlert) partnerInviteAlert.style.display = 'block';
          if (submitBtnText) submitBtnText.textContent = 'Save & Generate Partner Link';
        } else {
          if (documentSection) documentSection.style.display = 'block';
          if (partnerInviteAlert) partnerInviteAlert.style.display = 'none';
          if (submitBtnText) submitBtnText.textContent = 'Save & Run AI Intelligence';
        }
      });
    });
  }
});
