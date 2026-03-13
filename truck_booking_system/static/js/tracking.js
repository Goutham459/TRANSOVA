// Live GPS Tracking JS - Leaflet Map
// Auto-refreshes truck location every 10 seconds

let map;
let truckMarker;
let routeLayer;

function initTrackingMap(pickupLat, pickupLng, dropLat, dropLng, truckLat, truckLng, bookingId) {
    // Initialize Leaflet map
    map = L.map('tracking-map').setView([truckLat, truckLng], 12);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Add markers
    L.marker([pickupLat, pickupLng], {
        icon: L.divIcon({
            className: 'pickup-marker',
            html: '<i class="bi bi-geo-alt-fill" style="color: #10b981; font-size: 24px;"></i>',
            iconSize: [30, 30]
        })
    }).addTo(map).bindPopup('Pickup Location');
    
    L.marker([dropLat, dropLng], {
        icon: L.divIcon({
            className: 'drop-marker',
            html: '<i class="bi bi-geo-fill" style="color: #ef4444; font-size: 24px;"></i>',
            iconSize: [30, 30]
        })
    }).addTo(map).bindPopup('Drop Location');
    
    // Truck marker (animated)
    truckMarker = L.marker([truckLat, truckLng], {
        icon: L.divIcon({
            className: 'truck-marker',
            html: '<i class="bi bi-truck" style="color: #3b82f6; font-size: 28px; animation: pulse 2s infinite;"></i>',
            iconSize: [36, 36]
        })
    }).addTo(map).bindPopup('Your Truck - Live Location');
    
    // Draw route line
    const route = [[pickupLat, pickupLng], [truckLat, truckLng], [dropLat, dropLng]];
    routeLayer = L.polyline(route, {
        color: '#3b82f6',
        weight: 4,
        opacity: 0.8
    }).addTo(map);
    
    map.fitBounds(routeLayer.getBounds());
    
    // Auto-update location every 10s
    setInterval(() => updateTruckLocation(bookingId), 10000);
    updateTruckLocation(bookingId); // Initial update
}

async function updateTruckLocation(bookingId) {
    try {
        const response = await fetch(`/bookings/api/truck-location/${bookingId}/`);
        const data = await response.json();
        
        if (data.truck) {
            const newPos = [data.truck.lat, data.truck.lng];
            
            // Animate truck movement
            truckMarker.setLatLng(newPos);
            
            // Update route
            const route = [
                [data.pickup.lat, data.pickup.lng],
                newPos,
                [data.dropoff.lat, data.dropoff.lng]
            ];
            routeLayer.setLatLngs(route);
            
            // Update ETA (simple distance calc)
            const distanceKm = data.distance_km || 0;
            const eta = Math.round(distanceKm / 50); // 50km/hr avg
            document.getElementById('eta-display').textContent = `${eta} min ETA`;
            
            map.panTo(newPos, {animate: true, duration: 1});
        }
    } catch (error) {
        console.error('GPS update failed:', error);
    }
}

function rateCompany(companyId) {
    // Star rating popup
    const rating = prompt('Rate this company (1-5 stars):');
    if (rating && rating >= 1 && rating <= 5) {
        fetch(`/bookings/rate-company/${companyId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({rating: rating})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert('Rating failed: ' + data.error);
            }
        });
    }
}

// CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    #tracking-map { height: 500px; border-radius: 16px; }
    #eta-display { font-weight: bold; color: #10b981; }
`;
document.head.appendChild(style);

