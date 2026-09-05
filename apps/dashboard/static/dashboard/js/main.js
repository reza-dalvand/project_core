/**
 * ═══════════════════════════════════════════════
 *   بیو کلاب — جاوااسکریپت پنل مدیریت
 *   فاز ۴: بازنویسی کامل
 *   - مودال تایید به جای confirm()
 *   - کپی امن در کلیپ‌بورد با هندل خطا
 *   - ذخیره وضعیت سایدبار در localStorage
 *   - Debounce برای جستجو
 *   - دسترسی‌پذیری (ARIA)
 * ═══════════════════════════════════════════════
 */

(function () {
'use strict';

/* ═══════════════════════════════════════════
   ۱. سایدبار — باز/بسته + ذخیره وضعیت
═══════════════════════════════════════════ */
var sidebar = document.getElementById('sidebar');
var overlay = document.getElementById('sidebarOverlay');
var hamburger = document.getElementById('hamburgerBtn');
var closeBtn = document.getElementById('sidebarClose');
var mainContent = document.getElementById('mainContent');
var SIDEBAR_KEY = 'dashboard_sidebar_open';

function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
    if (mainContent && window.innerWidth > 768) {
        mainContent.classList.add('shifted');
    }
    if (hamburger) hamburger.setAttribute('aria-expanded', 'true');
    if (closeBtn) closeBtn.setAttribute('aria-expanded', 'true');
    try {
        localStorage.setItem(SIDEBAR_KEY, '1');
    } catch (e) { /* localStorage در دسترس نیست */ }
}

function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
    if (mainContent) mainContent.classList.remove('shifted');
    if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
    if (closeBtn) closeBtn.setAttribute('aria-expanded', 'false');
    try {
        localStorage.setItem(SIDEBAR_KEY, '0');
    } catch (e) { /* localStorage در دسترس نیست */ }
}

if (hamburger) {
    hamburger.addEventListener('click', function () {
        if (sidebar.classList.contains('open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });
}

if (closeBtn) {
    closeBtn.addEventListener('click', closeSidebar);
}

if (overlay) {
    overlay.addEventListener('click', closeSidebar);
}

// بستن با Escape
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar.classList.contains('open')) {
        closeSidebar();
    }
});

// ✅ فاز ۴: بازیابی وضعیت سایدبار از ذخیره‌سازی قبلی
try {
    if (localStorage.getItem(SIDEBAR_KEY) === '1' && window.innerWidth > 768) {
        openSidebar();
    }
} catch (e) { /* localStorage در دسترس نیست */ }

/* ═══════════════════════════════════════════
   ۲. مودال تایید — جایگزین confirm()
═══════════════════════════════════════════ */
var confirmModalEl = document.getElementById('confirmModal');
var confirmModalMessage = document.getElementById('confirmModalMessage');
var confirmModalSubmit = document.getElementById('confirmModalSubmit');
var confirmCallback = null;

/**
 * نمایش مودال تایید
 * @param {string} message - متن پیام تایید
 * @param {function} onConfirm - تابع اجرا پس از تایید
 */
window.showConfirmModal = function (message, onConfirm) {
    confirmModalMessage.textContent = message;
    confirmCallback = onConfirm;

    if (confirmModalEl && typeof bootstrap !== 'undefined') {
        var modal = new bootstrap.Modal(confirmModalEl);
        modal.show();
    } else {
        // Fallback اگر بوت‌استرپ در دسترس نبود
        if (confirm(message)) {
            onConfirm();
        }
    }
};

if (confirmModalSubmit) {
    confirmModalSubmit.addEventListener('click', function () {
        if (confirmModalEl && typeof bootstrap !== 'undefined') {
            var modal = bootstrap.Modal.getInstance(confirmModalEl);
            if (modal) modal.hide();
        }
        if (typeof confirmCallback === 'function') {
            confirmCallback();
            confirmCallback = null;
        }
    });
}

/**
 * تایید حذف آیتم — جایگزین تابع قبلی با confirm()
 * @param {number} itemId
 * @param {string} itemName
 */
window.confirmDelete = function (itemId, itemName) {
    var message = 'آیا از حذف "' + itemName + '" مطمئن هستید؟ این عملیات قابل بازگشت نیست.';
    window.showConfirmModal(message, function () {
        var form = document.getElementById('deleteForm' + itemId);
        if (form) {
            form.submit();
        }
    });
};

/**
 * تایید عملیات عمومی
 * @param {string} message
 * @returns {boolean}
 */
window.confirmAction = function (message) {
    return confirm(message || 'آیا مطمئن هستید؟');
};

/* ═══════════════════════════════════════════
   ۳. مودال رد کسب‌وکار / تسویه
═══════════════════════════════════════════ */
window.showRejectModal = function (itemId, itemName) {
    var nameEl = document.getElementById('rejectBusinessName')
              || document.getElementById('rejectItemName');
    if (nameEl) {
        nameEl.textContent = itemName;
    }
    var form = document.getElementById('rejectForm');
    if (form) {
        // ✅ فاز ۴: استفاده از data-base-url به جای رشته‌سازی دستی
        if (form.dataset.baseUrl) {
            form.action = form.dataset.baseUrl.replace('__ID__', itemId);
        }
    }
    var modalEl = document.getElementById('rejectModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
        var modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
};

window.submitReject = function () {
    var reasonEl = document.getElementById('rejectReasonText');
    if (reasonEl && !reasonEl.value.trim()) {
        reasonEl.classList.add('is-invalid');
        return;
    }
    if (reasonEl) reasonEl.classList.remove('is-invalid');

    var hiddenInput = document.getElementById('rejectionReason');
    if (hiddenInput && reasonEl) {
        hiddenInput.value = reasonEl.value.trim();
    }
    var form = document.getElementById('rejectForm');
    if (form) {
        form.submit();
    }
};

/* ═══════════════════════════════════════════
   ۴. کپی در کلیپ‌بورد — با هندل خطا
═══════════════════════════════════════════ */
window.copyToClipboard = function (text, btn) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () {
            _showCopyFeedback(btn, true);
        }).catch(function () {
            _fallbackCopy(text, btn);
        });
    } else {
        _fallbackCopy(text, btn);
    }
};

function _fallbackCopy(text, btn) {
    var textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        _showCopyFeedback(btn, true);
    } catch (e) {
        _showCopyFeedback(btn, false);
    }
    document.body.removeChild(textarea);
}

function _showCopyFeedback(btn, success) {
    if (!btn) return;
    var originalText = btn.textContent;
    btn.textContent = success ? '✅ کپی شد' : '❌ خطا';
    setTimeout(function () {
        btn.textContent = originalText;
    }, 2000);
}

/* ═══════════════════════════════════════════
   ۵. فرمت اعداد فارسی
═══════════════════════════════════════════ */
window.formatPersianNumber = function (num) {
    if (num === null || num === undefined) return '۰';
    return Number(num).toLocaleString('fa-IR');
};

window.toPersianDigits = function (str) {
    if (!str) return '';
    var persianDigits = '۰۱۲۳۴۵۶۷۸۹';
    return String(str).replace(/[0-9]/g, function (d) {
        return persianDigits[d];
    });
};

/* ═══════════════════════════════════════════
   ۶. Debounce برای جستجو
═══════════════════════════════════════════ */
function debounce(func, wait) {
    var timeout;
    return function () {
        var context = this;
        var args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function () {
            func.apply(context, args);
        }, wait);
    };
}

// ✅ فاز ۴: اعمال Debounce خودکار به اینپوت‌های جستجو
document.addEventListener('DOMContentLoaded', function () {
    var searchInputs = document.querySelectorAll('input[name="search"]');
    searchInputs.forEach(function (input) {
        var form = input.closest('form');
        if (!form) return;

        var debouncedSubmit = debounce(function () {
            form.submit();
        }, 500);

        input.addEventListener('input', debouncedSubmit);
    });
});

/* ═══════════════════════════════════════════
   ۷. حذف خودکار Alert ها بعد از ۵ ثانیه
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function () {
    var alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alertEl) {
        setTimeout(function () {
            if (typeof bootstrap !== 'undefined') {
                var bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
                if (bsAlert) bsAlert.close();
            }
        }, 5000);
    });
});

/* ═══════════════════════════════════════════
   ۸. Tooltip های Bootstrap
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function () {
    if (typeof bootstrap === 'undefined') return;
    var tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });
});

/* ═══════════════════════════════════════════
   ۹. دسترسی‌پذیری — اعلان تغییر صفحه
═══════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function () {
    var pageStatus = document.getElementById('page-status');
    if (pageStatus) {
        pageStatus.textContent = 'صفحه با موفقیت بارگذاری شد';
    }
});

})();