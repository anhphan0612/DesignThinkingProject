const state = {
    amenities: [],
    universities: [],
    rooms: [],
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
    recommendationBox: document.querySelector("#recommendationBox"),
    recommendationList: document.querySelector("#recommendationList"),
    recommendationCount: document.querySelector("#recommendationCount"),
    heroRoomCount: document.querySelector("#heroRoomCount"),
};

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

function renderRooms() {
    els.roomList.replaceChildren();
    els.resultCount.textContent = `${state.rooms.length} phòng`;
    if (els.heroRoomCount) {
        els.heroRoomCount.textContent = state.rooms.length;
    }
    if (!state.rooms.length) {
        renderEmptyRooms();
        return;
    }
    state.rooms.forEach((room) => els.roomList.append(roomCard(room)));
}

function renderRecommendations(items) {
    if (!items.length) {
        els.recommendationBox.hidden = true;
        return;
    }
    els.recommendationBox.hidden = false;
    els.recommendationCount.textContent = `${items.length} phòng`;
    els.recommendationList.replaceChildren();
    items.slice(0, 3).forEach((item) => {
        const element = document.createElement("div");
        element.className = "recommendation-item";
        const copy = document.createElement("div");
        copy.append(
            textElement("strong", item.room.title),
            textElement("span", item.score_detail.reasons.join(" · ")),
        );
        element.append(copy, textElement("span", `${Math.round(item.score * 100)}%`));
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
    const distance = room.distance_km ? `Cách trường ${room.distance_km} km` : "Chưa lọc theo trường";
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.append(
        textElement("span", `${room.area} m²`),
        textElement("span", `${room.max_occupants} người`),
        textElement("span", distance),
    );

    const tags = document.createElement("div");
    tags.className = "tags";
    room.amenities.slice(0, 4).forEach((amenity) => tags.append(tagElement(amenity.name)));

    const detailLink = textElement("span", "Xem chi tiết", "card-link");
    content.append(
        textElement("h3", room.title),
        textElement("div", `${formatCurrency(room.price)} / tháng`, "price"),
        meta,
        textElement("p", room.address, "muted"),
        tags,
        detailLink,
    );
    card.append(thumb, content);

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
        showStatus("Không tải được dữ liệu cần thiết. Hãy thử tải lại trang sau ít phút.", true);
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

bootstrap();
