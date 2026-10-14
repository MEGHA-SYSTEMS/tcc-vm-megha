(function () {
    "use strict";

    var CHAVE = "poupemais_a11y";
    var NIVEIS = [100, 115, 130, 150];

    var raiz = document.documentElement;
    var toggle = document.getElementById("a11y-toggle");
    var painel = document.getElementById("a11y-painel");
    var rotuloNivel = document.getElementById("a11y-nivel");
    var widget = document.getElementById("a11y-widget");

    if (!toggle || !painel) return;

    var btnDiminuir = painel.querySelector('[data-acao="diminuir"]');
    var btnAumentar = painel.querySelector('[data-acao="aumentar"]');
    var btnContraste = painel.querySelector('[data-acao="contraste"]');
    var btnLinks = painel.querySelector('[data-acao="links"]');
    var btnRestaurar = painel.querySelector('[data-acao="restaurar"]');

    var estado = { nivel: 0, contraste: false, links: false, velocidade: 0 };


    /* ---------- salvar / carregar ---------- */

    function carregar() {
        try {
            var salvo = JSON.parse(localStorage.getItem(CHAVE));
            if (salvo) {
                var n = parseInt(salvo.nivel, 10) || 0;
                estado.nivel = Math.min(Math.max(n, 0), NIVEIS.length - 1);
                estado.contraste = !!salvo.contraste;
                estado.links = !!salvo.links;
                var v = parseInt(salvo.velocidade, 10) || 0;
                estado.velocidade = Math.min(Math.max(v, 0), 2);
            }
        } catch (e) {}
    }

    function salvar() {
        try {
            localStorage.setItem(CHAVE, JSON.stringify(estado));
        } catch (e) {}
    }


    /* ---------- aplicar o estado na página ---------- */

    function aplicar() {
        var fator = NIVEIS[estado.nivel] / 100;

        raiz.style.setProperty("--a11y-zoom", fator);
        raiz.classList.toggle("a11y-zoom-ativo", estado.nivel > 0);
        raiz.classList.toggle("a11y-contraste", estado.contraste);
        raiz.classList.toggle("a11y-links", estado.links);

        rotuloNivel.textContent = NIVEIS[estado.nivel] + "%";
        btnDiminuir.disabled = estado.nivel === 0;
        btnAumentar.disabled = estado.nivel === NIVEIS.length - 1;

        btnContraste.setAttribute("aria-pressed", String(estado.contraste));
        btnLinks.setAttribute("aria-pressed", String(estado.links));

        atualizarVelocidade();
    }


    /* ---------- ações ---------- */

    btnAumentar.addEventListener("click", function () {
        if (estado.nivel < NIVEIS.length - 1) {
            estado.nivel++;
            salvar();
            aplicar();
        }
    });

    btnDiminuir.addEventListener("click", function () {
        if (estado.nivel > 0) {
            estado.nivel--;
            salvar();
            aplicar();
        }
    });

    btnContraste.addEventListener("click", function () {
        estado.contraste = !estado.contraste;
        salvar();
        aplicar();
    });

    btnLinks.addEventListener("click", function () {
        estado.links = !estado.links;
        salvar();
        aplicar();
    });

    btnRestaurar.addEventListener("click", function () {
        pararLeitura();
        estado = { nivel: 0, contraste: false, links: false, velocidade: 0 };
        salvar();
        aplicar();
    });


    /* ---------- abrir / fechar painel ---------- */

    function abrirPainel() {
        painel.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        toggle.setAttribute("aria-label", "Fechar opções de acessibilidade");
    }

    function fecharPainel() {
        painel.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Abrir opções de acessibilidade");
    }

    toggle.addEventListener("click", function () {
        if (painel.hidden) {
            abrirPainel();
        } else {
            fecharPainel();
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !painel.hidden) {
            fecharPainel();
            toggle.focus();
        }
    });

    document.addEventListener("click", function (e) {
        if (!painel.hidden && !widget.contains(e.target)) {
            fecharPainel();
        }
    });


    /* ---------- leitura em voz alta ---------- */

    var blocoVoz = document.getElementById("a11y-voz");
    var statusVoz = document.getElementById("a11y-voz-status");
    var btnLerPagina = painel.querySelector('[data-acao="ler-pagina"]');
    var btnLerSelecao = painel.querySelector('[data-acao="ler-selecao"]');
    var btnParar = painel.querySelector('[data-acao="parar"]');
    var btnVelocidade = painel.querySelector('[data-acao="velocidade"]');

    var sintese = window.speechSynthesis;
    var suportaVoz = !!sintese && "SpeechSynthesisUtterance" in window;

    var VELOCIDADES = [
        { rotulo: "Normal", valor: 1 },
        { rotulo: "Lenta", valor: 0.8 },
        { rotulo: "Rápida", valor: 1.25 }
    ];

    var sessao = 0;
    var falando = false;
    var ultimaSelecao = "";

    function atualizarVelocidade() {
        if (btnVelocidade) {
            btnVelocidade.textContent = "Velocidade: " + VELOCIDADES[estado.velocidade].rotulo;
        }
    }

    function mensagemVoz(texto) {
        if (statusVoz) statusVoz.textContent = texto || "";
    }

    function atualizarBotoesVoz() {
        btnParar.disabled = !falando;
        btnLerPagina.disabled = falando;
        btnLerSelecao.disabled = falando;
    }

    function escolherVoz() {
        var vozes = sintese.getVoices() || [];
        var i;
        for (i = 0; i < vozes.length; i++) {
            if (vozes[i].lang && vozes[i].lang.toLowerCase() === "pt-br") return vozes[i];
        }
        for (i = 0; i < vozes.length; i++) {
            if (vozes[i].lang && vozes[i].lang.toLowerCase().indexOf("pt") === 0) return vozes[i];
        }
        return null;
    }

    /* Descobre o bloco (elemento não-inline) de um texto, para saber quando pausar */
    function blocoDe(el) {
        while (el && el !== document.body) {
            var display = window.getComputedStyle(el).display;
            if (display !== "inline" && display !== "inline-block" && display !== "contents") {
                return el;
            }
            el = el.parentElement;
        }
        return document.body;
    }

    /* Junta só o texto visível da página, ignorando o painel e o VLibras */
    function textoDaPagina() {
        var raiz = document.querySelector("main") || document.body;
        var texto = "";
        var blocoAnterior = null;

        var caminhada = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, {
            acceptNode: function (no) {
                var el = no.parentElement;
                if (!el) return NodeFilter.FILTER_REJECT;
                if (!no.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
                if (el.closest("script, style, noscript, [vw], .a11y-widget, [aria-hidden='true']")) {
                    return NodeFilter.FILTER_REJECT;
                }
                if (!el.getClientRects().length) return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            }
        });

        while (caminhada.nextNode()) {
            var no = caminhada.currentNode;
            var bloco = blocoDe(no.parentElement);
            var parte = no.nodeValue.replace(/\s+/g, " ").trim();

            if (texto === "") {
                texto = parte;
            } else if (bloco !== blocoAnterior) {
                texto += "\n" + parte;
            } else {
                texto += " " + parte;
            }
            blocoAnterior = bloco;
        }

        return texto;
    }

    /* Divide em pedaços curtos: evita que o Chrome corte falas longas */
    function dividir(texto) {
        var partes = [];

        texto.split(/\n+/).forEach(function (linha) {
            linha = linha.trim();
            if (!linha) return;

            var frases = linha.match(/[^.!?]+[.!?]*/g) || [linha];

            frases.forEach(function (frase) {
                frase = frase.trim();
                while (frase.length > 180) {
                    var corte = frase.lastIndexOf(" ", 180);
                    if (corte < 60) corte = 180;
                    partes.push(frase.slice(0, corte).trim());
                    frase = frase.slice(corte).trim();
                }
                if (frase) partes.push(frase);
            });
        });

        return partes;
    }

    function pararLeitura() {
        if (!suportaVoz) return;
        sessao++;
        falando = false;
        sintese.cancel();
        atualizarBotoesVoz();
    }

    function falar(texto) {
        if (!suportaVoz) return;

        pararLeitura();

        var partes = dividir(texto);
        if (partes.length === 0) {
            mensagemVoz("Não encontrei texto para ler.");
            return;
        }

        var minhaSessao = ++sessao;
        var indice = 0;

        falando = true;
        atualizarBotoesVoz();
        mensagemVoz("Lendo...");

        function proxima() {
            if (minhaSessao !== sessao) return;

            if (indice >= partes.length) {
                falando = false;
                atualizarBotoesVoz();
                mensagemVoz("Leitura concluída.");
                return;
            }

            var fala = new SpeechSynthesisUtterance(partes[indice++]);
            fala.lang = "pt-BR";
            fala.rate = VELOCIDADES[estado.velocidade].valor;

            var voz = escolherVoz();
            if (voz) fala.voice = voz;

            fala.onend = proxima;
            fala.onerror = function () {
                if (minhaSessao !== sessao) return;
                falando = false;
                atualizarBotoesVoz();
                mensagemVoz("A leitura foi interrompida.");
            };

            sintese.speak(fala);
        }

        proxima();
    }

    if (!suportaVoz) {
        if (blocoVoz) blocoVoz.hidden = true;
    } else {
        /* Guarda a última seleção feita fora do painel
           (clicar no botão pode limpar a seleção em alguns navegadores) */
        document.addEventListener("selectionchange", function () {
            var selecao = window.getSelection();
            if (!selecao || selecao.isCollapsed) return;

            var no = selecao.anchorNode;
            var el = no && (no.nodeType === 1 ? no : no.parentElement);
            if (el && el.closest(".a11y-widget")) return;

            var texto = selecao.toString().trim();
            if (texto) ultimaSelecao = texto;
        });

        btnLerPagina.addEventListener("click", function () {
            falar(textoDaPagina());
        });

        btnLerSelecao.addEventListener("click", function () {
            if (!ultimaSelecao) {
                mensagemVoz("Selecione um texto na página primeiro.");
                return;
            }
            falar(ultimaSelecao);
        });

        btnParar.addEventListener("click", function () {
            pararLeitura();
            mensagemVoz("Leitura interrompida.");
        });

        btnVelocidade.addEventListener("click", function () {
            estado.velocidade = (estado.velocidade + 1) % VELOCIDADES.length;
            salvar();
            atualizarVelocidade();
        });

        /* Não deixa a fala continuar ao trocar de página */
        window.addEventListener("pagehide", pararLeitura);
        window.addEventListener("beforeunload", pararLeitura);

        /* Algumas vozes só carregam depois do primeiro evento */
        if (typeof sintese.onvoiceschanged !== "undefined") {
            sintese.onvoiceschanged = function () {};
        }

        atualizarBotoesVoz();
    }


    /* ---------- início ---------- */

    carregar();
    aplicar();
})();