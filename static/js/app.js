// MOU Management System Frontend Utilities

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
});
