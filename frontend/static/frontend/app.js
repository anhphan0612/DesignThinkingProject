const state = {
    amenities: [],
    universities: [],
    rooms: [],
    activeRoomId: null,
    leafletMap: null,
    roomLayer: null,
    landmarkLayer: null,
    compareRoomIds: [],
    isAuthenticated: document.querySelector("meta[name='is-authenticated']").content === "true",
};

const els = {
    query: document.querySelector("#query"),
    university: document.querySelector("#university"),
    distance: document.querySelector("#distance"),
    minPrice: document.querySelector("#minPrice"),
    maxPrice: document.querySelector("#maxPrice"),
    minArea: document.querySelector("#minArea"),
    sort: document.querySelector("#sortRooms"),
    amenities: document.querySelector("#amenities"),
    apply: document.querySelector("#applyFilters"),
    reset: document.querySelector("#resetFilters"),
    roomList: document.querySelector("#roomList"),
    resultCount: document.querySelector("#resultCount"),
    status: document.querySelector("#status"),
    recommendationBox: document.querySelector("#recommendationBox"),
    recommendationList: document.querySelector("#recommendationList"),
    recommendationCount: document.querySelector("#recommendationCount"),
    heroRoomCount: document.querySelector("#heroRoomCount"),
    mapPanel: document.querySelector("#mapPanel"),
    map: document.querySelector("#resultsMap"),
    mapTitle: document.querySelector("#mapTitle"),
    mapCount: document.querySelector("#mapCount"),
    mapHint: document.querySelector("#mapHint"),
    compareBar: document.querySelector("#compareBar"),
    compareCount: document.querySelector("#compareCount"),
    compareNames: document.querySelector("#compareNames"),
    openCompare: document.querySelector("#openCompare"),
    clearCompare: document.querySelector("#clearCompare"),
    compareModal: document.querySelector("#compareModal"),
    closeCompare: document.querySelector("#closeCompare"),
    compareTable: document.querySelector("#compareTable"),
};

function formatCurrency(value) {
    return new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0,
    }).format(Number(value));
}

function formatNumber(value, suffix = "") {
    if (value === null || value === undefined || value === "") {
        return "Chưa cập nhật";
    }
    const number = Number(value);
    if (!Number.isFinite(number)) {
        return "Chưa cập nhật";
    }
    return `${new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 }).format(number)}${suffix}`;
}

function csrfToken() {
    return document.querySelector("meta[name='csrf-token']").content;
}

function endpoint(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        if (Array.isArray(value)) {
            value.filter(Boolean).forEach((item) => url.searchParams.append(key, item));
        } else if (value !== undefined && value !== null && value !== "") {
            url.searchParams.set(key, value);
        }
    });
    return url;
}

async function fetchJson(path, params) {
    const response = await fetch(endpoint(path, params));
    if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
    }
    return response.json();
}

async function sendJson(path, method = "POST", body = {}) {
    const response = await fetch(path, {
        method,
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
    }
    return response.json();
}

function textElement(tagName, text, className) {
    const element = document.createElement(tagName);
    if (className) {
        element.className = className;
    }
    element.textContent = text;
    return element;
}

function tagElement(text) {
    return textElement("span", text, "tag");
}

function valueOrFallback(value, fallback = "Chưa cập nhật") {
    if (value === null || value === undefined || value === "") {
        return fallback;
    }
    return value;
}

function roomById(roomId) {
    return state.rooms.find((room) => room.id === roomId);
}

function selectedCompareRooms() {
    return state.compareRoomIds.map(roomById).filter(Boolean);
}

function amenityNames(room) {
    const names = (room.amenities || []).map((amenity) => amenity.name);
    return names.length ? names.join(", ") : "Chưa cập nhật";
}

function verificationLabel(room) {
    return room.verification_level_label || room.verification_level || "Chưa xác minh";
}

function updateCompareControls() {
    const selectedRooms = selectedCompareRooms();
    els.compareBar.hidden = selectedRooms.length === 0;
    els.compareCount.textContent = `Đã chọn ${selectedRooms.length}/2 phòng`;
    els.compareNames.textContent = selectedRooms.length
        ? selectedRooms.map((room) => room.title).join(" và ")
        : "Chọn phòng để xem bảng so sánh.";
    els.openCompare.disabled = selectedRooms.length !== 2;
    document.querySelectorAll(".compare-button").forEach((button) => {
        const isSelected = state.compareRoomIds.includes(Number(button.dataset.roomId));
        button.classList.toggle("active", isSelected);
        button.setAttribute("aria-pressed", isSelected ? "true" : "false");
        button.textContent = isSelected ? "Đã chọn so sánh" : "So sánh";
    });
}

function toggleCompare(room) {
    const exists = state.compareRoomIds.includes(room.id);
    if (exists) {
        state.compareRoomIds = state.compareRoomIds.filter((id) => id !== room.id);
        updateCompareControls();
        return;
    }
    if (state.compareRoomIds.length >= 2) {
        showStatus("Chỉ có thể so sánh tối đa 2 phòng cùng lúc. Hãy bỏ chọn một phòng trước.", true);
        return;
    }
    state.compareRoomIds.push(room.id);
    showStatus("");
    updateCompareControls();
}

function compareValue(label, first, second) {
    const row = document.createElement("div");
    row.className = "compare-row";
    row.append(
        textElement("div", label, "compare-label"),
        textElement("div", first, "compare-cell"),
        textElement("div", second, "compare-cell"),
    );
    return row;
}

function renderCompareTable() {
    const [first, second] = selectedCompareRooms();
    if (!first || !second) {
        return;
    }
    els.compareTable.replaceChildren();
    const header = document.createElement("div");
    header.className = "compare-row compare-row-head";
    header.append(
        textElement("div", "Tiêu chí", "compare-label"),
        textElement("div", first.title, "compare-cell"),
        textElement("div", second.title, "compare-cell"),
    );
    const rows = [
        compareValue("Giá thuê", `${formatCurrency(first.price)}/tháng`, `${formatCurrency(second.price)}/tháng`),
        compareValue("Tiền cọc", first.deposit ? formatCurrency(first.deposit) : "Chưa cập nhật", second.deposit ? formatCurrency(second.deposit) : "Chưa cập nhật"),
        compareValue("Diện tích", formatNumber(first.area, " m²"), formatNumber(second.area, " m²")),
        compareValue("Số người tối đa", `${first.max_occupants} người`, `${second.max_occupants} người`),
        compareValue("Khu vực", `${first.ward_name}, ${first.district_name}`, `${second.ward_name}, ${second.district_name}`),
        compareValue("Địa chỉ", first.address, second.address),
        compareValue("Khoảng cách", valueOrFallback(first.distance_km ? formatNumber(first.distance_km, " km") : ""), valueOrFallback(second.distance_km ? formatNumber(second.distance_km, " km") : "")),
        compareValue("Điện", first.electricity_price ? `${formatCurrency(first.electricity_price)}/kWh` : "Chưa cập nhật", second.electricity_price ? `${formatCurrency(second.electricity_price)}/kWh` : "Chưa cập nhật"),
        compareValue("Nước", first.water_price ? `${formatCurrency(first.water_price)}/m³` : "Chưa cập nhật", second.water_price ? `${formatCurrency(second.water_price)}/m³` : "Chưa cập nhật"),
        compareValue("Tiện ích", amenityNames(first), amenityNames(second)),
        compareValue("Xác minh", verificationLabel(first), verificationLabel(second)),
    ];
    els.compareTable.append(header, ...rows);
}

function openCompareModal() {
    if (selectedCompareRooms().length !== 2) {
        return;
    }
    renderCompareTable();
    els.compareModal.hidden = false;
}

function closeCompareModal() {
    els.compareModal.hidden = true;
}

function clearCompare() {
    state.compareRoomIds = [];
    closeCompareModal();
    updateCompareControls();
}

function landmarkSummary(room) {
    const landmarks = room.nearby_landmarks || [];
    if (!landmarks.length) {
        return "";
    }
    return landmarks
        .slice(0, 3)
        .map((landmark) => `${landmark.type_label}: ${landmark.name}${landmark.distance_km ? ` (${formatNumber(landmark.distance_km, " km")})` : ""}`)
        .join(" · ");
}

function checkedAmenityIds() {
    return Array.from(document.querySelectorAll("input[name='amenity']:checked")).map((input) => input.value);
}

function currentFilters() {
    const university = els.university.value;
    return {
        q: els.query.value.trim(),
        university,
        max_distance_km: university ? els.distance.value : "",
        min_price: els.minPrice.value,
        max_price: els.maxPrice.value,
        min_area: els.minArea.value,
        amenity: checkedAmenityIds(),
        sort: els.sort.value,
    };
}

function showStatus(message, isError = false) {
    els.status.hidden = !message;
    els.status.textContent = message || "";
    els.status.style.background = isError ? "#fef2f2" : "#fff7ed";
    els.status.style.color = isError ? "#991b1b" : "#9a3412";
}

function renderUniversities() {
    state.universities.forEach((university) => {
        const option = document.createElement("option");
        option.value = university.id;
        option.textContent = `${university.short_name || "UNI"} - ${university.name}`;
        els.university.append(option);
    });
}

function renderAmenities() {
    els.amenities.replaceChildren();
    state.amenities.forEach((amenity) => {
        const label = document.createElement("label");
        label.className = "check";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = "amenity";
        input.value = amenity.id;
        label.append(input, textElement("span", amenity.name));
        els.amenities.append(label);
    });
}

function renderEmptyRooms() {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.append(
        textElement("p", "Không có kết quả", "eyebrow"),
        textElement("h2", "Thử giảm điều kiện lọc"),
        textElement("p", "Hiện chưa có phòng phù hợp với điều kiện bạn chọn.", "muted"),
    );
    els.roomList.replaceChildren(empty);
}

function geocodedRooms() {
    return state.rooms.filter((room) => (
        room.location_status === "geocoded"
        && Number.isFinite(Number(room.latitude))
        && Number.isFinite(Number(room.longitude))
    ));
}

function mapBounds(rooms) {
    const latitudes = rooms.map((item) => Number(item.latitude));
    const longitudes = rooms.map((item) => Number(item.longitude));
    return {
        minLat: Math.min(...latitudes),
        maxLat: Math.max(...latitudes),
        minLng: Math.min(...longitudes),
        maxLng: Math.max(...longitudes),
    };
}

function markerPosition(room, bounds) {
    const latitude = Number(room.latitude);
    const longitude = Number(room.longitude);
    const latRange = bounds.maxLat - bounds.minLat || 0.01;
    const lngRange = bounds.maxLng - bounds.minLng || 0.01;
    const left = 8 + ((longitude - bounds.minLng) / lngRange) * 84;
    const top = 92 - ((latitude - bounds.minLat) / latRange) * 84;
    return {
        left: Math.max(6, Math.min(94, left)),
        top: Math.max(6, Math.min(94, top)),
    };
}

function landmarkMapItems(activeRoom) {
    return (activeRoom?.nearby_landmarks || [])
        .filter((landmark) => Number.isFinite(Number(landmark.latitude)) && Number.isFinite(Number(landmark.longitude)))
        .map((landmark) => ({
            ...landmark,
            latitude: landmark.latitude,
            longitude: landmark.longitude,
        }));
}

function hasLeaflet() {
    return typeof window.L !== "undefined" && els.map;
}

function markerIcon(className, label) {
    return window.L.divIcon({
        className,
        html: `<span>${label}</span>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
        popupAnchor: [0, -14],
    });
}

function ensureLeafletMap() {
    if (!hasLeaflet()) {
        return false;
    }
    if (!state.leafletMap) {
        state.leafletMap = window.L.map(els.map, {
            scrollWheelZoom: true,
            zoomControl: true,
        });
        window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap",
        }).addTo(state.leafletMap);
        state.roomLayer = window.L.layerGroup().addTo(state.leafletMap);
        state.landmarkLayer = window.L.layerGroup().addTo(state.leafletMap);
    }
    return true;
}

function renderLeafletMap(activeRoom) {
    const mapped = geocodedRooms();
    if (!ensureLeafletMap() || !mapped.length) {
        return false;
    }
    const selectedRoom = activeRoom || mapped[0];
    state.roomLayer.clearLayers();
    state.landmarkLayer.clearLayers();
    const bounds = [];
    mapped.forEach((room, index) => {
        const latLng = [Number(room.latitude), Number(room.longitude)];
        const marker = window.L.marker(latLng, {
            icon: markerIcon(room.id === selectedRoom.id ? "leaflet-room-marker active" : "leaflet-room-marker", index + 1),
        }).bindPopup(`<strong>${room.title}</strong><br>${formatCurrency(room.price)}/tháng`);
        marker.on("click", () => updateMap(room));
        marker.addTo(state.roomLayer);
        bounds.push(latLng);
    });
    landmarkMapItems(selectedRoom).forEach((landmark) => {
        const latLng = [Number(landmark.latitude), Number(landmark.longitude)];
        window.L.marker(latLng, {
            icon: markerIcon(`leaflet-landmark-marker landmark-${landmark.type}`, landmark.type_label?.slice(0, 1) || "L"),
        }).bindPopup(`<strong>${landmark.type_label}</strong><br>${landmark.name}`).addTo(state.landmarkLayer);
        bounds.push(latLng);
    });
    if (bounds.length === 1) {
        state.leafletMap.setView(bounds[0], 15);
    } else {
        state.leafletMap.fitBounds(bounds, { padding: [28, 28], maxZoom: 15 });
    }
    setTimeout(() => state.leafletMap.invalidateSize(), 0);
    return true;
}

function renderLocalMap(activeRoom) {
    const mapped = geocodedRooms();
    if (mapped.length && renderLeafletMap(activeRoom)) {
        return;
    }
    els.map.replaceChildren();
    if (!mapped.length) {
        const empty = document.createElement("div");
        empty.className = "local-map-empty";
        empty.append(
            textElement("strong", "Chưa có phòng được ghim tọa độ"),
            textElement("span", "Hãy cập nhật địa chỉ/geocoding hoặc chạy lại dữ liệu demo để kiểm tra bản đồ."),
        );
        els.map.append(empty);
        return;
    }
    const landmarks = landmarkMapItems(activeRoom);
    const bounds = mapBounds([...mapped, ...landmarks]);
    const backdrop = document.createElement("div");
    backdrop.className = "local-map-backdrop";
    backdrop.append(
        textElement("span", "Bắc", "map-axis map-axis-north"),
        textElement("span", "Nam", "map-axis map-axis-south"),
    );
    els.map.append(backdrop);
    mapped.forEach((room, index) => {
        const position = markerPosition(room, bounds);
        const marker = document.createElement("button");
        marker.type = "button";
        marker.className = room.id === activeRoom.id ? "map-marker active" : "map-marker";
        marker.style.left = `${position.left}%`;
        marker.style.top = `${position.top}%`;
        marker.setAttribute("aria-label", room.title);
        marker.title = room.title;
        marker.textContent = String(index + 1);
        marker.addEventListener("click", (event) => {
            event.stopPropagation();
            updateMap(room);
        });
        els.map.append(marker);
    });
    landmarks.forEach((landmark) => {
        const position = markerPosition(landmark, bounds);
        const marker = document.createElement("span");
        marker.className = `landmark-marker landmark-${landmark.type}`;
        marker.style.left = `${position.left}%`;
        marker.style.top = `${position.top}%`;
        marker.title = `${landmark.type_label}: ${landmark.name}`;
        marker.textContent = landmark.type_label?.slice(0, 1) || "L";
        els.map.append(marker);
    });
}

function updateMap(room = null) {
    const mapped = geocodedRooms();
    els.mapPanel.hidden = state.rooms.length === 0;
    els.mapCount.textContent = `${mapped.length} vị trí`;
    if (!mapped.length) {
        renderLocalMap(null);
        els.mapTitle.textContent = "Chưa có vị trí bản đồ";
        els.mapHint.textContent = "Danh sách hiện có phòng, nhưng chưa phòng nào có tọa độ hợp lệ để ghim lên bản đồ.";
        return;
    }

    const activeRoom = room || mapped.find((item) => item.id === state.activeRoomId) || mapped[0];
    state.activeRoomId = activeRoom.id;
    els.mapTitle.textContent = activeRoom.title;
    renderLocalMap(activeRoom);
    els.mapHint.textContent = `${activeRoom.address}. Bản đồ đang hiển thị phòng được chọn trong danh sách.`;
    document.querySelectorAll(".room-card").forEach((card) => {
        card.classList.toggle("active", Number(card.dataset.roomId) === activeRoom.id);
    });
}

function renderRooms() {
    els.roomList.replaceChildren();
    els.resultCount.textContent = `${state.rooms.length} phòng`;
    if (els.heroRoomCount) {
        els.heroRoomCount.textContent = state.rooms.length;
    }
    if (!state.rooms.length) {
        els.mapPanel.hidden = true;
        clearCompare();
        renderEmptyRooms();
        return;
    }
    state.compareRoomIds = state.compareRoomIds.filter((id) => state.rooms.some((room) => room.id === id));
    state.rooms.forEach((room) => els.roomList.append(roomCard(room)));
    updateMap();
    updateCompareControls();
}

function renderRecommendations(items) {
    if (!items.length) {
        els.recommendationBox.hidden = true;
        return;
    }
    els.recommendationBox.hidden = false;
    els.recommendationCount.textContent = `${items.length} phòng`;
    els.recommendationList.replaceChildren();
    const profileMeta = items[0]?.score_detail?.profile;
    if (profileMeta?.is_cold_start) {
        const hint = document.createElement("div");
        hint.className = "recommendation-hint";
        hint.textContent = "Gợi ý sẽ chính xác hơn khi bạn bổ sung trường, ngân sách và khu vực ưu tiên trong hồ sơ.";
        els.recommendationList.append(hint);
    }
    items.slice(0, 3).forEach((item) => {
        const element = document.createElement("div");
        element.className = "recommendation-item";
        const copy = document.createElement("div");
        const reasons = item.score_detail?.reasons || ["Phù hợp với hồ sơ của bạn"];
        const reasonList = document.createElement("div");
        reasonList.className = "reason-list";
        reasons.slice(0, 4).forEach((reason) => {
            reasonList.append(textElement("span", reason, "reason-chip"));
        });
        copy.append(
            textElement("strong", item.room.title),
            reasonList,
        );
        element.append(copy, textElement("span", `${Math.round(item.score * 100)}% phù hợp`, "recommendation-score"));
        element.addEventListener("click", () => {
            window.location.href = `/rooms/${item.room.id}/`;
        });
        els.recommendationList.append(element);
    });
}

function roomCard(room) {
    const card = document.createElement("article");
    card.className = "room-card";
    card.tabIndex = 0;
    card.dataset.roomId = room.id;
    card.setAttribute("role", "link");
    card.setAttribute("aria-label", `Xem chi tiết ${room.title}`);

    const cover = room.images.find((image) => image.is_cover) || room.images[0];
    const thumb = document.createElement("div");
    thumb.className = "thumb";
    if (cover) {
        const image = document.createElement("img");
        image.src = cover.image;
        image.alt = cover.caption || room.title;
        thumb.append(image);
    } else {
        thumb.append(textElement("span", "ẢNH"));
    }

    const content = document.createElement("div");
    const hasDistance = room.distance_km !== null && room.distance_km !== undefined && room.distance_km !== "";
    const distance = hasDistance ? `Cách trường ${formatNumber(room.distance_km, " km")}` : "Chưa lọc theo trường";
    const location = room.location_status === "geocoded" ? "Có bản đồ" : "Chưa ghim bản đồ";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.append(
        textElement("span", formatNumber(room.area, " m²")),
        textElement("span", `${room.max_occupants} người`),
        textElement("span", distance),
        textElement("span", location),
    );

    const tags = document.createElement("div");
    tags.className = "tags";
    (room.amenities || []).slice(0, 4).forEach((amenity) => tags.append(tagElement(amenity.name)));
    const landmarkText = landmarkSummary(room);

    const cardActions = document.createElement("div");
    cardActions.className = "card-actions-row";
    const detailLink = document.createElement("a");
    detailLink.className = "card-link";
    detailLink.href = `/rooms/${room.id}/`;
    detailLink.textContent = "Xem chi tiết";
    detailLink.addEventListener("click", (event) => event.stopPropagation());
    const favoriteButton = document.createElement("button");
    favoriteButton.type = "button";
    favoriteButton.className = room.is_favorited ? "favorite-button active" : "favorite-button";
    favoriteButton.textContent = room.is_favorited ? "Đã lưu" : "Lưu phòng";
    favoriteButton.setAttribute("aria-pressed", room.is_favorited ? "true" : "false");
    favoriteButton.addEventListener("click", async (event) => {
        event.stopPropagation();
        if (!state.isAuthenticated) {
            window.location.href = `/auth/login/?next=/rooms/${room.id}/`;
            return;
        }
        favoriteButton.disabled = true;
        try {
            if (room.is_favorited) {
                await sendJson(`/api/rooms/${room.id}/unfavorite/`, "DELETE");
                room.is_favorited = false;
            } else {
                await sendJson(`/api/rooms/${room.id}/favorite/`, "POST");
                room.is_favorited = true;
            }
            favoriteButton.classList.toggle("active", room.is_favorited);
            favoriteButton.textContent = room.is_favorited ? "Đã lưu" : "Lưu phòng";
            favoriteButton.setAttribute("aria-pressed", room.is_favorited ? "true" : "false");
        } catch (error) {
            showStatus("Không cập nhật được phòng yêu thích. Hãy thử lại.", true);
            console.error(error);
        } finally {
            favoriteButton.disabled = false;
        }
    });
    const compareButton = document.createElement("button");
    compareButton.type = "button";
    compareButton.className = "secondary compare-button";
    compareButton.dataset.roomId = room.id;
    compareButton.setAttribute("aria-pressed", state.compareRoomIds.includes(room.id) ? "true" : "false");
    compareButton.textContent = state.compareRoomIds.includes(room.id) ? "Đã chọn so sánh" : "So sánh";
    compareButton.addEventListener("click", (event) => {
        event.stopPropagation();
        toggleCompare(room);
    });
    cardActions.append(detailLink, favoriteButton, compareButton);
    content.append(
        textElement("h3", room.title),
        textElement("div", `${formatCurrency(room.price)}/tháng`, "price"),
        meta,
        textElement("p", room.address, "muted"),
        landmarkText ? textElement("p", landmarkText, "landmark-summary") : "",
        tags,
        cardActions,
    );
    card.append(thumb, content);

    card.addEventListener("mouseenter", () => updateMap(room));
    card.addEventListener("focus", () => updateMap(room));
    card.addEventListener("click", () => {
        window.location.href = `/rooms/${room.id}/`;
    });
    card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            window.location.href = `/rooms/${room.id}/`;
        }
    });
    return card;
}

async function loadRecommendations() {
    if (!state.isAuthenticated) {
        return;
    }
    try {
        const recommendations = await fetchJson("/api/recommendations/", { q: els.query.value.trim(), limit: 10 });
        renderRecommendations(recommendations);
    } catch (error) {
        els.recommendationBox.hidden = true;
        console.error(error);
    }
}

async function loadRooms() {
    showStatus("Đang tải phòng phù hợp...");
    try {
        const data = await fetchJson("/api/rooms/", currentFilters());
        state.rooms = data.results || [];
        state.activeRoomId = null;
        if (data.search_intelligence?.fallback_used) {
            showStatus("Không tìm thấy kết quả khớp chính xác với từ khóa, đang hiển thị các phòng gần với nhu cầu hơn.");
        } else {
            showStatus("");
        }
        renderRooms();
        await loadRecommendations();
    } catch (error) {
        showStatus("Không tải được danh sách phòng. Hãy kiểm tra server Django và API.", true);
        console.error(error);
    }
}

async function bootstrap() {
    try {
        const [universities, amenities] = await Promise.all([
            fetchJson("/api/universities/"),
            fetchJson("/api/amenities/"),
        ]);
        state.universities = universities.results || [];
        state.amenities = amenities.results || [];
        renderUniversities();
        renderAmenities();
        await loadRooms();
    } catch (error) {
        showStatus("Không tải được dữ liệu cần thiết. Hãy thử tải lại trang sau ít phút.", true);
        console.error(error);
    }
}

els.apply.addEventListener("click", loadRooms);
els.sort.addEventListener("change", loadRooms);
els.reset.addEventListener("click", () => {
    els.query.value = "";
    els.university.value = "";
    els.distance.value = "2";
    els.minPrice.value = "";
    els.maxPrice.value = "";
    els.minArea.value = "";
    els.sort.value = "newest";
    document.querySelectorAll("input[name='amenity']").forEach((input) => {
        input.checked = false;
    });
    loadRooms();
});
els.query.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        loadRooms();
    }
});
els.openCompare.addEventListener("click", openCompareModal);
els.clearCompare.addEventListener("click", clearCompare);
els.closeCompare.addEventListener("click", closeCompareModal);
els.compareModal.addEventListener("click", (event) => {
    if (event.target === els.compareModal) {
        closeCompareModal();
    }
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !els.compareModal.hidden) {
        closeCompareModal();
    }
});

bootstrap();
