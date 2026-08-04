navigator.geolocation.getCurrentPosition(
    sucesso,
    erro,
    {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0
    }
);

function sucesso(position) {
    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;

    console.log(latitude, longitude);
}

function erro(error) {
    console.log(error.message);
}

const map = L.map('map', {
    zoomControl: false,
    attributionControl: false
}).setView([-21.6033, -48.3658], 15);


L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);

const farmacias = [

    {
        nome: "Drogasil",
        lat: -21.6030,
        lon: -48.3650,
       
    },

    {
        nome: "Droga Raia",
        lat: -21.6020,
        lon: -48.3665,
      
    },

    {
        nome: "Farmácia São Paulo",
        lat: -21.6042,
        lon: -48.3641,
       
    }

];


if (navigator.geolocation) {

    navigator.geolocation.getCurrentPosition(function (position) {

        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        map.setView([latitude, longitude], 16);

        L.marker([latitude, longitude])
            .addTo(map)
            .bindPopup("local atual")
            .openPopup();

    }, function () {

        alert("Não foi possível obter sua localização.");

    });

} else {

    alert("Seu navegador não suporta Geolocalização.");

}

document.getElementById("buscar").addEventListener("click", buscarEndereco);

async function buscarEndereco() {

    const bairro = document.getElementById("bairro").value;
    const rua = document.getElementById("rua").value;
    const numero = document.getElementById("numero").value;

    const endereco =
        `${rua} ${numero}, ${bairro}, Matão, SP`;

    const resposta = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(endereco)}`
    );

    const dados = await resposta.json();

    if (dados.length == 0) {

        alert("Endereço não encontrado.");

        return;

    }

    const lat = parseFloat(dados[0].lat);
    const lon = parseFloat(dados[0].lon);

    map.setView([lat, lon],17);

    L.marker([lat, lon])
    .addTo(map)
    .bindPopup("Endereço pesquisado")
    .openPopup();
    
    mostrarFarmacias(lat, lon);
}

async function mostrarFarmacias(lat, lon){

    const query = `
    [out:json];
    (
      node["amenity"="pharmacy"](around:2000,${lat},${lon});
      way["amenity"="pharmacy"](around:2000,${lat},${lon});
      relation["amenity"="pharmacy"](around:2000,${lat},${lon});
    );
    out center;
    `;

    const resposta = await fetch(
        "https://overpass-api.de/api/interpreter",
        {
            method:"POST",
            body:query
        }
    );

    const dados = await resposta.json();

    dados.elements.forEach(farmacia => {

        const latitude = farmacia.lat || farmacia.center.lat;
        const longitude = farmacia.lon || farmacia.center.lon;

        const nome = farmacia.tags.name || "Farmácia";

        L.marker([latitude, longitude])

            .addTo(map)

            .bindPopup(`<b>${nome}</b>`);

    });

}