/**
 * TRANSOVA - Unified Theme JavaScript
 * Clean interactions without excessive animations
 */

document.addEventListener("DOMContentLoaded", function() {
    
    /* ===============================
       PREMIUM FEATURES INIT
    =============================== */
    
    // Skeleton loader toggle
    function toggleSkeleton(show) {
        document.querySelectorAll('.skeleton-container').forEach(container => {
            if (show) {
                container.classList.add('loading');
            } else {
                container.classList.remove('loading');
            }
        });
    }
    
    /* ===============================
       CHART.JS DASHBOARD CHARTS
    =============================== */
    function initCharts() {
        // Stats Donut Chart (Dashboard)
        const statsCtx = document.getElementById('statsChart');
        if (statsCtx) {
            new Chart(statsCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Confirmed', 'Pending', 'Total'],
                    datasets: [{
                        data: [65, 25, 90],
                        backgroundColor: ['#22c55e', '#f59e0b', '#8b5cf6'],
                        borderWidth: 0,
                        cutout: '70%'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(24,24,31,0.95)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            borderColor: '#8b5cf6',
                            borderWidth: 1
                        }
                    }
                }
            });
        }
        
        // Bookings Timeline (Line Chart)
        const timelineCtx = document.getElementById('timelineChart');
        if (timelineCtx) {
            new Chart(timelineCtx, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
                    datasets: [{
                        label: 'Bookings',
                        data: [12, 19, 3, 5, 2],
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139,92,246,0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
    }
    
    /* ===============================
       LEAFLET MINI-MAP (Home/Dashboard)
    =============================== */
    function initMiniMap(containerId, center = [25.2048, 55.2708]) { // Dubai default
        const mapContainer = document.getElementById(containerId);
        if (!mapContainer) return;
        
        // Create Leaflet map
        const map = L.map(mapContainer).setView(center, 11);
        
        // Premium tile layer (OpenStreetMap)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        
        // Custom purple truck icon
        const truckIcon = L.divIcon({
            html: '<i class="bi bi-truck text-primary" style="font-size: 24px; color: #8b5cf6;"></i>',
            className: 'truck-marker',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
        
        // Sample trucks (replace with API data)
        const trucks = [
            { pos: [25.2048, 55.2708], name: 'Truck #AE123' },
            { pos: [25.2769, 55.2963], name: 'Truck #DX456' },
            { pos: [25.1923, 55.2744], name: 'Truck #SH789' }
        ];
        
        trucks.forEach(truck => {
            L.marker(truck.pos, { icon: truckIcon })
                .addTo(map)
                .bindPopup(`<b>${truck.name}</b><br>Available Now`);
        });
        
        // Responsive resize
        window.addEventListener('resize', () => map.invalidateSize());
    }
    
    /* ===============================
       ANIMATED STATS COUNTER
    =============================== */
    function animateCounters() {
        const counters = document.querySelectorAll('.stat-number');
        const duration = 2000;
        
        counters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-target') || counter.textContent);
            const increment = target / (duration / 16);
            let current = 0;
            
            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    counter.textContent = Math.floor(current) + '+';
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target + '+';
                }
            };
            
            // Trigger on scroll into view
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        updateCounter();
                        observer.unobserve(entry.target);
                    }
                });
            });
            observer.observe(counter);
        });
    }
    
    /* ===============================
       CONFetti CELEBRATION (Booking Success)
    =============================== */
    function showConfetti() {
        // canvas-confetti (load CDN if needed)
        if (typeof confetti === 'undefined') return;
        
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 },
            colors: ['#8b5cf6', '#a78bfa', '#c084fc']
        });
    }
    
    /* ===============================
       CSV EXPORT BUTTONS
    =============================== */
    function initCsvExports() {
        document.querySelectorAll('.btn-export-csv').forEach(btn => {
            btn.addEventListener('click', function() {
                const table = document.getElementById(this.dataset.table);
                if (!table) return;
                
                let csv = [];
                table.querySelectorAll('tr').forEach(row => {
                    const cols = row.querySelectorAll('td, th');
                    csv.push(Array.from(cols).map(col => col.textContent.trim()).join(','));
                });
                
                const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'transova-data.csv';
                a.click();
            });
        });
    }
    
    /* ===============================
       NOTIFICATION SYSTEM (Toasts)
    =============================== */
    function showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container');
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'primary'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    }
    
    /* ===============================
       FAQ ACCORDION (Legacy)
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
    document.querySelectorAll('a[href^=\"#\"]').forEach(anchor => {
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
       HERO POPUP SPECIAL HANDLING
    =============================== */
    const heroModalEl = document.getElementById('heroTaglineModal');
    if (heroModalEl) {
        heroModalEl.addEventListener('shown.bs.modal', function () {
            // Trigger animation for popup elements using existing observer
            const popupAnimateEls = heroModalEl.querySelectorAll('.animate-on-scroll');
            popupAnimateEls.forEach(el => {
                if (!el.classList.contains('is-visible')) {
                    scrollObserver.observe(el);
                }
            });
        });
        
        heroModalEl.addEventListener('hidden.bs.modal', function () {
            // Reset animations
            const popupAnimateEls = heroModalEl.querySelectorAll('.animate-on-scroll');
            popupAnimateEls.forEach(el => {
                el.classList.remove('is-visible');
            });
        });
    }

    /* ===============================
       BOOTSTRAP TOOLTIPS (if loaded)
    =============================== */
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle=\"tooltip\"]'));
        tooltipTriggerList.map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

/* ===============================
   PROMO CODE FUNCTIONS
============================== */
async function applyPromo() {
    const promoCode = document.getElementById('promo_code').value.trim().toUpperCase();
    const promoMessage = document.getElementById('promoMessage');
    const applyBtn = document.getElementById('applyPromoBtn');
    const promoDiscount = document.getElementById('promo_discount_percent');
    
    if (!promoCode) {
        promoMessage.innerHTML = '';
        promoDiscount.value = '0';
        return;
    }
    
    // Disable button and show loading
    applyBtn.disabled = true;
    applyBtn.innerHTML = '<i class="spinner-border spinner-border-sm me-1"></i>Validating...';
    
    try {
        const response = await fetch('/api/validate-promo/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({promo_code: promoCode})
        });
        
        const data = await response.json();
        
        if (data.success) {
            promoMessage.innerHTML = `<div class="alert alert-success py-2 mb-0 small">
                ✅ ${data.promo_code} applied! ${data.discount_percent}% OFF
            </div>`;
            promoDiscount.value = data.discount_percent;
            updatePrice();  // Recalculate price with discount
        } else {
            promoMessage.innerHTML = `<div class="alert alert-danger py-2 mb-0 small">
                ❌ ${data.error || 'Invalid promo code'}
            </div>`;
            promoDiscount.value = '0';
        }
    } catch (error) {
        promoMessage.innerHTML = '<div class="alert alert-danger py-2 mb-0 small">Network error. Try again.</div>';
        promoDiscount.value = '0';
    } finally {
        applyBtn.disabled = false;
        applyBtn.innerHTML = 'Apply';
    }
}

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
        toast.innerHTML = '<div class=\"d-flex align-items-center\"><span>' + message + '</span><button type=\"button\" class=\"btn-close ms-auto\" onclick=\"this.parentElement.parentElement.remove()\"></button></div>';
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
        loader.innerHTML = '<div class=\"spinner-futuristic\"></div>';
        
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

