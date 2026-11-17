/**
 * HTML5 Canvas Signature Pad
 * Handles retina scaling, mouse and touch drawing, clearing, and exporting to base64.
 */
class SimpleSignaturePad {
  constructor(canvasElement, hiddenInputElement, clearButtonElement) {
    this.canvas = canvasElement;
    this.hiddenInput = hiddenInputElement;
    this.clearBtn = clearButtonElement;
    this.ctx = this.canvas.getContext('2d');
    this.isDrawing = false;
    this.hasDrawn = false;

    this.init();
  }

  init() {
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());

    // Mouse events
    this.canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
    this.canvas.addEventListener('mousemove', (e) => this.draw(e));
    window.addEventListener('mouseup', () => this.stopDrawing());

    // Touch events
    this.canvas.addEventListener('touchstart', (e) => {
      e.preventDefault();
      const touch = e.touches[0];
      const mouseEvent = new MouseEvent('mousedown', {
        clientX: touch.clientX,
        clientY: touch.clientY
      });
      this.canvas.dispatchEvent(mouseEvent);
    }, { passive: false });

    this.canvas.addEventListener('touchmove', (e) => {
      e.preventDefault();
      const touch = e.touches[0];
      const mouseEvent = new MouseEvent('mousemove', {
        clientX: touch.clientX,
        clientY: touch.clientY
      });
      this.canvas.dispatchEvent(mouseEvent);
    }, { passive: false });

    window.addEventListener('touchend', () => {
      const mouseEvent = new MouseEvent('mouseup', {});
      window.dispatchEvent(mouseEvent);
    });

    // Clear button
    if (this.clearBtn) {
      this.clearBtn.addEventListener('click', () => this.clear());
    }

    // Capture on parent form submit
    const parentForm = this.canvas.closest('form');
    if (parentForm) {
      parentForm.addEventListener('submit', () => this.syncToInput());
    }
  }

  resizeCanvas() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;

    // Save content if already drawn
    let dataUrl = null;
    if (this.hasDrawn) {
      dataUrl = this.canvas.toDataURL();
    }

    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);

    this.ctx.lineWidth = 2.5;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
    this.ctx.strokeStyle = '#0f172a'; // Deep slate ink

    if (dataUrl) {
      const img = new Image();
      img.onload = () => {
        this.ctx.drawImage(img, 0, 0, rect.width, rect.height);
      };
      img.src = dataUrl;
    }
  }

  getCoordinates(event) {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
  }

  startDrawing(event) {
    this.isDrawing = true;
    this.hasDrawn = true;
    const { x, y } = this.getCoordinates(event);
    this.ctx.beginPath();
    this.ctx.moveTo(x, y);
  }

  draw(event) {
    if (!this.isDrawing) return;
    const { x, y } = this.getCoordinates(event);
    this.ctx.lineTo(x, y);
    this.ctx.stroke();
  }

  stopDrawing() {
    if (this.isDrawing) {
      this.isDrawing = false;
      this.syncToInput();
    }
  }

  clear() {
    const rect = this.canvas.getBoundingClientRect();
    this.ctx.clearRect(0, 0, rect.width, rect.height);
    this.hasDrawn = false;
    if (this.hiddenInput) {
      this.hiddenInput.value = '';
    }
  }

  syncToInput() {
    if (this.hasDrawn && this.hiddenInput) {
      this.hiddenInput.value = this.canvas.toDataURL('image/png');
    }
  }
}

// Auto-initialize any signature canvases on page
document.addEventListener('DOMContentLoaded', () => {
  const canvasElements = document.querySelectorAll('canvas[data-signature-pad]');
  canvasElements.forEach(canvas => {
    const targetInputId = canvas.getAttribute('data-target-input');
    const clearBtnId = canvas.getAttribute('data-clear-btn');
    const targetInput = targetInputId ? document.getElementById(targetInputId) : null;
    const clearBtn = clearBtnId ? document.getElementById(clearBtnId) : null;
    new SimpleSignaturePad(canvas, targetInput, clearBtn);
  });
});
