// chores/static/js/main.js

// CSRF token helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// --- Issue #54: JavaScript for assignment completion ---
// Attaches event listeners to "Complete" buttons on chore cards.
// On click, sends a POST request to the assignment completion endpoint.
// On success, removes the card or updates its status. Handles errors with an alert.

document.addEventListener('DOMContentLoaded', function () {
    // Complete button handlers
    const completeForms = document.querySelectorAll('.complete-form');
    completeForms.forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const actionUrl = form.getAttribute('action');
            const card = form.closest('.overdue-card, .d-flex');

            fetch(actionUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin',
            })
                .then(function (response) {
                    if (response.ok) {
                        if (card) {
                            card.remove();
                        } else {
                            const parent = form.closest('.list-group-item, tr, .mb-2');
                            if (parent) {
                                parent.remove();
                            }
                        }
                        updateUnreadCount();
                    } else {
                        alert('Failed to complete chore. Please try again.');
                    }
                })
                .catch(function () {
                    alert('Network error. Please try again.');
                });
        });
    });

    // Notification read handlers
    const notificationItems = document.querySelectorAll('.notification-item');
    notificationItems.forEach(function (item) {
        item.addEventListener('click', function () {
            const notificationId = item.getAttribute('data-notification-id');
            markNotificationRead(notificationId, item);
        });
    });
});

// --- Issue #55: JavaScript for notification read ---
// Sends a POST to the notification read endpoint when an unread notification is clicked.
// Updates the UI to remove the unread highlight and adjusts the navbar badge count.

function markNotificationRead(notificationId, element) {
    // Only mark unread notifications as read
    if (!element.classList.contains('list-group-item-warning')) {
        return;
    }

    const url = '/notifications/' + notificationId + '/mark-read/';

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({}),
    })
        .then(function (response) {
            if (response.ok) {
                // Remove the highlight (warning class) and unread dot
                element.classList.remove('list-group-item-warning');

                const unreadDot = element.querySelector('.unread-dot');
                if (unreadDot) {
                    unreadDot.remove();
                }

                // Update the status text
                const statusEl = element.querySelector('.d-flex.w-100.justify-content-between small.text-muted:last-child');
                if (statusEl) {
                    statusEl.textContent = 'Read';
                }

                // Update unread count in navbar
                updateUnreadCount();
            }
        })
        .catch(function () {
            // Silently fail - clicking a notification shouldn't break the UI
        });
}

// Update the unread count badge in the navbar
function updateUnreadCount() {
    fetch('/notifications/', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
    })
        .then(function (response) {
            if (response.ok) {
                return response.text();
            }
            return null;
        })
        .then(function (html) {
            if (!html) return;
            const temp = document.createElement('div');
            temp.innerHTML = html;
            const badges = temp.querySelectorAll('.badge');
            badges.forEach(function (newBadge) {
                const badgeLink = newBadge.closest('a');
                if (badgeLink && badgeLink.href && badgeLink.href.indexOf('notifications') !== -1) {
                    const newCount = parseInt(newBadge.textContent, 10);
                    const currentBadge = document.querySelector('#navbarNav a[href*="notifications"] .badge');
                    if (currentBadge) {
                        if (newCount > 0) {
                            currentBadge.textContent = newCount;
                            currentBadge.style.display = '';
                        } else {
                            currentBadge.style.display = 'none';
                        }
                    }
                }
            });
        })
        .catch(function () {
            // Silently fail
        });
}
