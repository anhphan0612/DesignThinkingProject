function csrfToken() {
    return document.querySelector("meta[name='csrf-token']").content;
}

function isAuthenticated() {
    return document.querySelector("meta[name='is-authenticated']").content === "true";
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

async function requestJson(path, method = "POST", body = {}) {
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

const favoriteButton = document.querySelector("#favoriteButton");
const contactButton = document.querySelector("#contactButton");
const contactResult = document.querySelector("#contactResult");

if (favoriteButton) {
    favoriteButton.addEventListener("click", async () => {
        const roomId = favoriteButton.dataset.roomId;
        if (!isAuthenticated()) {
            window.location.href = `/auth/login/?next=/rooms/${roomId}/`;
            return;
        }
        const isFavorited = favoriteButton.dataset.favorited === "true";
        favoriteButton.disabled = true;
        try {
            if (isFavorited) {
                await requestJson(`/api/rooms/${roomId}/unfavorite/`, "DELETE");
                favoriteButton.dataset.favorited = "false";
                favoriteButton.classList.remove("active");
                favoriteButton.textContent = "Lưu phòng yêu thích";
            } else {
                await requestJson(`/api/rooms/${roomId}/favorite/`, "POST");
                favoriteButton.dataset.favorited = "true";
                favoriteButton.classList.add("active");
                favoriteButton.textContent = "Đã lưu phòng";
            }
        } catch (error) {
            contactResult.hidden = false;
            contactResult.textContent = "Không cập nhật được phòng yêu thích. Hãy thử lại.";
        } finally {
            favoriteButton.disabled = false;
        }
    });
}

if (contactButton) {
    contactButton.addEventListener("click", async () => {
        contactButton.disabled = true;
        const originalText = contactButton.textContent;
        contactButton.textContent = "Đang lấy thông tin...";
        try {
            const roomId = contactButton.dataset.roomId;
            const data = await postJson(`/api/rooms/${roomId}/contact/`);
            contactResult.hidden = false;
            contactResult.textContent = `${data.landlord_name}: ${data.phone || "Chưa có số điện thoại"}`;
        } catch (error) {
            contactResult.hidden = false;
            contactResult.textContent = "Không lấy được thông tin liên hệ.";
        } finally {
            contactButton.disabled = false;
            contactButton.textContent = originalText;
        }
    });
}

