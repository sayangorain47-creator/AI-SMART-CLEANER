// AI Smart Cleaner - Client Interaction Scripts
document.addEventListener('DOMContentLoaded', () => {
  // Flash Alert Dismissal
  document.querySelectorAll('.alert-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 200);
      }
    });
  });

  // Modal Handlers
  window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  };

  window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  };

  // Close modals when clicking backdrop
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
      }
    });
  });

  // Close modals on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.active').forEach(modal => {
        modal.classList.remove('active');
        document.body.style.overflow = '';
      });
    }
  });

  // Image Upload Preview
  const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"], input[type="file"][name*="images"]');
  imageInputs.forEach(input => {
    const previewContainer = document.getElementById('image-preview-box');
    if (!previewContainer) return;

    input.addEventListener('change', () => {
      previewContainer.innerHTML = '';
      if (!input.files || input.files.length === 0) return;

      Array.from(input.files).forEach(file => {
        if (!file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = (e) => {
          const thumb = document.createElement('img');
          thumb.src = e.target.result;
          thumb.className = 'image-preview-thumb';
          thumb.alt = file.name;
          previewContainer.appendChild(thumb);
        };
        reader.readAsDataURL(file);
      });
    });
  });

  // Browser Geolocation Detector
  const geoBtn = document.getElementById('btn-detect-location');
  const latInput = document.getElementById('latitude');
  const lonInput = document.getElementById('longitude');
  const geoStatus = document.getElementById('geo-status');

  if (geoBtn && latInput && lonInput) {
    geoBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        if (geoStatus) geoStatus.textContent = 'Geolocation is not supported by your browser.';
        return;
      }

      geoBtn.disabled = true;
      if (geoStatus) geoStatus.textContent = 'Detecting coordinates...';

      navigator.geolocation.getCurrentPosition(
        (position) => {
          latInput.value = position.coords.latitude.toFixed(6);
          lonInput.value = position.coords.longitude.toFixed(6);
          geoBtn.disabled = false;
          if (geoStatus) {
            geoStatus.textContent = `Coordinates detected (Accuracy: ±${Math.round(position.coords.accuracy)}m)`;
            geoStatus.style.color = '#15803d';
          }
        },
        (error) => {
          geoBtn.disabled = false;
          let msg = 'Could not retrieve location.';
          if (error.code === error.PERMISSION_DENIED) {
            msg = 'Location permission denied. You can still enter your address manually.';
          } else if (error.code === error.POSITION_UNAVAILABLE) {
            msg = 'Location information is currently unavailable.';
          } else if (error.code === error.TIMEOUT) {
            msg = 'Location request timed out.';
          }
          if (geoStatus) {
            geoStatus.textContent = msg;
            geoStatus.style.color = '#dc2626';
          }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
      );
    });
  }

  // Copy Tracking ID button
  window.copyTrackingId = function(id, btnElement) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(id).then(() => {
        const originalText = btnElement.innerHTML;
        btnElement.innerHTML = '✓ Copied!';
        setTimeout(() => { btnElement.innerHTML = originalText; }, 2000);
      });
    }
  };
});
