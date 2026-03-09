/**
 * TRANSOVA - Unified Theme JavaScript
 * Clean interactions without excessive animations
 */

document.addEventListener("DOMContentLoaded", function() {
    
    /* ===============================
       FAQ ACCORDION
    =============================== */
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        if (question) {
            question.addEventListener('click', () => {
                const isActive = item.classList.contains('active');
                
                // Close all other items
                faqItems.forEach(otherItem => {
                    if (otherItem !== item) {
                        otherItem.classList.remove('active');
                    }
                });
                
                // Toggle current item
                item.classList.toggle('active');
            });
        }
    });

    /* ===============================
       FILTER PANEL TOGGLE (MOBILE)
    =============================== */
    const filterToggle = document.getElementById("filter-toggle");
    const filterPanel = document.getElementById("filter-panel");

    if (filterToggle && filterPanel) {
        filterToggle.addEventListener("click", () => {
            filterPanel.classList.toggle("show");
            filterPanel.classList.toggle("d-none");
        });
    }

    /* ===============================
       SMOOTH SCROLL
    =============================== */
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    /* ===============================
       SCROLL ANIMATION OBSERVER
    =============================== */
    const observerOptions = { root: null, rootMargin: '0px', threshold: 0.1 };
    const scrollObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
            } else {
                entry.target.classList.remove('is-visible');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.animate-on-scroll').forEach(el => scrollObserver.observe(el));

    /* ===============================
       BOOTSTRAP TOOLTIPS (if loaded)
    =============================== */
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

/* ===============================
   GLOBAL UTILITY FUNCTIONS
============================== */
window.TransovaTheme = {
    // Show notification
    notify: function(message, type = 'info') {
        const toast = document.createElement('div');
        const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-danger' : 'alert-info';
        toast.className = alertClass + ' position-fixed top-0 end-0 m-3';
        toast.style.cssText = 'z-index: 9999; min-width: 250px;';
        toast.innerHTML = '<div class="d-flex align-items-center"><span>' + message + '</span><button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button></div>';
        document.body.appendChild(toast);
        
        setTimeout(function() {
            toast.remove();
        }, 5000);
    },
    
    // Loading spinner
    showLoader: function(target) {
        const loader = document.createElement('div');
        loader.className = 'position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        loader.style.cssText = 'z-index: 100; opacity: 0.8; background: rgba(0,0,0,0.5);';
        loader.innerHTML = '<div class="spinner-futuristic"></div>';
        
        const targetEl = document.querySelector(target);
        if (targetEl) {
            targetEl.style.position = 'relative';
            targetEl.appendChild(loader);
        }
        
        return loader;
    },
    
    hideLoader: function(loader) {
        if (loader && loader.remove) {
            loader.remove();
        }
    }
};

