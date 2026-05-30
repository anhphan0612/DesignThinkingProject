function csrfToken() {
    return document.querySelector("meta[name='csrf-token']").content;
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

const contactButton = document.querySelector("#contactButton");
const contactResult = document.querySelector("#contactResult");

if (contactButton) {
    contactButton.addEventListener("click", async () => {
        try {
            const roomId = contactButton.dataset.roomId;
            const data = await postJson(`/api/rooms/${roomId}/contact/`);
            contactResult.hidden = false;
            contactResult.textContent = `${data.landlord_name}: ${data.phone || "Chua co so dien thoai"}`;
        } catch (error) {
            contactResult.hidden = false;
            contactResult.textContent = "Khong lay duoc thong tin lien he.";
        }
    });
}

