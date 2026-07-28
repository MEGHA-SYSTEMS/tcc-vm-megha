const modal = document.getElementById("modal-localizacao");

document.getElementById("permitir").onclick = () => {

    navigator.geolocation.getCurrentPosition(
        (position)=>{

            console.log(position.coords.latitude);
            console.log(position.coords.longitude);

            modal.style.display = "none";

        },

        (erro)=>{

            alert("Não foi possível acessar sua localização.");

        }
    );

}

document.getElementById("negar").onclick = ()=>{

    modal.style.display = "none";

}
