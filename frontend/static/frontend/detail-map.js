const detailMapEl = document.querySelector("#detailLeafletMap");

function detailLandmarks() {
    return JSON.parse(document.querySelector("#nearbyLandmarksData")?.textContent || "[]")
        .filter((landmark) => Number.isFinite(Number(landmark.latitude)) && Number.isFinite(Number(landmark.longitude)));
}

function detailMarkerIcon(className, label, options = {}) {
    return window.L.divIcon({
        className,
        html: `<span>${label}</span>`,
        iconSize: options.iconSize || [30, 30],
        iconAnchor: options.iconAnchor || [15, 15],
        popupAnchor: options.popupAnchor || [0, -14],
    });
}

function detailBounds(items) {
    const latitudes = items.map((item) => Number(item.latitude));
    const longitudes = items.map((item) => Number(item.longitude));
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    const latPadding = Math.max((maxLat - minLat) * 0.18, 0.003);
    const lngPadding = Math.max((maxLng - minLng) * 0.18, 0.003);
    return {
        minLat: minLat - latPadding,
        maxLat: maxLat + latPadding,
        minLng: minLng - lngPadding,
        maxLng: maxLng + lngPadding,
    };
}

function detailMarkerPosition(item, bounds) {
    const latitude = Number(item.latitude);
    const longitude = Number(item.longitude);
    const x = ((longitude - bounds.minLng) / (bounds.maxLng - bounds.minLng)) * 100;
    const y = (1 - (latitude - bounds.minLat) / (bounds.maxLat - bounds.minLat)) * 100;
    return {
        left: `${Math.min(92, Math.max(8, x))}%`,
        top: `${Math.min(88, Math.max(12, y))}%`,
    };
}

function renderDetailStaticMap(latitude, longitude) {
    const landmarks = detailLandmarks();
    const items = [{ latitude, longitude }, ...landmarks];
    const bounds = detailBounds(items);
    detailMapEl.replaceChildren();

    const backdrop = document.createElement("div");
    backdrop.className = "local-map-backdrop";
    ["Bắc", "Nam"].forEach((label, index) => {
        const axis = document.createElement("span");
        axis.className = index === 0 ? "map-axis map-axis-north" : "map-axis map-axis-south";
        axis.textContent = label;
        backdrop.append(axis);
    });
    detailMapEl.append(backdrop);

    const roomMarker = document.createElement("span");
    roomMarker.className = "detail-map-pin";
    roomMarker.setAttribute("aria-label", "Vị trí phòng đang xem");
    roomMarker.title = "Vị trí phòng đang xem";
    Object.assign(roomMarker.style, detailMarkerPosition({ latitude, longitude }, bounds));
    detailMapEl.append(roomMarker);

    landmarks.forEach((landmark) => {
        const marker = document.createElement("span");
        marker.className = `landmark-marker landmark-${landmark.type}`;
        marker.textContent = landmark.type_label?.slice(0, 1) || "L";
        marker.title = `${landmark.type_label}: ${landmark.name}`;
        Object.assign(marker.style, detailMarkerPosition(landmark, bounds));
        detailMapEl.append(marker);
    });
}

function renderDetailLeafletMap() {
    if (!detailMapEl || typeof window.L === "undefined") {
        if (detailMapEl) {
            const latitude = Number(detailMapEl.dataset.latitude);
            const longitude = Number(detailMapEl.dataset.longitude);
            if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
                renderDetailStaticMap(latitude, longitude);
            }
        }
        return;
    }
    const latitude = Number(detailMapEl.dataset.latitude);
    const longitude = Number(detailMapEl.dataset.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        return;
    }
    detailMapEl.replaceChildren();
    const map = window.L.map(detailMapEl, {
        scrollWheelZoom: true,
        zoomControl: true,
    }).setView([latitude, longitude], 15);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
    }).addTo(map);
    window.L.marker([latitude, longitude], {
        icon: detailMarkerIcon("leaflet-detail-room-marker", "", {
            iconSize: [36, 44],
            iconAnchor: [18, 42],
            popupAnchor: [0, -38],
        }),
    }).bindPopup(`<strong>${detailMapEl.dataset.title || "Phòng trọ"}</strong>`).addTo(map);

    const landmarks = detailLandmarks();
    const bounds = [[latitude, longitude]];
    landmarks.forEach((landmark) => {
        if (!landmark.latitude || !landmark.longitude) {
            return;
        }
        const latLng = [Number(landmark.latitude), Number(landmark.longitude)];
        window.L.marker(latLng, {
            icon: detailMarkerIcon(`leaflet-landmark-marker landmark-${landmark.type}`, landmark.type_label?.slice(0, 1) || "L"),
        }).bindPopup(`<strong>${landmark.type_label}</strong><br>${landmark.name}`).addTo(map);
        bounds.push(latLng);
    });
    if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [26, 26], maxZoom: 15 });
    }
    setTimeout(() => {
        map.invalidateSize();
        if (!detailMapEl.querySelector(".leaflet-marker-icon")) {
            map.remove();
            renderDetailStaticMap(latitude, longitude);
        }
    }, 800);
}

renderDetailLeafletMap();
