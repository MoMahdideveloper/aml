/**
 * Main Application JavaScript
 * 全局工具函数和组件初始化
 */

const App = {
    /**
     * 初始化应用
     */
    init() {
        console.log('🚀 App initializing...');
        this.initMobileMenu();
        this.initDropdowns();
        this.initFlashMessages();
        this.initForms();
        this.initModals();
        console.log('✅ App initialized successfully');
    },

    /**
     * 移动端菜单切换
     */
    initMobileMenu() {
        const toggle = document.getElementById('mobile-menu-toggle');
        const sidebar = document.getElementById('sidebar') || document.querySelector('aside#sidebar') || document.querySelector('aside');

        if (!toggle || !sidebar) {
            console.warn('Mobile menu elements not found');
            return;
        }

        let overlay = document.getElementById('mobile-menu-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'mobile-menu-overlay';
            overlay.className = 'hidden fixed inset-0 bg-black/40 z-40 lg:hidden';
            document.body.appendChild(overlay);
        }

        const openMenu = () => {
            sidebar.classList.remove('-translate-x-full');
            overlay.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            toggle.setAttribute('aria-expanded', 'true');
        };

        const closeMenu = () => {
            sidebar.classList.add('-translate-x-full');
            overlay.classList.add('hidden');
            document.body.style.overflow = '';
            toggle.setAttribute('aria-expanded', 'false');
        };

        toggle.addEventListener('click', () => {
            if (sidebar.classList.contains('-translate-x-full')) {
                openMenu();
            } else {
                closeMenu();
            }
        });

        overlay.addEventListener('click', closeMenu);

        sidebar.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                if (window.matchMedia('(max-width: 1023px)').matches) {
                    setTimeout(closeMenu, 150);
                }
            });
        });

        window.addEventListener('resize', () => {
            if (window.matchMedia('(min-width: 1024px)').matches) {
                closeMenu();
                // Desktop: ensure open state classes don't fight layout
                sidebar.classList.remove('-translate-x-full');
            } else if (!overlay.classList.contains('hidden')) {
                // keep open if overlay visible
            } else {
                sidebar.classList.add('-translate-x-full');
            }
        });

        console.log('✓ Mobile menu initialized');
    },

    closeMobileMenu(sidebar, overlay) {
        if (!sidebar) sidebar = document.getElementById('sidebar');
        if (!overlay) overlay = document.getElementById('mobile-menu-overlay');
        if (sidebar) sidebar.classList.add('-translate-x-full');
        if (overlay) overlay.classList.add('hidden');
        document.body.style.overflow = '';
        const toggle = document.getElementById('mobile-menu-toggle');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
    },

    /**
     * 下拉菜单
     */
    initDropdowns() {
        document.querySelectorAll('[data-dropdown-toggle]').forEach(button => {
            const menu = button.nextElementSibling;
            if (!menu) return;

            button.addEventListener('click', (e) => {
                e.stopPropagation();
                document.querySelectorAll('[data-dropdown-menu]').forEach(m => {
                    if (m !== menu) m.classList.add('hidden');
                });
                menu.classList.toggle('hidden');
            });
        });

        document.addEventListener('click', () => {
            document.querySelectorAll('[data-dropdown-menu]').forEach(menu => {
                menu.classList.add('hidden');
            });
        });

        console.log('✓ Dropdowns initialized');
    },

    /**
     * Flash消息自动关闭
     */
    initFlashMessages() {
        document.querySelectorAll('[data-flash-message]').forEach(msg => {
            const autoClose = setTimeout(() => this.dismissFlashMessage(msg), 5000);

            const closeBtn = msg.querySelector('[data-dismiss]');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    clearTimeout(autoClose);
                    this.dismissFlashMessage(msg);
                });
            }
        });
        console.log('✓ Flash messages initialized');
    },

    dismissFlashMessage(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(-10px)';
        setTimeout(() => element.remove(), 300);
    },

    /**
     * 表单增强
     */
    initForms() {
        document.querySelectorAll('form[data-loading]').forEach(form => {
            form.addEventListener('submit', () => {
                const button = form.querySelector('[type="submit"]');
                if (button) {
                    button.disabled = true;
                    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Loading...';
                }
            });
        });
        console.log('✓ Forms initialized');
    },

    /**
     * 模态框
     */
    initModals() {
        const hideModal = (modal) => {
            if (!modal) return;
            if (typeof modal === 'string') modal = document.getElementById(modal);
            if (!modal) return;
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
            // Bootstrap compat
            modal.classList.remove('show');
            modal.style.display = 'none';
            document.body.style.overflow = '';
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                try {
                    const inst = bootstrap.Modal.getInstance(modal);
                    if (inst) inst.hide();
                } catch (_) { /* ignore */ }
            }
        };

        const showModal = (modal) => {
            if (!modal) return;
            if (typeof modal === 'string') modal = document.getElementById(modal);
            if (!modal) return;
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            modal.style.display = '';
            document.body.style.overflow = 'hidden';
            // If Bootstrap modal markup, try native show when available
            if (modal.classList.contains('modal') && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                try {
                    new bootstrap.Modal(modal).show();
                    return;
                } catch (_) { /* fall through to PH */ }
            }
        };

        window.PHModal = {
            show: showModal,
            hide: hideModal,
            open: showModal,
            close: hideModal,
        };

        document.querySelectorAll('[data-modal-close]').forEach(button => {
            button.addEventListener('click', () => {
                hideModal(button.closest('[data-modal]'));
            });
        });

        // Open triggers: <button data-open-modal="addAgentModal">
        document.querySelectorAll('[data-open-modal]').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const id = button.getAttribute('data-open-modal');
                if (id) showModal(id);
            });
        });

        // Backdrop click (on overlay itself, not dialog panel)
        document.querySelectorAll('[data-modal]').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) hideModal(modal);
            });
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('[data-modal]:not(.hidden)').forEach(hideModal);
            }
        });
        console.log('✓ Modals initialized');
    },

    /**
     * AJAX辅助
     */
    async fetch(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            this.showError(error.message);
            throw error;
        }
    },

    showSuccess(message) {
        this.showToast(message, 'success', 'fa-check-circle', 'bg-green-500');
    },

    showError(message) {
        this.showToast(message, 'error', 'fa-exclamation-circle', 'bg-red-500');
    },

    showToast(message, type, icon, bgColor) {
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-4 rounded-lg shadow-lg z-50 flex items-center gap-3`;
        toast.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }
};

// 初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
} else {
    App.init();
}

window.App = App;
