/**
 * ═══════════════════════════════════════════════
 *   بیو کلاب — جاوااسکریپت پنل مدیریت
 *   فاز ۴: توابع مشترک و کاربردی
 * ═══════════════════════════════════════════════
 */

document.addEventListener('DOMContentLoaded', function () {

    // ═══════════════════════════════════════════
    //   ۱. حذف خودکار Alert ها بعد از ۵ ثانیه
    // ═══════════════════════════════════════════
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // ═══════════════════════════════════════════
    //   ۲. سایدبار — باز/بسته کردن
    // ═══════════════════════════════════════════
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const hamburger = document.getElementById('hamburgerBtn');
    const closeBtn = document.getElementById('sidebarClose');
    const mainContent = document.getElementById('mainContent');

    function openSidebar() {
        if (!sidebar) return;
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('show');
        if (mainContent && window.innerWidth > 768) {
            mainContent.classList.add('shifted');
        }
    }

    function closeSidebar() {
        if (!sidebar) return;
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('show');
        if (mainContent) mainContent.classList.remove('shifted');
    }

    if (hamburger) hamburger.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // بستن سایدبار با کلید Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeSidebar();
    });

    // ═══════════════════════════════════════════
    //   ۳. Tooltip های Bootstrap
    // ═══════════════════════════════════════════
    var tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });

});

// ═══════════════════════════════════════════════
//   ۴. تابع تایید حذف — استفاده در همه تمپلیت‌ها
// ═══════════════════════════════════════════════
/**
 * تایید حذف با نمایش مودال یا confirm ساده
 * @param {number} itemId - شناسه آیتم
 * @param {string} itemName - نام آیتم برای نمایش
 * @param {string} formId - شناسه فرم حذف (اختیاری)
 */
function confirmDelete(itemId, itemName, formId) {
    var message = 'آیا از حذف "' + itemName + '" مطمئن هستید؟';
    if (confirm(message)) {
        var form = document.getElementById(
            formId || ('deleteForm' + itemId)
        );
        if (form) {
            form.submit();
        }
    }
}

/**
 * تایید حذف عمومی برای فرم‌هایی که onsubmit دارند
 */
function confirmAction(message) {
    return confirm(message || 'آیا مطمئن هستید؟');
}

// ═══════════════════════════════════════════════
//   ۵. مودال رد — تنظیم اکشن فرم و نمایش مودال
// ═══════════════════════════════════════════════
function showRejectModal(itemId, itemName) {
    var nameEl = document.getElementById('rejectBusinessName')
        || document.getElementById('rejectItemName');
    
    if (nameEl) {
        nameEl.textContent = itemName;
    }
    
    var form = document.getElementById('rejectForm');
    if (form) {
        // اگر data-base-url وجود داشت از آن استفاده کن
        if (form.dataset.baseUrl) {
            form.action = form.dataset.baseUrl.replace('__ID__', itemId);
        } else {
            // در غیر این صورت از مسیر فعلی استفاده کن
            var basePath = window.location.pathname.replace(/\/$/, '');
            form.action = basePath + '/' + itemId + '/reject/';
        }
    }
    
    var modalEl = document.getElementById('rejectModal');
    if (modalEl && typeof bootstrap !== 'undefined') {
        var modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

function submitReject() {
    var reasonEl = document.getElementById('rejectReasonText');
    if (reasonEl && !reasonEl.value.trim()) {
        alert('لطفاً دلیل رد را وارد کنید.');
        return;
    }
    var hiddenInput = document.getElementById('rejectionReason');
    if (hiddenInput && reasonEl) {
        hiddenInput.value = reasonEl.value.trim();
    }
    var form = document.getElementById('rejectForm');
    if (form) {
        form.submit();
    }
}

// ═══════════════════════════════════════════════
//   ۶. کپی در کلیپ‌بورد
// ═══════════════════════════════════════════════
function copyToClipboard(text, btn) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () {
            if (btn) {
                var originalText = btn.textContent;
                btn.textContent = '✅ کپی شد';
                setTimeout(function () {
                    btn.textContent = originalText;
                }, 2000);
            }
        });
    }
}

// ═══════════════════════════════════════════════
//   ۷. فرمت عدد با جداکننده هزارگان فارسی
// ═══════════════════════════════════════════════
function formatPersianNumber(num) {
    if (num === null || num === undefined) return '۰';
    return Number(num).toLocaleString('fa-IR');
}

// ═══════════════════════════════════════════════
//   ۸. تبدیل اعداد انگلیسی به فارسی
// ═══════════════════════════════════════════════
function toPersianDigits(str) {
    if (!str) return '';
    var persianDigits = '۰۱۲۳۴۵۶۷۸۹';
    return String(str).replace(/[0-9]/g, function (d) {
        return persianDigits[d];
    });
}