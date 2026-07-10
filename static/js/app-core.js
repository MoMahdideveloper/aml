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
     * PH modal: dialog semantics, focus trap, restore opener focus.
     */
    initModals() {
        let lastOpener = null;
        let trapHandler = null;

        const focusableSelector = [
            'a[href]',
            'button:not([disabled])',
            'textarea:not([disabled])',
            'input:not([disabled]):not([type="hidden"])',
            'select:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
        ].join(',');

        const getFocusable = (root) =>
            Array.from(root.querySelectorAll(focusableSelector)).filter(
                (el) => !el.hasAttribute('disabled') && el.offsetParent !== null
            );

        const releaseTrap = () => {
            if (trapHandler) {
                document.removeEventListener('keydown', trapHandler, true);
                trapHandler = null;
            }
        };

        const hideModal = (modal) => {
            if (!modal) return;
            if (typeof modal === 'string') modal = document.getElementById(modal);
            if (!modal) return;
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
            modal.classList.remove('show');
            modal.style.display = 'none';
            document.body.style.overflow = '';
            document.querySelectorAll('.modal-backdrop').forEach((b) => b.remove());
            releaseTrap();
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                try {
                    const inst = bootstrap.Modal.getInstance(modal);
                    if (inst) inst.hide();
                } catch (_) { /* ignore */ }
            }
            if (lastOpener && typeof lastOpener.focus === 'function') {
                try {
                    lastOpener.focus();
                } catch (_) { /* ignore */ }
            }
            lastOpener = null;
        };

        const showModal = (modal, opener) => {
            if (!modal) return;
            if (typeof modal === 'string') modal = document.getElementById(modal);
            if (!modal) return;

            lastOpener = opener || document.activeElement;

            if (!modal.hasAttribute('role')) modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');
            modal.setAttribute('aria-hidden', 'false');
            modal.classList.remove('hidden');
            modal.style.display = '';
            document.body.style.overflow = 'hidden';

            if (modal.classList.contains('modal') && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                try {
                    new bootstrap.Modal(modal).show();
                } catch (_) { /* fall through to PH focus */ }
            }

            // Prefer focus inside the dialog panel if present
            const panel =
                modal.querySelector('[role="dialog"]') ||
                modal.querySelector('.bg-surface-container-lowest, .bg-white, .modal-dialog') ||
                modal;
            if (panel !== modal && !panel.hasAttribute('role')) {
                panel.setAttribute('role', 'document');
            }

            const focusables = getFocusable(modal);
            const initial =
                modal.querySelector('[data-autofocus]') ||
                focusables.find((el) => el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') ||
                focusables[0] ||
                panel;
            window.setTimeout(() => {
                try {
                    initial.focus();
                } catch (_) { /* ignore */ }
            }, 0);

            releaseTrap();
            trapHandler = (e) => {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    hideModal(modal);
                    return;
                }
                if (e.key !== 'Tab') return;
                const nodes = getFocusable(modal);
                if (!nodes.length) {
                    e.preventDefault();
                    return;
                }
                const first = nodes[0];
                const last = nodes[nodes.length - 1];
                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                } else if (!modal.contains(document.activeElement)) {
                    e.preventDefault();
                    first.focus();
                }
            };
            document.addEventListener('keydown', trapHandler, true);
        };

        window.PHModal = {
            show: (m) => showModal(m),
            hide: hideModal,
            open: (m) => showModal(m),
            close: hideModal,
        };

        document.querySelectorAll('[data-modal-close]').forEach((button) => {
            button.addEventListener('click', () => {
                hideModal(button.closest('[data-modal]'));
            });
        });

        document.querySelectorAll('[data-open-modal]').forEach((button) => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const id = button.getAttribute('data-open-modal');
                if (id) showModal(id, button);
            });
        });

        document.querySelectorAll('[data-modal]').forEach((modal) => {
            if (!modal.hasAttribute('aria-hidden')) {
                modal.setAttribute('aria-hidden', modal.classList.contains('hidden') ? 'true' : 'false');
            }
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

// Match-alert inbox (shell bell)
const PHNotif = {
    agentId: null,
    open: false,

    init() {
        this.refreshBadge();
        document.addEventListener('click', (e) => {
            if (!this.open) return;
            const root = e.target.closest('[id^="ph-notif-root"]');
            const panel = e.target.closest('[id^="ph-notif-panel"]');
            if (!root && !panel) this.closeAll();
        });
        setInterval(() => this.refreshBadge(), 60000);
    },

    _badgeEls() {
        return [
            document.getElementById('ph-notif-badge-mobile'),
            document.getElementById('ph-notif-badge-desktop'),
        ].filter(Boolean);
    },

    _listEls() {
        return [
            document.getElementById('ph-notif-list-mobile'),
            document.getElementById('ph-notif-list-desktop'),
        ].filter(Boolean);
    },

    _panelEls() {
        return [
            document.getElementById('ph-notif-panel-mobile'),
            document.getElementById('ph-notif-panel-desktop'),
        ].filter(Boolean);
    },

    async refreshBadge() {
        try {
            const res = await fetch('/api/notifications/inbox?status=unread&limit=1', {
                headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!res.ok) return;
            const data = await res.json();
            const n = data.unread_count || 0;
            if (data.default_agent_id) this.agentId = data.default_agent_id;
            this._badgeEls().forEach((el) => {
                if (n > 0) {
                    el.classList.remove('hidden');
                    el.textContent = n > 99 ? '99+' : String(n);
                } else {
                    el.classList.add('hidden');
                    el.textContent = '0';
                }
            });
        } catch (_) { /* ignore */ }
    },

    async toggle() {
        const wasOpen = this.open;
        this.closeAll();
        if (wasOpen) return;
        this.open = true;
        this._panelEls().forEach((p) => p && p.classList.remove('hidden'));
        await this.loadList();
    },

    closeAll() {
        this.open = false;
        this._panelEls().forEach((p) => p && p.classList.add('hidden'));
    },

    async loadList() {
        const lists = this._listEls();
        lists.forEach((el) => {
            el.innerHTML = '<p class="px-3 py-4 text-on-surface-variant text-xs">Loading…</p>';
        });
        try {
            const res = await fetch('/api/notifications/inbox?status=all&limit=15', {
                headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!res.ok) throw new Error('Failed');
            const data = await res.json();
            if (data.default_agent_id) this.agentId = data.default_agent_id;
            const items = data.notifications || [];
            const html =
                items.length === 0
                    ? '<p class="px-3 py-6 text-center text-on-surface-variant text-xs">No match alerts yet. High-quality matches create alerts when always-on rematch runs.</p>'
                    : items
                          .map((n) => {
                              const unread = n.status === 'unread';
                              const title = this._esc(n.title || 'Match alert');
                              const msg = this._esc((n.message || '').slice(0, 120));
                              const when = n.created_at
                                  ? new Date(n.created_at).toLocaleString()
                                  : '';
                              return (
                                  '<button type="button" class="w-full text-left px-3 py-2.5 border-b border-outline-variant hover:bg-surface-container transition-colors ' +
                                  (unread ? 'bg-primary/5' : '') +
                                  '" data-notif-id="' +
                                  n.id +
                                  '" data-agent-id="' +
                                  n.agent_id +
                                  '" onclick="PHNotif.openItem(this)">' +
                                  '<div class="flex items-start gap-2">' +
                                  '<span class="material-symbols-outlined text-[18px] text-primary mt-0.5">' +
                                  (n.priority === 'high' ? 'priority_high' : 'auto_awesome') +
                                  '</span>' +
                                  '<div class="min-w-0 flex-1">' +
                                  '<div class="text-xs font-semibold text-primary">' +
                                  title +
                                  '</div>' +
                                  '<div class="text-[11px] text-on-surface-variant mt-0.5 line-clamp-2">' +
                                  msg +
                                  '</div>' +
                                  '<div class="text-[10px] text-on-surface-variant/80 mt-1">' +
                                  when +
                                  '</div></div></div></button>'
                              );
                          })
                          .join('');
            lists.forEach((el) => {
                el.innerHTML = html;
            });
            const n = data.unread_count || 0;
            this._badgeEls().forEach((el) => {
                if (n > 0) {
                    el.classList.remove('hidden');
                    el.textContent = n > 99 ? '99+' : String(n);
                } else {
                    el.classList.add('hidden');
                }
            });
        } catch (e) {
            lists.forEach((el) => {
                el.innerHTML = '<p class="px-3 py-4 text-error text-xs">Could not load alerts.</p>';
            });
        }
    },

    async openItem(btn) {
        const id = btn.getAttribute('data-notif-id');
        const agentId = btn.getAttribute('data-agent-id') || this.agentId;
        if (id && agentId) {
            try {
                await fetch('/api/agents/' + agentId + '/notifications/' + id + '/read', {
                    method: 'POST',
                    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                });
            } catch (_) { /* ignore */ }
        }
        this.closeAll();
        window.location.href = '/recommendations';
    },

    async markAllRead() {
        if (!this.agentId) {
            await this.loadList();
            return;
        }
        try {
            await fetch('/api/agents/' + this.agentId + '/notifications/mark-all-read', {
                method: 'POST',
                headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            });
        } catch (_) { /* ignore */ }
        await this.refreshBadge();
        await this.loadList();
    },

    _esc(s) {
        return String(s ?? '').replace(/[&<>"']/g, function (m) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m];
        });
    },
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        App.init();
        PHNotif.init();
    });
} else {
    App.init();
    PHNotif.init();
}

window.App = App;
window.PHNotif = PHNotif;
