import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

from validar_dados import (
    COLUNAS_ESPERADAS,
    converter_numero,
    validar_dados,
)


ABAS = [
    "INICIATIVAS",
    "EXECUCAO_FINANCEIRA",
    "CUSTOS_ABC",
    "EVIDENCIAS",
]

ESCOPO_GOOGLE = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

AVISO_FICTICIO = (
    "DADOS FICTÍCIOS PARA TESTE DA METODOLOGIA."
)

AVISO_ESTIMADO = (
    "VALORES ESTIMADOS PARA VALIDAÇÃO DO PROJETO PILOTO."
)


def obter_variavel_ambiente(nome):
    valor = os.environ.get(nome, "").strip()

    if not valor:
        raise RuntimeError(
            f"A variável protegida {nome} não foi configurada."
        )

    return valor


def conectar_planilha():
    credencial_texto = obter_variavel_ambiente(
        "GOOGLE_SERVICE_ACCOUNT_JSON"
    )
    identificador_planilha = obter_variavel_ambiente(
        "GOOGLE_SPREADSHEET_ID"
    )

    try:
        dados_credencial = json.loads(credencial_texto)
    except json.JSONDecodeError as erro:
        raise RuntimeError(
            "A credencial do Google não possui um JSON válido."
        ) from erro

    credenciais = Credentials.from_service_account_info(
        dados_credencial,
        scopes=ESCOPO_GOOGLE,
    )

    cliente = gspread.authorize(credenciais)

    return cliente.open_by_key(identificador_planilha)


def remover_colunas_vazias(cabecalhos):
    resultado = list(cabecalhos)

    while resultado and not str(resultado[-1]).strip():
        resultado.pop()

    return [str(valor).strip() for valor in resultado]


def ler_aba(planilha, nome_aba):
    pagina = planilha.worksheet(nome_aba)
    matriz = pagina.get_all_values()

    if len(matriz) < 4:
        raise RuntimeError(
            f"A aba {nome_aba} não possui a linha de cabeçalhos."
        )

    cabecalhos = remover_colunas_vazias(matriz[3])
    registros = []

    for linha_planilha in matriz[4:]:
        linha_completa = linha_planilha + [""] * (
            len(cabecalhos) - len(linha_planilha)
        )

        registro = dict(
            zip(
                cabecalhos,
                linha_completa[:len(cabecalhos)],
            )
        )

        if any(
            str(valor).strip()
            for valor in registro.values()
        ):
            registros.append(registro)

    return cabecalhos, registros


def ler_todas_as_abas(planilha):
    cabecalhos = {}
    tabelas = {}

    for nome_aba in ABAS:
        cabecalho, registros = ler_aba(
            planilha,
            nome_aba,
        )

        cabecalhos[nome_aba] = cabecalho
        tabelas[nome_aba] = registros

    return cabecalhos, tabelas


def numero_para_json(valor):
    numero = (
        valor
        if isinstance(valor, Decimal)
        else converter_numero(valor)
    )

    if numero == numero.to_integral_value():
        return int(numero)

    return float(numero)


def calcular_percentual(valor, total):
    if total == 0:
        return Decimal("0")

    return valor / total * Decimal("100")


def criar_aviso(tipo_dado):
    if tipo_dado == "Fictício":
        return AVISO_FICTICIO

    if tipo_dado == "Estimado":
        return AVISO_ESTIMADO

    return ""


def preparar_execucao_financeira(linha):
    dotacao = converter_numero(
        linha["DOTACAO_ATUALIZADA"]
    )
    contratado = converter_numero(
        linha["VALOR_CONTRATADO"]
    )
    empenhado = converter_numero(
        linha["VALOR_EMPENHADO"]
    )
    liquidado = converter_numero(
        linha["VALOR_LIQUIDADO"]
    )
    pago = converter_numero(
        linha["VALOR_PAGO"]
    )

    saldo = dotacao - empenhado
    liquidado_a_pagar = liquidado - pago

    return {
        "periodo": linha["PERIODO"],
        "tipoDado": linha["TIPO_DADO"],
        "dotacaoAtualizada": numero_para_json(dotacao),
        "valorContratado": numero_para_json(contratado),
        "valorEmpenhado": numero_para_json(empenhado),
        "valorLiquidado": numero_para_json(liquidado),
        "valorPago": numero_para_json(pago),
        "saldoOrcamentario": numero_para_json(saldo),
        "liquidadoAPagar": numero_para_json(
            liquidado_a_pagar
        ),
        "execucaoEmpenho": numero_para_json(
            calcular_percentual(empenhado, dotacao)
        ),
        "execucaoLiquidacao": numero_para_json(
            calcular_percentual(liquidado, dotacao)
        ),
        "execucaoPagamento": numero_para_json(
            calcular_percentual(pago, dotacao)
        ),
        "aviso": criar_aviso(linha["TIPO_DADO"]),
    }


def preparar_custo_abc(linha):
    quantidade = converter_numero(
        linha["QTD_EMPREGADOS"]
    )
    remuneracao_referencia = converter_numero(
        linha["REMUNERACAO_MENSAL_REFERENCIA"]
    )
    carga_horaria = converter_numero(
        linha["CARGA_HORARIA_MENSAL"]
    )
    horas_por_empregado = converter_numero(
        linha["HORAS_POR_EMPREGADO"]
    )
    despesa_direta = converter_numero(
        linha["DESPESA_DIRETA"]
    )

    total_horas = quantidade * horas_por_empregado
    custo_hora = remuneracao_referencia / carga_horaria
    custo_abc = total_horas * custo_hora
    custo_total = custo_abc + despesa_direta

    return {
        "tipoDado": linha["TIPO_DADO"],
        "quantidadeParticipantes": numero_para_json(
            quantidade
        ),
        "horasPorParticipante": numero_para_json(
            horas_por_empregado
        ),
        "totalHoras": numero_para_json(total_horas),
        "custoHoraReferencia": numero_para_json(
            custo_hora
        ),
        "custoAbcMaoDeObra": numero_para_json(
            custo_abc
        ),
        "despesaDireta": numero_para_json(
            despesa_direta
        ),
        "custoTotalEstimado": numero_para_json(
            custo_total
        ),
        "metodologia": (
            "Custo da hora multiplicado pelo total "
            "de horas consumidas."
        ),
        "limitacoes": (
            "Não inclui encargos, benefícios, depreciação, "
            "energia ou estrutura física."
        ),
        "aviso": criar_aviso(linha["TIPO_DADO"]),
    }


def preparar_evidencia(linha):
    return {
        "tipoEvidencia": linha["TIPO_EVIDENCIA"],
        "descricao": linha["DESCRICAO"],
        "tipoDado": linha["TIPO_DADO"],
        "dataReferencia": linha["DATA_REFERENCIA"],
    }


def organizar_registros(tabelas):
    financeiro_por_iniciativa = {}
    custos_por_iniciativa = {}
    evidencias_por_iniciativa = defaultdict(list)

    for linha in tabelas["EXECUCAO_FINANCEIRA"]:
        identificador = linha["ID_INICIATIVA"]

        financeiro_por_iniciativa[identificador] = (
            preparar_execucao_financeira(linha)
        )

    for linha in tabelas["CUSTOS_ABC"]:
        identificador = linha["ID_INICIATIVA"]

        custos_por_iniciativa[identificador] = (
            preparar_custo_abc(linha)
        )

    for linha in tabelas["EVIDENCIAS"]:
        identificador = linha["ID_INICIATIVA"]

        evidencias_por_iniciativa[identificador].append(
            preparar_evidencia(linha)
        )

    return (
        financeiro_por_iniciativa,
        custos_por_iniciativa,
        evidencias_por_iniciativa,
    )


def preparar_json_publico(tabelas):
    (
        financeiro_por_iniciativa,
        custos_por_iniciativa,
        evidencias_por_iniciativa,
    ) = organizar_registros(tabelas)

    iniciativas_publicas = []

    for linha in tabelas["INICIATIVAS"]:
        identificador = linha["ID_INICIATIVA"]

        iniciativa = {
            "id": identificador,
            "iniciativa": linha["INICIATIVA"],
            "objetivoEstrategico": (
                linha["OBJETIVO_ESTRATEGICO"]
            ),
            "programa": linha["PROGRAMA"],
            "prioridade": linha["PRIORIDADE"],
            "status": linha["STATUS"],
            "execucaoFisica": numero_para_json(
                linha["EXECUCAO_FISICA"]
            ),
            "tipoDado": linha["TIPO_DADO"],
            "formaExecucao": linha["FORMA_EXECUCAO"],
            "resultadoEntregue": (
                linha["RESULTADO_ENTREGUE"]
            ),
            "responsavel": linha["RESPONSAVEL"],
            "dataAtualizacao": linha["DATA_ATUALIZACAO"],
            "aviso": criar_aviso(linha["TIPO_DADO"]),
            "evidencias": evidencias_por_iniciativa.get(
                identificador,
                [],
            ),
        }

        if identificador in financeiro_por_iniciativa:
            iniciativa["financeiro"] = (
                financeiro_por_iniciativa[identificador]
            )

        if identificador in custos_por_iniciativa:
            iniciativa["custos"] = (
                custos_por_iniciativa[identificador]
            )

        iniciativas_publicas.append(iniciativa)

    agora = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    )

    return {
        "metadados": {
            "titulo": "Monitor do PPA do Coren-GO",
            "versaoMetodologia": "Projeto piloto 1.0",
            "dataGeracao": agora.strftime(
                "%d/%m/%Y às %H:%M"
            ),
            "quantidadeIniciativas": len(
                iniciativas_publicas
            ),
            "aviso": (
                "O projeto piloto contém valores estimados "
                "e dados fictícios identificados."
            ),
        },
        "iniciativas": iniciativas_publicas,
    }


def verificar_json_publico(dados_publicos):
    texto_json = json.dumps(
        dados_publicos,
        ensure_ascii=False,
    )

    termos_proibidos = [
        "REMUNERACAO_MENSAL_REFERENCIA",
        "remuneracaoMensalReferencia",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "private_key",
        "client_email",
        "DOCUMENTO_OU_LINK",
        "OBSERVACOES",
    ]

    encontrados = [
        termo
        for termo in termos_proibidos
        if termo in texto_json
    ]

    if encontrados:
        raise RuntimeError(
            "O JSON público contém campos proibidos: "
            + ", ".join(encontrados)
        )


def salvar_json(dados_publicos):
    pasta_saida = Path("data")
    pasta_saida.mkdir(parents=True, exist_ok=True)

    arquivo_saida = pasta_saida / "iniciativas.json"

    with arquivo_saida.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            dados_publicos,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

        arquivo.write("\n")

    print(
        "JSON público gerado com sucesso em "
        "data/iniciativas.json."
    )


def executar():
    planilha = conectar_planilha()
    cabecalhos, tabelas = ler_todas_as_abas(planilha)

    erros = validar_dados(
        tabelas,
        cabecalhos,
    )

    if erros:
        print(
            "PUBLICAÇÃO BLOQUEADA PELA VALIDAÇÃO:",
            file=sys.stderr,
        )

        for erro in erros:
            print(
                f"• {erro}",
                file=sys.stderr,
            )

        raise SystemExit(1)

    dados_publicos = preparar_json_publico(tabelas)
    verificar_json_publico(dados_publicos)
    salvar_json(dados_publicos)


if __name__ == "__main__":
    try:
        executar()
    except SystemExit:
        raise
    except Exception as erro:
        print(
            "Falha controlada no processamento: "
            f"{type(erro).__name__}: {erro}",
            file=sys.stderr,
        )
        raise SystemExit(1)
