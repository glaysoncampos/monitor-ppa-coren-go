from decimal import Decimal, InvalidOperation


TIPOS_DADO_PERMITIDOS = {
    "Real",
    "Estimado",
    "Fictício",
}

STATUS_PERMITIDOS = {
    "Não iniciada",
    "Fazendo",
    "Concluída",
    "Pausada",
}

COLUNAS_ESPERADAS = {
    "INICIATIVAS": [
        "ID_INICIATIVA",
        "INICIATIVA",
        "OBJETIVO_ESTRATEGICO",
        "PROGRAMA",
        "PRIORIDADE",
        "STATUS",
        "EXECUCAO_FISICA",
        "TIPO_DADO",
        "FORMA_EXECUCAO",
        "RESULTADO_ENTREGUE",
        "RESPONSAVEL",
        "DATA_ATUALIZACAO",
        "OBSERVACOES",
    ],
    "EXECUCAO_FINANCEIRA": [
        "ID_REGISTRO",
        "ID_INICIATIVA",
        "PERIODO",
        "TIPO_DADO",
        "DOTACAO_ATUALIZADA",
        "VALOR_CONTRATADO",
        "VALOR_EMPENHADO",
        "VALOR_LIQUIDADO",
        "VALOR_PAGO",
        "SALDO_ORCAMENTARIO",
        "LIQUIDADO_A_PAGAR",
        "EXECUCAO_EMPENHO",
        "EXECUCAO_LIQUIDACAO",
        "EXECUCAO_PAGAMENTO",
        "OBSERVACOES",
    ],
    "CUSTOS_ABC": [
        "ID_CUSTO",
        "ID_INICIATIVA",
        "TIPO_DADO",
        "QTD_EMPREGADOS",
        "REMUNERACAO_MENSAL_REFERENCIA",
        "CARGA_HORARIA_MENSAL",
        "HORAS_POR_EMPREGADO",
        "TOTAL_HORAS",
        "CUSTO_HORA",
        "CUSTO_ABC_MAO_DE_OBRA",
        "DESPESA_DIRETA",
        "CUSTO_TOTAL_ESTIMADO",
        "OBSERVACOES",
    ],
    "EVIDENCIAS": [
        "ID_EVIDENCIA",
        "ID_INICIATIVA",
        "TIPO_EVIDENCIA",
        "DESCRICAO",
        "DOCUMENTO_OU_LINK",
        "TIPO_DADO",
        "DATA_REFERENCIA",
        "OBSERVACOES",
    ],
}

CAMPOS_OBRIGATORIOS = {
    aba: [
        coluna
        for coluna in colunas
        if coluna != "OBSERVACOES"
    ]
    for aba, colunas in COLUNAS_ESPERADAS.items()
}


def converter_numero(valor):
    if isinstance(valor, Decimal):
        return valor

    if isinstance(valor, (int, float)):
        return Decimal(str(valor))

    texto = str(valor).strip()

    if not texto:
        raise InvalidOperation

    texto = (
        texto.replace("R$", "")
        .replace("%", "")
        .replace("\u00a0", "")
        .replace(" ", "")
    )

    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")

    return Decimal(texto)


def numeros_iguais(valor_atual, valor_esperado, tolerancia="0.01"):
    return abs(valor_atual - valor_esperado) <= Decimal(tolerancia)


def validar_colunas(cabecalhos, erros):
    for aba, colunas_esperadas in COLUNAS_ESPERADAS.items():
        colunas_encontradas = cabecalhos.get(aba, [])

        if colunas_encontradas != colunas_esperadas:
            erros.append(
                f"{aba}: as colunas estão ausentes, fora de ordem "
                "ou possuem nomes diferentes do modelo."
            )


def validar_campos_obrigatorios(tabelas, erros):
    for aba, linhas in tabelas.items():
        campos = CAMPOS_OBRIGATORIOS.get(aba, [])

        for numero_linha, linha in enumerate(linhas, start=5):
            for campo in campos:
                valor = linha.get(campo)

                if valor is None or str(valor).strip() == "":
                    erros.append(
                        f"{aba}, linha {numero_linha}: "
                        f"o campo {campo} está vazio."
                    )


def validar_identificadores(tabelas, erros):
    configuracao_ids = {
        "INICIATIVAS": "ID_INICIATIVA",
        "EXECUCAO_FINANCEIRA": "ID_REGISTRO",
        "CUSTOS_ABC": "ID_CUSTO",
        "EVIDENCIAS": "ID_EVIDENCIA",
    }

    for aba, campo_id in configuracao_ids.items():
        encontrados = set()

        for linha in tabelas.get(aba, []):
            identificador = str(linha.get(campo_id, "")).strip()

            if identificador in encontrados:
                erros.append(
                    f"{aba}: identificador duplicado {identificador}."
                )

            encontrados.add(identificador)

    ids_iniciativas = {
        str(linha.get("ID_INICIATIVA", "")).strip()
        for linha in tabelas.get("INICIATIVAS", [])
    }

    for aba in [
        "EXECUCAO_FINANCEIRA",
        "CUSTOS_ABC",
        "EVIDENCIAS",
    ]:
        for linha in tabelas.get(aba, []):
            identificador = str(
                linha.get("ID_INICIATIVA", "")
            ).strip()

            if identificador not in ids_iniciativas:
                erros.append(
                    f"{aba}: a iniciativa {identificador} "
                    "não existe na aba INICIATIVAS."
                )


def validar_classificacoes(tabelas, erros):
    for linha in tabelas.get("INICIATIVAS", []):
        status = str(linha.get("STATUS", "")).strip()

        if status not in STATUS_PERMITIDOS:
            erros.append(
                f"INICIATIVAS: status não permitido: {status}."
            )

    for aba, linhas in tabelas.items():
        for linha in linhas:
            tipo = str(linha.get("TIPO_DADO", "")).strip()

            if tipo not in TIPOS_DADO_PERMITIDOS:
                erros.append(
                    f"{aba}: natureza do dado não permitida: {tipo}."
                )


def validar_execucao_fisica(tabelas, erros):
    for linha in tabelas.get("INICIATIVAS", []):
        identificador = linha.get("ID_INICIATIVA")

        try:
            percentual = converter_numero(
                linha.get("EXECUCAO_FISICA")
            )

            if percentual < 0 or percentual > 100:
                erros.append(
                    f"{identificador}: execução física deve estar "
                    "entre 0% e 100%."
                )
        except InvalidOperation:
            erros.append(
                f"{identificador}: execução física inválida."
            )


def validar_execucao_financeira(tabelas, erros):
    campos_financeiros = [
        "DOTACAO_ATUALIZADA",
        "VALOR_CONTRATADO",
        "VALOR_EMPENHADO",
        "VALOR_LIQUIDADO",
        "VALOR_PAGO",
        "SALDO_ORCAMENTARIO",
        "LIQUIDADO_A_PAGAR",
    ]

    for linha in tabelas.get("EXECUCAO_FINANCEIRA", []):
        identificador = linha.get("ID_INICIATIVA")
        valores = {}

        try:
            for campo in campos_financeiros:
                valores[campo] = converter_numero(linha.get(campo))

                if valores[campo] < 0:
                    erros.append(
                        f"{identificador}: {campo} não pode ser negativo."
                    )

            dotacao = valores["DOTACAO_ATUALIZADA"]
            empenhado = valores["VALOR_EMPENHADO"]
            liquidado = valores["VALOR_LIQUIDADO"]
            pago = valores["VALOR_PAGO"]
            saldo = valores["SALDO_ORCAMENTARIO"]
            liquidado_a_pagar = valores["LIQUIDADO_A_PAGAR"]

            if pago > liquidado:
                erros.append(
                    f"{identificador}: o valor pago supera o liquidado."
                )

            if liquidado > empenhado:
                erros.append(
                    f"{identificador}: o liquidado supera o empenhado."
                )

            if not numeros_iguais(saldo, dotacao - empenhado):
                erros.append(
                    f"{identificador}: saldo orçamentário incorreto."
                )

            if not numeros_iguais(
                liquidado_a_pagar,
                liquidado - pago,
            ):
                erros.append(
                    f"{identificador}: liquidado a pagar incorreto."
                )

            percentuais_esperados = {
                "EXECUCAO_EMPENHO": (
                    empenhado / dotacao * 100 if dotacao else Decimal("0")
                ),
                "EXECUCAO_LIQUIDACAO": (
                    liquidado / dotacao * 100 if dotacao else Decimal("0")
                ),
                "EXECUCAO_PAGAMENTO": (
                    pago / dotacao * 100 if dotacao else Decimal("0")
                ),
            }

            for campo, esperado in percentuais_esperados.items():
                atual = converter_numero(linha.get(campo))

                if atual < 0 or atual > 100:
                    erros.append(
                        f"{identificador}: {campo} deve estar "
                        "entre 0% e 100%."
                    )

                if not numeros_iguais(atual, esperado, "0.1"):
                    erros.append(
                        f"{identificador}: {campo} não corresponde "
                        "aos valores financeiros."
                    )

        except InvalidOperation:
            erros.append(
                f"{identificador}: existe valor financeiro inválido."
            )


def validar_custos_abc(tabelas, erros):
    for linha in tabelas.get("CUSTOS_ABC", []):
        identificador = linha.get("ID_INICIATIVA")

        try:
            quantidade = converter_numero(
                linha.get("QTD_EMPREGADOS")
            )
            remuneracao = converter_numero(
                linha.get("REMUNERACAO_MENSAL_REFERENCIA")
            )
            carga_horaria = converter_numero(
                linha.get("CARGA_HORARIA_MENSAL")
            )
            horas_por_empregado = converter_numero(
                linha.get("HORAS_POR_EMPREGADO")
            )
            total_horas = converter_numero(
                linha.get("TOTAL_HORAS")
            )
            custo_hora = converter_numero(
                linha.get("CUSTO_HORA")
            )
            custo_abc = converter_numero(
                linha.get("CUSTO_ABC_MAO_DE_OBRA")
            )
            despesa_direta = converter_numero(
                linha.get("DESPESA_DIRETA")
            )
            custo_total = converter_numero(
                linha.get("CUSTO_TOTAL_ESTIMADO")
            )

            valores = [
                quantidade,
                remuneracao,
                carga_horaria,
                horas_por_empregado,
                total_horas,
                custo_hora,
                custo_abc,
                despesa_direta,
                custo_total,
            ]

            if any(valor < 0 for valor in valores):
                erros.append(
                    f"{identificador}: custos e quantidades "
                    "não podem ser negativos."
                )

            if carga_horaria == 0:
                erros.append(
                    f"{identificador}: carga horária não pode ser zero."
                )
                continue

            if not numeros_iguais(
                total_horas,
                quantidade * horas_por_empregado,
            ):
                erros.append(
                    f"{identificador}: total de horas incorreto."
                )

            if not numeros_iguais(
                custo_hora,
                remuneracao / carga_horaria,
            ):
                erros.append(
                    f"{identificador}: custo da hora incorreto."
                )

            if not numeros_iguais(
                custo_abc,
                total_horas * custo_hora,
            ):
                erros.append(
                    f"{identificador}: custo ABC incorreto."
                )

            if not numeros_iguais(
                custo_total,
                custo_abc + despesa_direta,
            ):
                erros.append(
                    f"{identificador}: custo total estimado incorreto."
                )

            if identificador == "IE_01" and not numeros_iguais(
                custo_abc,
                Decimal("2000"),
            ):
                erros.append(
                    "IE_01: o piloto deve reproduzir o custo "
                    "ABC de R$ 2.000,00."
                )

        except InvalidOperation:
            erros.append(
                f"{identificador}: existe valor inválido "
                "no cálculo do custo ABC."
            )


def validar_dados(tabelas, cabecalhos):
    erros = []

    validar_colunas(cabecalhos, erros)
    validar_campos_obrigatorios(tabelas, erros)
    validar_identificadores(tabelas, erros)
    validar_classificacoes(tabelas, erros)
    validar_execucao_fisica(tabelas, erros)
    validar_execucao_financeira(tabelas, erros)
    validar_custos_abc(tabelas, erros)

    return erros
