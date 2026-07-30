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


if (navigator.geolocation) {

    navigator.geolocation.getCurrentPosition(function (position) {

        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        map.setView([latitude, longitude], 16);

        L.marker([latitude, longitude])
            .addTo(map)
            .bindPopup("Você está aqui.")
            .openPopup();

    }, function () {

        alert("Não foi possível obter sua localização.");

    });

} else {

    alert("Seu navegador não suporta Geolocalização.");

}

document.getElementById("buscar").addEventListener("click", buscarEndereco);

async function buscarEndereco(){

    const bairro = document.getElementById("bairro").value;
    const rua = document.getElementById("rua").value;
    const numero = document.getElementById("numero").value;

    const endereco =
        `${rua} ${numero}, ${bairro}, Matão, SP`;

    const resposta = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(endereco)}`
    );

    const dados = await resposta.json();

    if(dados.length == 0){

        alert("Endereço não encontrado.");

        return;

    }

    const lat = dados[0].lat;
    const lon = dados[0].lon;

    map.setView([lat, lon],17);

    L.marker([lat,lon])
        .addTo(map)
        .bindPopup(endereco)
        .openPopup();

}