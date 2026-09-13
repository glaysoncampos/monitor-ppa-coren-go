"use strict";

let iniciativasCarregadas = [];

document.addEventListener("DOMContentLoaded", iniciarPainel);

async function iniciarPainel() {
    configurarImpressao();

    try {
        const resposta = await fetch("data/iniciativas.json", {
            cache: "no-store"
        });

        if (!resposta.ok) {
            throw new Error(
                `Não foi possível carregar os dados. Código ${resposta.status}.`
            );
        }

        const dados = await resposta.json();

        if (!dados || !Array.isArray(dados.iniciativas)) {
            throw new Error("O arquivo JSON não possui a estrutura esperada.");
        }

        iniciativasCarregadas = dados.iniciativas;

        renderizarResumo(iniciativasCarregadas, dados.metadados);
        criarFiltros(iniciativasCarregadas);
        renderizarIniciativas(iniciativasCarregadas);
        renderizarMetodologia(iniciativasCarregadas);
        renderizarAuditoria(iniciativasCarregadas, dados.metadados);
    } catch (erro) {
        apresentarErro(erro.message);
    }
}

function configurarImpressao() {
    const botao = document.getElementById("botaoImprimir");

    if (botao) {
        botao.addEventListener("click", () => {
            window.print();
        });
    }
}

function renderizarResumo(iniciativas, metadados = {}) {
    const area = document.getElementById("resumoExecutivo");

    const concluidas = iniciativas.filter(
        item => normalizar(item.status) === "concluida"
    ).length;

    const emExecucao = iniciativas.filter(
        item => normalizar(item.status) === "em execucao"
    ).length;

    const iniciativaFinanceira = iniciativas.find(
        item => item.financeiro && Number(item.financeiro.dotacaoAtualizada) > 0
    );

    const iniciativaComCusto = iniciativas.find(
        item => item.custos && Number(item.custos.custoAbcMaoDeObra) > 0
    );

    const cartoes = [
        {
            titulo: "Iniciativas do piloto",
            valor: iniciativas.length,
            complemento: "Escopo restrito para validação"
        },
        {
            titulo: "Concluídas",
            valor: concluidas,
            complemento: "Execução física finalizada"
        },
        {
            titulo: "Em execução",
            valor: emExecucao,
            complemento: "Entrega ainda em andamento"
        },
        {
            titulo: "Última geração",
            valor: textoSeguro(metadados.dataGeracao || "Pendente"),
            complemento: "Atualização automática futura"
        }
    ];

    if (iniciativaFinanceira) {
        const financeiro = iniciativaFinanceira.financeiro;
        const identificacao = iniciativaFinanceira.id;

        cartoes.push(
            {
                titulo: `Dotação fictícia ${identificacao}`,
                valor: formatarMoeda(financeiro.dotacaoAtualizada),
                complemento: "Não representa dado oficial"
            },
            {
                titulo: `Empenhado fictício ${identificacao}`,
                valor: formatarMoeda(financeiro.valorEmpenhado),
                complemento: formatarPercentual(
                    financeiro.execucaoEmpenho
                )
            },
            {
                titulo: `Liquidado fictício ${identificacao}`,
                valor: formatarMoeda(financeiro.valorLiquidado),
                complemento: formatarPercentual(
                    financeiro.execucaoLiquidacao
                )
            },
            {
                titulo: `Pago fictício ${identificacao}`,
                valor: formatarMoeda(financeiro.valorPago),
                complemento: formatarPercentual(
                    financeiro.execucaoPagamento
                )
            }
        );
    }

    if (iniciativaComCusto) {
        cartoes.push({
            titulo: `Custo ABC ${iniciativaComCusto.id}`,
            valor: formatarMoeda(
                iniciativaComCusto.custos.custoAbcMaoDeObra
            ),
            complemento: "Custo de mão de obra no teste"
        });
    }

    area.innerHTML = cartoes.map(cartao => `
        <article class="indicador">
            <p class="indicadorTitulo">${textoSeguro(cartao.titulo)}</p>
            <p class="indicadorValor">${textoSeguro(cartao.valor)}</p>
            <small>${textoSeguro(cartao.complemento)}</small>
        </article>
    `).join("");
}

function criarFiltros(iniciativas) {
    const area = document.getElementById("filtros");

    const configuracoes = [
        {
            id: "filtroStatus",
            rotulo: "Situação",
            campo: "status"
        },
        {
            id: "filtroObjetivo",
            rotulo: "Objetivo estratégico",
            campo: "objetivoEstrategico"
        },
        {
            id: "filtroPrioridade",
            rotulo: "Prioridade",
            campo: "prioridade"
        },
        {
            id: "filtroTipo",
            rotulo: "Natureza do dado",
            campo: "tipoDado"
        }
    ];

    area.className = "filtros";

    area.innerHTML = configuracoes.map(configuracao => {
        const valores = obterValoresUnicos(
            iniciativas,
            configuracao.campo
        );

        return `
            <div class="campoFiltro">
                <label for="${configuracao.id}">
                    ${textoSeguro(configuracao.rotulo)}
                </label>

                <select
                    id="${configuracao.id}"
                    data-campo="${configuracao.campo}"
                >
                    <option value="">Todos</option>
                    ${valores.map(valor => `
                        <option value="${textoSeguro(valor)}">
                            ${textoSeguro(valor)}
                        </option>
                    `).join("")}
                </select>
            </div>
        `;
    }).join("");

    area.querySelectorAll("select").forEach(seletor => {
        seletor.addEventListener("change", aplicarFiltros);
    });
}

function aplicarFiltros() {
    const seletores = document.querySelectorAll(
        "#filtros select"
    );

    const filtradas = iniciativasCarregadas.filter(iniciativa => {
        return Array.from(seletores).every(seletor => {
            const valorEscolhido = seletor.value;
            const campo = seletor.dataset.campo;

            if (!valorEscolhido) {
                return true;
            }

            return String(iniciativa[campo]) === valorEscolhido;
        });
    });

    renderizarIniciativas(filtradas);
}

function renderizarIniciativas(iniciativas) {
    const area = document.getElementById("cartoesIniciativas");

    if (iniciativas.length === 0) {
        area.innerHTML = `
            <p>Nenhuma iniciativa corresponde aos filtros selecionados.</p>
        `;
        return;
    }

    area.innerHTML = iniciativas.map(iniciativa => {
        const execucao = limitarPercentual(
            iniciativa.execucaoFisica
        );

        const classeStatus = normalizar(iniciativa.status) === "concluida"
            ? "statusConcluida"
            : "statusExecucao";

        const classeTipo = normalizar(iniciativa.tipoDado) === "ficticio"
            ? "etiqueta etiquetaFicticio"
            : "etiqueta";

        return `
            <article class="cartaoIniciativa ${classeStatus}">
                <div>
                    <span class="${classeTipo}">
                        ${textoSeguro(iniciativa.tipoDado)}
                    </span>
                </div>

                <h3>${textoSeguro(iniciativa.iniciativa)}</h3>

                <p>
                    <strong>ID:</strong>
                    ${textoSeguro(iniciativa.id)}
                </p>

                <p>
                    <strong>Situação:</strong>
                    ${textoSeguro(iniciativa.status)}
                </p>

                <p>
                    <strong>Execução física:</strong>
                    ${formatarPercentual(execucao)}
                </p>

                <div
                    class="barraProgresso"
                    role="progressbar"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    aria-valuenow="${execucao}"
                    aria-label="Execução física da iniciativa"
                >
                    <span style="width: ${execucao}%"></span>
                </div>

                <details>
                    <summary>Ver detalhamento</summary>
                    ${montarDetalhamento(iniciativa)}
                </details>
            </article>
        `;
    }).join("");
}

function montarDetalhamento(iniciativa) {
    const financeiro = iniciativa.financeiro || {};
    const custos = iniciativa.custos || {};
    const evidencias = Array.isArray(iniciativa.evidencias)
        ? iniciativa.evidencias
        : [];

    return `
        <div>
            <p>
                <strong>Objetivo estratégico:</strong>
                ${textoSeguro(iniciativa.objetivoEstrategico)}
            </p>

            <p>
                <strong>Programa:</strong>
                ${textoSeguro(iniciativa.programa)}
            </p>

            <p>
                <strong>Prioridade:</strong>
                ${textoSeguro(iniciativa.prioridade)}
            </p>

            <p>
                <strong>Forma de execução:</strong>
                ${textoSeguro(iniciativa.formaExecucao)}
            </p>

            <p>
                <strong>Resultado entregue:</strong>
                ${textoSeguro(iniciativa.resultadoEntregue)}
            </p>

            <p>
                <strong>Unidade responsável:</strong>
                ${textoSeguro(iniciativa.responsavel)}
            </p>

            ${montarFinanceiro(financeiro)}
            ${montarCustos(custos)}
            ${montarEvidencias(evidencias)}
        </div>
    `;
}

function montarFinanceiro(financeiro) {
    if (!financeiro || financeiro.periodo === undefined) {
        return "";
    }

    return `
        <h4>Execução orçamentária e financeira</h4>

        <div class="tabelaResponsiva">
            <table>
                <tbody>
                    <tr>
                        <th>Período</th>
                        <td>${textoSeguro(financeiro.periodo)}</td>
                    </tr>
                    <tr>
                        <th>Dotação atualizada</th>
                        <td>${formatarMoeda(financeiro.dotacaoAtualizada)}</td>
                    </tr>
                    <tr>
                        <th>Contratado</th>
                        <td>${formatarMoeda(financeiro.valorContratado)}</td>
                    </tr>
                    <tr>
                        <th>Empenhado</th>
                        <td>${formatarMoeda(financeiro.valorEmpenhado)}</td>
                    </tr>
                    <tr>
                        <th>Liquidado</th>
                        <td>${formatarMoeda(financeiro.valorLiquidado)}</td>
                    </tr>
                    <tr>
                        <th>Pago</th>
                        <td>${formatarMoeda(financeiro.valorPago)}</td>
                    </tr>
                    <tr>
                        <th>Saldo orçamentário</th>
                        <td>${formatarMoeda(financeiro.saldoOrcamentario)}</td>
                    </tr>
                    <tr>
                        <th>Liquidado a pagar</th>
                        <td>${formatarMoeda(financeiro.liquidadoAPagar)}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    `;
}

function montarCustos(custos) {
    if (!custos || custos.custoAbcMaoDeObra === undefined) {
        return "";
    }

    return `
        <h4>Custo ABC simplificado</h4>

        <div class="memoriaCalculo">
            <p>
                <strong>Participantes:</strong>
                ${textoSeguro(custos.quantidadeParticipantes)}
            </p>

            <p>
                <strong>Total de horas:</strong>
                ${textoSeguro(custos.totalHoras)}
            </p>

            <p>
                <strong>Custo da hora:</strong>
                ${formatarMoeda(custos.custoHoraReferencia)}
            </p>

            <p>
                <strong>Custo ABC de mão de obra:</strong>
                ${formatarMoeda(custos.custoAbcMaoDeObra)}
            </p>

            <p>
                <strong>Custo total estimado:</strong>
                ${formatarMoeda(custos.custoTotalEstimado)}
            </p>
        </div>
    `;
}

function montarEvidencias(evidencias) {
    if (evidencias.length === 0) {
        return "<p><strong>Evidências:</strong> Não cadastradas.</p>";
    }

    return `
        <h4>Evidências e fontes</h4>

        <ul>
            ${evidencias.map(evidencia => `
                <li>
                    <strong>${textoSeguro(evidencia.tipoEvidencia)}:</strong>
                    ${textoSeguro(evidencia.descricao)}
                </li>
            `).join("")}
        </ul>
    `;
}

function renderizarMetodologia(iniciativas) {
    const area = document.getElementById("memoriaCalculo");

    const iniciativa = iniciativas.find(
        item => item.custos && item.custos.custoAbcMaoDeObra !== undefined
    );

    if (!iniciativa) {
        area.innerHTML = "<p>Nenhum custo ABC cadastrado.</p>";
        return;
    }

    const custos = iniciativa.custos;

    area.innerHTML = `
        <div class="memoriaCalculo">
            <h3>Custo ABC simplificado de mão de obra</h3>

            <p class="formula">
                Custo da hora = remuneração de referência ÷ carga horária mensal
            </p>

            <p class="formula">
                ${textoSeguro(custos.quantidadeParticipantes)}
                participantes ×
                ${textoSeguro(custos.horasPorParticipante)}
                horas =
                ${textoSeguro(custos.totalHoras)}
                horas consumidas
            </p>

            <p class="formula">
                ${textoSeguro(custos.totalHoras)}
                horas ×
                ${formatarMoeda(custos.custoHoraReferencia)}
                =
                ${formatarMoeda(custos.custoAbcMaoDeObra)}
            </p>

            <p>
                Este cálculo ainda não inclui encargos, benefícios,
                energia, depreciação ou estrutura física.
            </p>
        </div>
    `;
}

function renderizarAuditoria(iniciativas, metadados = {}) {
    const area = document.getElementById("dadosAuditoria");

    const linhas = iniciativas.map(iniciativa => {
        const evidencias = Array.isArray(iniciativa.evidencias)
            ? iniciativa.evidencias
            : [];

        const situacaoEvidencia = evidencias.length > 0
            ? "Evidência cadastrada"
            : "Evidência pendente";

        return `
            <tr>
                <td>${textoSeguro(iniciativa.id)}</td>
                <td>${textoSeguro(iniciativa.tipoDado)}</td>
                <td>${textoSeguro(iniciativa.dataAtualizacao)}</td>
                <td>${textoSeguro(situacaoEvidencia)}</td>
            </tr>
        `;
    }).join("");

    area.innerHTML = `
        <p>
            <strong>Versão da metodologia:</strong>
            ${textoSeguro(metadados.versaoMetodologia || "Piloto")}
        </p>

        <div class="tabelaResponsiva">
            <table>
                <thead>
                    <tr>
                        <th>Iniciativa</th>
                        <th>Natureza</th>
                        <th>Atualização</th>
                        <th>Evidência</th>
                    </tr>
                </thead>

                <tbody>
                    ${linhas}
                </tbody>
            </table>
        </div>
    `;
}

function obterValoresUnicos(lista, campo) {
    return [...new Set(
        lista
            .map(item => item[campo])
            .filter(valor => valor !== null && valor !== undefined && valor !== "")
    )].sort((a, b) => String(a).localeCompare(String(b), "pt-BR"));
}

function normalizar(valor) {
    return String(valor || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

function limitarPercentual(valor) {
    const numero = Number(valor);

    if (!Number.isFinite(numero)) {
        return 0;
    }

    return Math.min(100, Math.max(0, numero));
}

function formatarMoeda(valor) {
    const numero = Number(valor);

    if (!Number.isFinite(numero)) {
        return "Não informado";
    }

    return numero.toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL"
    });
}

function formatarPercentual(valor) {
    const numero = Number(valor);

    if (!Number.isFinite(numero)) {
        return "Não informado";
    }

    return `${numero.toLocaleString("pt-BR", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 1
    })}%`;
}

function textoSeguro(valor) {
    return String(valor ?? "Não informado")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function apresentarErro(mensagem) {
    const aviso = `
        <div class="aviso">
            O painel ainda não conseguiu carregar os dados.
            Motivo: ${textoSeguro(mensagem)}
        </div>
    `;

    document.getElementById("resumoExecutivo").innerHTML = aviso;
    document.getElementById("cartoesIniciativas").innerHTML = aviso;
    document.getElementById("memoriaCalculo").innerHTML = aviso;
    document.getElementById("dadosAuditoria").innerHTML = aviso;

    console.error(mensagem);
}
