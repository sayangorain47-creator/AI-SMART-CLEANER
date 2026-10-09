// AI Smart Cleaner - Dashboard Interaction Script
document.addEventListener('DOMContentLoaded', () => {
  // Mobile Sidebar Toggle
  const toggleBtn = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 900 &&
          !sidebar.contains(e.target) &&
          !toggleBtn.contains(e.target) &&
          sidebar.classList.contains('mobile-open')) {
        sidebar.classList.remove('mobile-open');
      }
    });
  }

  // Notification dropdown toggle & mark read
  const bellBtn = document.getElementById('notification-bell');
  const notifMenu = document.getElementById('notification-dropdown');

  if (bellBtn && notifMenu) {
    bellBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifMenu.classList.toggle('active');
    });

    document.addEventListener('click', () => {
      notifMenu.classList.remove('active');
    });

    // Mark as read button
    const markReadBtn = document.getElementById('mark-notifications-read');
    if (markReadBtn) {
      markReadBtn.addEventListener('click', () => {
        const url = markReadBtn.getAttribute('data-url');
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken || '',
            'Content-Type': 'application/json'
          }
        }).then(res => res.json()).then(data => {
          if (data.status === 'success') {
            const countBadge = document.querySelector('.notification-count');
            if (countBadge) countBadge.remove();
            const unreadItems = document.querySelectorAll('.notification-item.unread');
            unreadItems.forEach(el => el.classList.remove('unread'));
          }
        }).catch(err => console.error('Error marking notifications read:', err));
      });
    }
  }
});
