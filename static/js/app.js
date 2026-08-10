const refreshSeconds = Number(document.body.dataset.refresh || 15);
const apiUrl = document.body.dataset.apiUrl || "/api/status";

function setBar(id, value) {
    const el = document.getElementById(id);
    el.style.width = `${Math.max(0, Math.min(100, value || 0))}%`;
}

function statusText(service) {
    if (!service.online) return "OFFLINE";
    const container = service.container_state;
    if (container && container.status && container.status !== "running") return "ATENÇÃO";
    return "ONLINE";
}

function renderServices(services) {
    const grid = document.getElementById("services-grid");
    grid.innerHTML = "";

    for (const service of services) {
        const state = statusText(service);
        const online = state === "ONLINE";
        const container = service.container_state;
        const isPing = service.type === "ping";
        const monitorLabel = isPing
            ? `PING • ${service.host}`
            : container
                ? `${container.status}${container.health ? ` • ${container.health}` : ""}`
                : "Monitor HTTP";

        const card = document.createElement(service.url ? "a" : "article");
        card.className = "service-card";
        if (service.url) {
            card.href = service.url;
            card.target = "_blank";
            card.rel = "noopener";
        }
        card.innerHTML = `
            <div class="service-header">
                <span class="service-name">${service.name}</span>
                <span class="badge ${online ? "online" : "offline"}">${state}</span>
            </div>
            <p class="service-description">${service.description}</p>
            <div class="service-footer">
                <span>${service.response_ms ?? "--"} ms</span>
                <span>${monitorLabel}</span>
            </div>
        `;
        grid.appendChild(card);
    }

    const allOnline = services.length > 0 && services.every(item => statusText(item) === "ONLINE");
    const dot = document.getElementById("overall-dot");
    dot.className = `status-dot ${allOnline ? "online" : "offline"}`;
    document.getElementById("overall-text").textContent = allOnline
        ? "Todos online"
        : "Atenção necessária";
}

async function updateDashboard() {
    try {
        const response = await fetch(apiUrl, { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        const cpu = data.server.cpu_percent ?? 0;
        const memory = data.server.memory.percent ?? 0;
        const disk = data.server.disk.percent ?? 0;

        document.getElementById("cpu-value").textContent = `${cpu}%`;
        document.getElementById("memory-value").textContent = `${memory}%`;
        document.getElementById("disk-value").textContent = `${disk}%`;
        document.getElementById("memory-detail").textContent =
            `${data.server.memory.used_gb ?? "--"} de ${data.server.memory.total_gb ?? "--"} GB`;
        document.getElementById("disk-detail").textContent =
            `${data.server.disk.used_gb ?? "--"} de ${data.server.disk.total_gb ?? "--"} GB`;
        document.getElementById("uptime-value").textContent = data.server.uptime;
        document.getElementById("container-detail").textContent =
            `Contêineres: ${data.server.containers_running}/${data.server.containers_total}`;

        setBar("cpu-bar", cpu);
        setBar("memory-bar", memory);
        setBar("disk-bar", disk);

        renderServices(data.services);
        document.getElementById("last-update").textContent =
            `Atualizado às ${new Date().toLocaleTimeString("pt-BR")}`;
    } catch (error) {
        document.getElementById("overall-dot").className = "status-dot offline";
        document.getElementById("overall-text").textContent = "Falha no painel";
        document.getElementById("last-update").textContent = error.message;
    }
}

updateDashboard();
setInterval(updateDashboard, refreshSeconds * 1000);
