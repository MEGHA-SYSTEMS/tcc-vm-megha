const CIDADE_PADRAO = "Matão, SP";
const CHAVE_LOCAL = "poupemais_localizacao";
const VALIDADE_MS = 30 * 60 * 1000; // 30 minutos

function salvarLocalizacao(lat, lng) {
    try {
        localStorage.setItem(CHAVE_LOCAL, JSON.stringify({ lat, lng, quando: Date.now() }));
    } catch (e) { /* navegador bloqueou o armazenamento, segue sem salvar */ }
}

function localizacaoSalva() {
    try {
        const s = JSON.parse(localStorage.getItem(CHAVE_LOCAL));
        if (s && Date.now() - s.quando < VALIDADE_MS) return s;
    } catch (e) {}
    return null;
}

const map = L.map('map', {
    zoomControl: false,
    attributionControl: false
}).setView([-21.6033, -48.3658], 14);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);

let farmacias = [];          // vêm do Firestore via /api/farmacias
let origem = null;           // {lat, lng} de quem está procurando
let marcadorOrigem = null;
const marcadores = {};       // id da farmácia -> marcador

const elLista = document.getElementById("lista-farmacias");
const elAviso = document.getElementById("aviso-mapa");


/* ---------- utilidades ---------- */

function escapar(texto) {
    const d = document.createElement("div");
    d.textContent = texto ?? "";
    return d.innerHTML;
}

function distanciaKm(a, b) {
    const R = 6371;
    const rad = x => x * Math.PI / 180;
    const dLat = rad(b.lat - a.lat);
    const dLng = rad(b.lng - a.lng);
    const h = Math.sin(dLat / 2) ** 2 +
        Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
}

function textoDistancia(km) {
    return km < 1
        ? `${Math.round(km * 1000)} m`
        : `${km.toFixed(1).replace(".", ",")} km`;
}

function avisar(texto) {
    elAviso.textContent = texto || "";
}


/* ---------- farmácias cadastradas ---------- */

function popupHtml(f) {
    const dist = f.distancia != null
        ? `<br><small>${textoDistancia(f.distancia)} de você</small>` : "";

    return `
        <b>${escapar(f.nome)}</b><br>
        <small>${escapar(f.endereco)}</small>${dist}<br>
        <a href="/farmacia/${encodeURIComponent(f.id)}">Ver farmácia</a> ·
        <a target="_blank" rel="noopener"
           href="https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lng}">Como chegar</a>
    `;
}

function desenharMarcadores() {
    farmacias.forEach(f => {
        const m = L.marker([f.lat, f.lng]).addTo(map).bindPopup(popupHtml(f));
        marcadores[f.id] = m;
    });
}

function renderizarLista() {
    if (!farmacias.length) {
        elLista.innerHTML = "<p>Nenhuma farmácia cadastrada com localização ainda.</p>";
        return;
    }

    const ordenadas = [...farmacias];
    if (origem) ordenadas.sort((a, b) => a.distancia - b.distancia);

    elLista.innerHTML = "";
    ordenadas.forEach(f => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "item-farmacia";
        btn.innerHTML = `
            <strong>${escapar(f.nome)}</strong>
            <small>${escapar(f.endereco)}${f.distancia != null ? " · " + textoDistancia(f.distancia) : ""}</small>
        `;
        btn.addEventListener("click", () => focarFarmacia(f.id));
        elLista.appendChild(btn);
    });
}

function focarFarmacia(id) {
    const f = farmacias.find(x => x.id === id);
    if (!f) return;
    map.setView([f.lat, f.lng], 17);
    marcadores[id].openPopup();
}

async function carregarFarmacias() {
    try {
        const resp = await fetch("/api/farmacias");
        farmacias = await resp.json();
    } catch (e) {
        farmacias = [];
        avisar("Não foi possível carregar as farmácias agora.");
    }

    desenharMarcadores();
    renderizarLista();

    // veio da página da farmácia/produto: /localizacao?farmacia=ID
    const id = new URLSearchParams(window.location.search).get("farmacia");
    if (id) {
        focarFarmacia(id);
    } else if (farmacias.length) {
        map.fitBounds(farmacias.map(f => [f.lat, f.lng]), { padding: [40, 40], maxZoom: 16 });
    }

    // localização guardada pela página inicial (ou por um clique anterior)
    const salva = localizacaoSalva();
    if (salva) {
        // com ?farmacia=ID o foco continua na farmácia; só marca você no mapa
        definirOrigem(salva.lat, salva.lng, "Você está aqui", !id);
    }
}


/* ---------- origem (localização atual ou endereço) ---------- */

function definirOrigem(lat, lng, rotulo, enquadrar = true) {
    origem = { lat, lng };

    if (marcadorOrigem) map.removeLayer(marcadorOrigem);
    marcadorOrigem = L.marker([lat, lng]).addTo(map).bindPopup(rotulo);

    farmacias.forEach(f => {
        f.distancia = distanciaKm(origem, f);
        marcadores[f.id].setPopupContent(popupHtml(f));
    });

    renderizarLista();

    if (enquadrar) {
        // enquadra você + as 3 farmácias mais próximas
        const proximas = [...farmacias]
            .sort((a, b) => a.distancia - b.distancia)
            .slice(0, 3)
            .map(f => [f.lat, f.lng]);

        if (proximas.length) {
            map.fitBounds([[lat, lng], ...proximas], { padding: [40, 40], maxZoom: 16 });
        } else {
            map.setView([lat, lng], 16);
        }
        marcadorOrigem.openPopup();
    }
}

document.getElementById("usar-localizacao").addEventListener("click", () => {
    if (!navigator.geolocation) {
        avisar("Seu navegador não suporta geolocalização.");
        return;
    }

    avisar("Obtendo sua localização...");

    navigator.geolocation.getCurrentPosition(
        pos => {
            avisar("");
            salvarLocalizacao(pos.coords.latitude, pos.coords.longitude);
            definirOrigem(pos.coords.latitude, pos.coords.longitude, "Você está aqui");
        },
        err => {
            if (err.code === 1) {
                avisar("Permissão negada. Libere a localização no navegador ou digite seu endereço.");
            } else {
                avisar("Não foi possível obter sua localização. Tente digitar o endereço.");
            }
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
});

document.getElementById("buscar").addEventListener("click", async () => {
    const bairro = document.getElementById("bairro").value.trim();
    const rua = document.getElementById("rua").value.trim();
    const cep = document.getElementById("cep").value.trim();
    const numero = document.getElementById("numero").value.trim();

    if (!rua && !cep) {
        avisar("Digite pelo menos a rua ou o CEP.");
        return;
    }

    avisar("Procurando endereço...");

    const consulta = [`${rua} ${numero}`.trim(), bairro, cep, CIDADE_PADRAO]
        .filter(Boolean).join(", ");

    try {
        const resp = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(consulta)}`
        );
        const dados = await resp.json();

        if (!dados.length) {
            avisar("Endereço não encontrado.");
            return;
        }

        avisar("");
        definirOrigem(parseFloat(dados[0].lat), parseFloat(dados[0].lon), "Endereço pesquisado");
    } catch (e) {
        avisar("Erro ao buscar o endereço. Tente de novo.");
    }
});

carregarFarmacias();