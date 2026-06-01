const state = {
    amenities: [],
    universities: [],
    rooms: [],
    selectedRoomId: null,
    isAuthenticated: document.querySelector("meta[name='is-authenticated']").content === "true",
};

const els = {
    query: document.querySelector("#query"),
    university: document.querySelector("#university"),
    distance: document.querySelector("#distance"),
    minPrice: document.querySelector("#minPrice"),
    maxPrice: document.querySelector("#maxPrice"),
    minArea: document.querySelector("#minArea"),
    amenities: document.querySelector("#amenities"),
    apply: document.querySelector("#applyFilters"),
    reset: document.querySelector("#resetFilters"),
    roomList: document.querySelector("#roomList"),
    resultCount: document.querySelector("#resultCount"),
    status: document.querySelector("#status"),
    detailEmpty: document.querySelector("#detailEmpty"),
    roomDetail: document.querySelector("#roomDetail"),
    detailTitle: document.querySelector("#detailTitle"),
    detailAddress: document.querySelector("#detailAddress"),
    detailPrice: document.querySelector("#detailPrice"),
    detailArea: document.querySelector("#detailArea"),
    detailOccupants: document.querySelector("#detailOccupants"),
    detailDistance: document.querySelector("#detailDistance"),
    detailAmenities: document.querySelector("#detailAmenities"),
    mapFrame: document.querySelector("#mapFrame"),
    favoriteButton: document.querySelector("#favoriteButton"),
    contactButton: document.querySelector("#contactButton"),
    contactResult: document.querySelector("#contactResult"),
    detailPageLink: document.querySelector("#detailPageLink"),
    recommendationBox: document.querySelector("#recommendationBox"),
    recommendationList: document.querySelector("#recommendationList"),
    recommendationCount: document.querySelector("#recommendationCount"),
    heroRoomCount: document.querySelector("#heroRoomCount"),
};

function csrfToken() {
    return document.querySelector("meta[name='csrf-token']").content;
}

function formatCurrency(value) {
    return new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND",
        maximumFractionDigits: 0,
    }).format(Number(value));
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

async function postJson(path, body = {}) {
    const response = await fetch(path, {
        method: "POST",
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
    els.amenities.innerHTML = "";
    state.amenities.forEach((amenity) => {
        const label = document.createElement("label");
        label.className = "check";
        label.innerHTML = `<input type="checkbox" name="amenity" value="${amenity.id}"><span>${amenity.name}</span>`;
        els.amenities.append(label);
    });
}

function renderRooms() {
    els.roomList.innerHTML = "";
    els.resultCount.textContent = `${state.rooms.length} phòng`;
    if (els.heroRoomCount) {
        els.heroRoomCount.textContent = state.rooms.length;
    }
    if (!state.rooms.length) {
        els.roomList.innerHTML = '<div class="empty-state"><p class="eyebrow">Không có kết quả</p><h2>Thử giảm điều kiện lọc</h2><p class="muted">Bộ dữ liệu hiện tại vẫn là dữ liệu demo nên số lượng phòng chưa nhiều.</p></div>';
        els.detailEmpty.hidden = false;
        els.roomDetail.hidden = true;
        return;
    }
    state.rooms.forEach((room) => els.roomList.append(roomCard(room)));
    selectRoom(state.rooms[0].id);
}

function renderRecommendations(items) {
    if (!items.length) {
        els.recommendationBox.hidden = true;
        return;
    }
    els.recommendationBox.hidden = false;
    els.recommendationCount.textContent = `${items.length} phòng`;
    els.recommendationList.innerHTML = "";
    items.slice(0, 3).forEach((item) => {
        const element = document.createElement("div");
        element.className = "recommendation-item";
        element.innerHTML = `
            <div>
                <strong>${item.room.title}</strong>
                <span>${item.score_detail.reasons.join(" · ")}</span>
            </div>
            <span>${Math.round(item.score * 100)}%</span>
        `;
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
    const amenities = room.amenities.slice(0, 4).map((amenity) => `<span class="tag">${amenity.name}</span>`).join("");
    const distance = room.distance_km ? `Cách trường ${room.distance_km} km` : "Chưa lọc theo trường";
    const cover = room.images.find((image) => image.is_cover) || room.images[0];
    const thumbnail = cover
        ? `<img src="${cover.image}" alt="${cover.caption || room.title}">`
        : "<span>ẢNH</span>";
    card.innerHTML = `
        <div class="thumb">${thumbnail}</div>
        <div>
            <h3>${room.title}</h3>
            <div class="price">${formatCurrency(room.price)} / tháng</div>
            <div class="meta"><span>${room.area} m²</span><span>${room.max_occupants} người</span><span>${distance}</span></div>
            <p class="muted">${room.address}</p>
            <div class="tags">${amenities}</div>
            <span class="card-link">Xem chi tiết</span>
        </div>
    `;
    card.addEventListener("click", () => {
        window.location.href = `/rooms/${room.id}/`;
    });
    card.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            window.location.href = `/rooms/${room.id}/`;
        }
    });
    return card;
}

function selectRoom(roomId) {
    const room = state.rooms.find((item) => item.id === roomId);
    if (!room) {
        return;
    }
    state.selectedRoomId = roomId;
    document.querySelectorAll(".room-card").forEach((card) => {
        card.classList.toggle("active", Number(card.dataset.roomId) === roomId);
    });
    els.detailEmpty.hidden = true;
    els.roomDetail.hidden = false;
    els.detailTitle.textContent = room.title;
    els.detailAddress.textContent = `${room.address} - ${room.ward_name}, ${room.district_name}`;
    els.detailPrice.textContent = `${formatCurrency(room.price)} / tháng`;
    els.detailArea.textContent = `${room.area} m²`;
    els.detailOccupants.textContent = `${room.max_occupants} người`;
    els.detailDistance.textContent = room.distance_km ? `${room.distance_km} km` : "Chưa lọc theo trường";
    els.detailAmenities.innerHTML = room.amenities.map((amenity) => `<span class="tag">${amenity.name}</span>`).join("");
    els.favoriteButton.disabled = !state.isAuthenticated;
    els.favoriteButton.textContent = state.isAuthenticated ? "Lưu yêu thích" : "Đăng nhập để lưu";
    els.contactResult.hidden = true;
    els.detailPageLink.href = `/rooms/${room.id}/`;

    const lat = Number(room.latitude);
    const lng = Number(room.longitude);
    const delta = 0.006;
    els.mapFrame.src = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - delta}%2C${lat - delta}%2C${lng + delta}%2C${lat + delta}&layer=mapnik&marker=${lat}%2C${lng}`;
    postJson("/api/events/", { type: "view_room", room: room.id, metadata: { source: "frontend" } }).catch(() => {});
}

async function loadRooms() {
    showStatus("Đang tải phòng phù hợp...");
    try {
        const data = await fetchJson("/api/rooms/", currentFilters());
        state.rooms = data.results || [];
        showStatus("");
        renderRooms();
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
        if (state.isAuthenticated) {
            const recommendations = await fetchJson("/api/recommendations/");
            renderRecommendations(recommendations);
        }
    } catch (error) {
        showStatus("Không tải được dữ liệu tham chiếu. Hãy chạy migrate và seed demo data.", true);
        console.error(error);
    }
}

els.apply.addEventListener("click", loadRooms);
els.reset.addEventListener("click", () => {
    els.query.value = "";
    els.university.value = "";
    els.distance.value = "2";
    els.minPrice.value = "";
    els.maxPrice.value = "";
    els.minArea.value = "";
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

els.favoriteButton.addEventListener("click", async () => {
    if (!state.selectedRoomId || !state.isAuthenticated) {
        window.location.href = "/auth/login/";
        return;
    }
    try {
        const data = await postJson(`/api/rooms/${state.selectedRoomId}/favorite/`);
        els.favoriteButton.textContent = data.created ? "Đã lưu yêu thích" : "Đã nằm trong yêu thích";
    } catch (error) {
        showStatus("Không lưu được phòng yêu thích. Hãy thử đăng nhập lại.", true);
    }
});

els.contactButton.addEventListener("click", async () => {
    if (!state.selectedRoomId) {
        return;
    }
    try {
        const data = await postJson(`/api/rooms/${state.selectedRoomId}/contact/`);
        els.contactResult.hidden = false;
        els.contactResult.textContent = `${data.landlord_name}: ${data.phone || "Chưa có số điện thoại"}`;
    } catch (error) {
        showStatus("Không lấy được thông tin liên hệ.", true);
    }
});

bootstrap();
