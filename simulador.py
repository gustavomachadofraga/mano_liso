#!/usr/bin/env python3
"""
Máquina Estatística - Probabilidade e Estatística I (IFES - Campus Serra)
Trabalho I - 2026/2

Simulador acadêmico - somente créditos fictícios.

Uso:
    python simulador.py                 # executa os cinco experimentos
    python simulador.py --rodada        # mostra uma única rodada (semente aleatória)
    python simulador.py --rodada --seed 7
    python simulador.py --saida pasta   # escolhe a pasta de resultados

Regras (Seção 5 do enunciado):
  * 5 símbolos (A..E) em cada rolo, sequência circular R = (A, B, C, D, E)
  * Parada K uniforme em {0,...,4}; coluna = R[K], R[(K+1)%5], R[(K+2)%5]
  * Três rolos independentes -> tabuleiro 3x3; só a LINHA CENTRAL é avaliada
  * Aposta fixa de 1 crédito; P = prêmio bruto; X = P - 1 = lucro líquido

A semente é controlada por quem inicia cada experimento: cada gerador
(random.Random) é criado UMA vez e passado às funções, nunca reiniciado
dentro de uma rodada.
"""

import argparse
import csv
import json
import os
import platform
import random
import statistics
import sys
from collections import Counter

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    TEM_MPL = True
except ImportError:  # os CSVs são gerados mesmo sem matplotlib
    TEM_MPL = False

# ----------------------------------------------------------------------------
# Regras do modelo
# ----------------------------------------------------------------------------
AVISO = "Simulador acadêmico - somente créditos fictícios"
ROLO = ("A", "B", "C", "D", "E")
APOSTA = 1
PREMIOS_BASE = {"A": 5, "B": 10, "C": 15, "D": 25, "E": 50}
# +10% calculado como v*11/10 para evitar erros de ponto flutuante (5,5; 11; ...)
PREMIOS_MAIS10 = {s: v * 11 / 10 for s, v in PREMIOS_BASE.items()}

N_TRIPLAS = 5 ** 3  # 125 triplas centrais equiprováveis

SEMENTE_E1 = 2026
SEMENTES_E2 = (10, 2026, 123456)
SEMENTE_E3 = 42
N_RODADAS = 10_000
CHECKPOINTS_E2 = (100, 1_000, 10_000)
N_PARTICIPANTES = 100
SALDO_INICIAL = 100
MAX_RODADAS_SESSAO = 500


# ----------------------------------------------------------------------------
# Núcleo: sorteio, janela e pagamento
# ----------------------------------------------------------------------------
def sortear_coluna(rng):
    """Sorteia a parada K e devolve a janela (topo, centro, base) de um rolo."""
    k = rng.randrange(5)
    return (ROLO[k], ROLO[(k + 1) % 5], ROLO[(k + 2) % 5])


def calcular_premio(centro, premios):
    """Prêmio bruto P: paga só se a linha central tem três símbolos iguais."""
    if centro[0] == centro[1] == centro[2]:
        return premios[centro[0]]
    return 0


def rodada(rng, premios=PREMIOS_BASE):
    """Executa uma rodada. Devolve (tabuleiro, centro, P, X).

    tabuleiro[r][l] = símbolo do rolo r (0..2) na linha l (0=topo, 1=centro, 2=base).
    """
    tabuleiro = [sortear_coluna(rng) for _ in range(3)]
    centro = tuple(coluna[1] for coluna in tabuleiro)
    p = calcular_premio(centro, premios)
    return tabuleiro, centro, p, p - APOSTA


def simular(rng, n, premios=PREMIOS_BASE):
    """Executa n rodadas sem saldo nem regra de parada.

    Devolve lista de tuplas (centro, P, X).
    """
    resultados = []
    for _ in range(n):
        _, centro, p, x = rodada(rng, premios)
        resultados.append((centro, p, x))
    return resultados


def mostrar_rodada(tabuleiro, centro, p, x):
    print(f"\n*** {AVISO} ***\n")
    print("        Rolo 1  Rolo 2  Rolo 3")
    for linha in range(3):
        marca = "-->" if linha == 1 else "   "
        simbolos = "       ".join(tabuleiro[r][linha] for r in range(3))
        print(f"  {marca}     {simbolos}")
    print(f"\nLinha central: {'-'.join(centro)}")
    print(f"Aposta: {APOSTA} crédito | Prêmio bruto P = {p:g} | Lucro X = {x:g}\n")


# ----------------------------------------------------------------------------
# Utilitários de saída
# ----------------------------------------------------------------------------
def escrever_csv(caminho, cabecalho, linhas):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecalho)
        w.writerows(linhas)


def salvar_figura(fig, caminho):
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


def fmt(v, casas=4):
    return f"{v:.{casas}f}"


# ----------------------------------------------------------------------------
# Experimento 1 - frequências x probabilidades
# ----------------------------------------------------------------------------
def distribuicao_teorica():
    """Lista (X, probabilidade) conforme a Tabela 1, em ordem crescente de X."""
    dist = [(-1, (N_TRIPLAS - 5) / N_TRIPLAS)]
    for simbolo in ROLO:
        dist.append((PREMIOS_BASE[simbolo] - APOSTA, 1 / N_TRIPLAS))
    return dist


def experimento1(saida):
    rng = random.Random(SEMENTE_E1)
    dados = simular(rng, N_RODADAS)
    xs = [x for _, _, x in dados]
    ps = [p for _, p, _ in dados]

    # Registro completo das rodadas
    escrever_csv(
        os.path.join(saida, "e1_rodadas.csv"),
        ["rodada", "linha_central", "P", "X"],
        [(i + 1, "-".join(c), p, x) for i, (c, p, x) in enumerate(dados)],
    )

    contagem = Counter(xs)
    dist = distribuicao_teorica()
    tabela = []
    for x, prob in dist:
        c = contagem.get(x, 0)
        tabela.append((x, prob, c, c / N_RODADAS))
    escrever_csv(
        os.path.join(saida, "e1_distribuicao.csv"),
        ["lucro_X", "prob_teorica", "contagem", "freq_relativa"],
        [(x, fmt(pt, 6), c, fmt(fr, 6)) for x, pt, c, fr in tabela],
    )

    media = sum(xs) / N_RODADAS
    rtp_obs = sum(ps) / N_RODADAS / APOSTA
    prop_premio = sum(1 for p in ps if p > 0) / N_RODADAS
    desvio = statistics.stdev(xs)  # divisor N-1
    resumo = [
        ("lucro_medio_X", fmt(media), "créditos/rodada"),
        ("lucro_esperado_teorico", "-0.1600", "créditos/rodada"),
        ("rtp_observado", fmt(100 * rtp_obs, 2), "%"),
        ("rtp_teorico", "84.00", "%"),
        ("proporcao_rodadas_premiadas", fmt(100 * prop_premio, 2), "%"),
        ("proporcao_teorica_premiadas", "4.00", "%"),
        ("desvio_padrao_amostral_X", fmt(desvio), "créditos"),
        ("soma_das_contagens", sum(contagem.values()), "rodadas"),
    ]
    escrever_csv(os.path.join(saida, "e1_resumo.csv"),
                 ["medida", "valor", "unidade"], resumo)

    if TEM_MPL:
        fig, ax = plt.subplots(figsize=(7, 4))
        pos = range(len(tabela))
        larg = 0.38
        ax.bar([i - larg / 2 for i in pos], [100 * t[1] for t in tabela],
               width=larg, label="Teoria")
        ax.bar([i + larg / 2 for i in pos], [100 * t[3] for t in tabela],
               width=larg, label="Observado (semente 2026)")
        ax.set_xticks(list(pos))
        ax.set_xticklabels([str(t[0]) for t in tabela])
        ax.set_xlabel("Lucro X por rodada (créditos)")
        ax.set_ylabel("Frequência (%)")
        ax.legend()
        salvar_figura(fig, os.path.join(saida, "e1_barras.png"))

    return dados, {
        "media": media, "rtp": rtp_obs, "prop": prop_premio,
        "desvio": desvio, "soma": sum(contagem.values()),
    }


# ----------------------------------------------------------------------------
# Experimento 2 - Lei dos Grandes Números
# ----------------------------------------------------------------------------
def experimento2(saida, dados_e1):
    sequencias = {}
    for semente in SEMENTES_E2:
        if semente == SEMENTE_E1:
            sequencias[semente] = [x for _, _, x in dados_e1]  # reutiliza o E1
        else:
            rng = random.Random(semente)
            sequencias[semente] = [x for _, _, x in simular(rng, N_RODADAS)]

    # Tabela 3 x 3 de médias acumuladas
    linhas = []
    for semente in SEMENTES_E2:
        xs = sequencias[semente]
        linhas.append([semente] + [fmt(sum(xs[:n]) / n) for n in CHECKPOINTS_E2])
    escrever_csv(os.path.join(saida, "e2_medias_acumuladas.csv"),
                 ["semente"] + [f"media_apos_{n}" for n in CHECKPOINTS_E2], linhas)

    # Trajetórias completas (para o gráfico)
    trajetorias = {}
    for semente, xs in sequencias.items():
        acum, soma = [], 0
        for i, x in enumerate(xs, start=1):
            soma += x
            acum.append(soma / i)
        trajetorias[semente] = acum
    escrever_csv(
        os.path.join(saida, "e2_trajetorias.csv"),
        ["rodada"] + [f"semente_{s}" for s in SEMENTES_E2],
        [[i + 1] + [fmt(trajetorias[s][i], 6) for s in SEMENTES_E2]
         for i in range(N_RODADAS)],
    )

    # Reprodução: repetir a semente 2026 no mesmo ambiente
    rng = random.Random(SEMENTE_E1)
    repetido = [x for _, _, x in simular(rng, 10)]
    original = sequencias[SEMENTE_E1][:10]
    reproduziu = repetido == original
    escrever_csv(
        os.path.join(saida, "e2_reproducao.csv"),
        ["rodada", "X_execucao_original", "X_execucao_repetida"],
        [(i + 1, original[i], repetido[i]) for i in range(10)],
    )

    if TEM_MPL:
        fig, ax = plt.subplots(figsize=(7, 4))
        for semente in SEMENTES_E2:
            ax.plot(range(1, N_RODADAS + 1), trajetorias[semente],
                    linewidth=1, label=f"Semente {semente}")
        ax.axhline(-0.16, color="black", linestyle="--", linewidth=1,
                   label="E[X] = -0,16")
        ax.set_xscale("log")
        ax.set_xlabel("Número de rodadas (escala logarítmica)")
        ax.set_ylabel("Média acumulada do lucro (créditos)")
        ax.legend()
        salvar_figura(fig, os.path.join(saida, "e2_trajetorias.png"))

    return {"reproduziu": reproduziu, "medias": linhas}


# ----------------------------------------------------------------------------
# Experimento 3 - saldo limitado
# ----------------------------------------------------------------------------
def experimento3(saida):
    rng = random.Random(SEMENTE_E3)  # iniciado uma vez; continua entre participantes
    participantes = []
    trajetorias = []
    for pid in range(1, N_PARTICIPANTES + 1):
        saldo = SALDO_INICIAL
        traj = [saldo]
        n = 0
        while n < MAX_RODADAS_SESSAO and saldo >= 1:
            _, _, _, x = rodada(rng)
            saldo += x  # B_{t+1} = B_t + X_{t+1}
            n += 1
            traj.append(saldo)
        participantes.append((pid, saldo, n, saldo < 1))
        trajetorias.append(traj)

    escrever_csv(
        os.path.join(saida, "e3_participantes.csv"),
        ["participante", "saldo_final", "rodadas_jogadas", "esgotou"],
        [(pid, s, n, int(e)) for pid, s, n, e in participantes],
    )

    finais = [s for _, s, _, _ in participantes]
    ganho = sum(1 for s in finais if s > SALDO_INICIAL)
    empate = sum(1 for s in finais if s == SALDO_INICIAL)
    perda = sum(1 for s in finais if s < SALDO_INICIAL)
    esgot = sum(1 for _, _, _, e in participantes if e)
    pct = lambda k: fmt(100 * k / N_PARTICIPANTES, 1)
    resumo = [
        ("ganho (Bf > 100)", ganho, pct(ganho)),
        ("empate (Bf = 100)", empate, pct(empate)),
        ("perda (Bf < 100)", perda, pct(perda)),
        ("esgotamento (subconjunto das perdas)", esgot, pct(esgot)),
        ("saldo_final_medio", fmt(statistics.mean(finais), 2), "créditos"),
        ("saldo_final_mediano", fmt(statistics.median(finais), 2), "créditos"),
        ("rodadas_medias_por_sessao",
         fmt(statistics.mean(n for _, _, n, _ in participantes), 1), "rodadas"),
    ]
    escrever_csv(os.path.join(saida, "e3_resumo.csv"),
                 ["medida", "valor", "percentual_ou_unidade"], resumo)

    # Trajetórias dos 5 primeiros (saldo constante após a parada)
    cinco = []
    for traj in trajetorias[:5]:
        cinco.append(traj + [traj[-1]] * (MAX_RODADAS_SESSAO + 1 - len(traj)))
    escrever_csv(
        os.path.join(saida, "e3_trajetorias_5_primeiros.csv"),
        ["rodada"] + [f"participante_{i}" for i in range(1, 6)],
        [[t] + [cinco[j][t] for j in range(5)]
         for t in range(MAX_RODADAS_SESSAO + 1)],
    )

    if TEM_MPL:
        fig, ax = plt.subplots(figsize=(7, 4))
        for j in range(5):
            ax.plot(range(MAX_RODADAS_SESSAO + 1), cinco[j], linewidth=1.2,
                    label=f"Participante {j + 1}")
        ax.axhline(SALDO_INICIAL, color="black", linestyle="--", linewidth=1,
                   label="Saldo inicial (100)")
        ax.set_xlabel("Rodada")
        ax.set_ylabel("Saldo (créditos)")
        ax.legend()
        salvar_figura(fig, os.path.join(saida, "e3_trajetorias.png"))

    return {"ganho": ganho, "empate": empate, "perda": perda,
            "esgot": esgot, "media": statistics.mean(finais),
            "mediana": statistics.median(finais),
            "soma_categorias": ganho + empate + perda}


# ----------------------------------------------------------------------------
# Experimento 4 - probabilidade condicional
# ----------------------------------------------------------------------------
def experimento4(saida, dados_e1):
    premiado = [p > 0 for _, p, _ in dados_e1]
    grupos = {"após prêmio": [0, 0], "após sem prêmio": [0, 0]}  # [pares, prêmios]
    for anterior, seguinte in zip(premiado[:-1], premiado[1:]):
        chave = "após prêmio" if anterior else "após sem prêmio"
        grupos[chave][0] += 1
        grupos[chave][1] += int(seguinte)

    linhas, props = [], {}
    for chave, (pares, premios) in grupos.items():
        if pares == 0:
            prop = "não estimável"
            props[chave] = None
        else:
            props[chave] = premios / pares
            prop = fmt(100 * premios / pares, 2) + "%"
        linhas.append((chave, pares, premios, prop))
    escrever_csv(os.path.join(saida, "e4_condicional.csv"),
                 ["resultado_anterior", "total_de_pares",
                  "premios_na_rodada_seguinte", "proporcao"], linhas)

    total_pares = sum(p for p, _ in grupos.values())
    return {"grupos": grupos, "props": props, "total_pares": total_pares}


# ----------------------------------------------------------------------------
# Experimento 5 - tabelas de pagamento
# ----------------------------------------------------------------------------
def experimento5(saida, dados_e1):
    centros = [c for c, _, _ in dados_e1]  # mesmos 10.000 resultados do E1
    configs = {"Base": PREMIOS_BASE, "Prêmios +10%": PREMIOS_MAIS10}
    linhas, rtps = [], {}
    for nome, tabela in configs.items():
        ps = [calcular_premio(c, tabela) for c in centros]
        n = len(ps)
        premio_medio = sum(ps) / n
        lucro_medio = premio_medio - APOSTA
        rtp_obs = premio_medio / APOSTA
        rtp_teo = sum(tabela.values()) / N_TRIPLAS / APOSTA
        freq_premio = sum(1 for p in ps if p > 0) / n
        rtps[nome] = (rtp_teo, rtp_obs)
        linhas.append((
            nome, "4.00", fmt(100 * freq_premio, 2),
            fmt(premio_medio), fmt(lucro_medio),
            fmt(100 * rtp_teo, 2), fmt(100 * rtp_obs, 2),
            fmt(rtp_teo - APOSTA, 4),
        ))
    escrever_csv(
        os.path.join(saida, "e5_comparacao.csv"),
        ["tabela", "prob_premio_teorica_%", "freq_premio_observada_%",
         "premio_medio_observado", "lucro_medio_observado",
         "RTP_teorico_%", "RTP_observado_%", "E_X_teorico"],
        linhas,
    )

    if TEM_MPL:
        fig, ax = plt.subplots(figsize=(6, 4))
        nomes = list(configs)
        pos = range(len(nomes))
        larg = 0.38
        ax.bar([i - larg / 2 for i in pos], [100 * rtps[n][0] for n in nomes],
               width=larg, label="RTP teórico")
        ax.bar([i + larg / 2 for i in pos], [100 * rtps[n][1] for n in nomes],
               width=larg, label="RTP observado")
        ax.axhline(100, color="black", linestyle="--", linewidth=1,
                   label="Retorno de 100% (jogo justo)")
        ax.set_xticks(list(pos))
        ax.set_xticklabels(nomes)
        ax.set_ylabel("RTP (%)")
        ax.set_ylim(0, 110)
        ax.legend(loc="lower right")
        salvar_figura(fig, os.path.join(saida, "e5_rtp.png"))

    return rtps


# ----------------------------------------------------------------------------
# Conferência antes da entrega
# ----------------------------------------------------------------------------
def conferir(e1, e2, e3, e4):
    # pagamento das cinco triplas e prêmio zero nas demais
    for s in ROLO:
        assert calcular_premio((s, s, s), PREMIOS_BASE) == PREMIOS_BASE[s]
    assert calcular_premio(("A", "A", "B"), PREMIOS_BASE) == 0
    assert calcular_premio(("B", "D", "A"), PREMIOS_BASE) == 0
    # desconto da aposta no lucro
    assert rodada(random.Random(1))[3] == rodada(random.Random(1))[2] - APOSTA
    # teoria
    assert abs(sum(PREMIOS_BASE.values()) / N_TRIPLAS - 0.84) < 1e-12
    # totais
    assert e1["soma"] == N_RODADAS
    assert e2["reproduziu"]
    assert e3["soma_categorias"] == N_PARTICIPANTES
    assert e4["total_pares"] == N_RODADAS - 1
    return True


def registrar_parametros(saida):
    info = {
        "aviso": AVISO,
        "python": sys.version,
        "plataforma": platform.platform(),
        "gerador": "random.Random (Mersenne Twister), método randrange(5)",
        "sementes": {"E1": SEMENTE_E1, "E2": list(SEMENTES_E2), "E3": SEMENTE_E3},
        "rodadas_E1_E2": N_RODADAS,
        "participantes_E3": N_PARTICIPANTES,
        "saldo_inicial_E3": SALDO_INICIAL,
        "max_rodadas_sessao_E3": MAX_RODADAS_SESSAO,
        "premios_base": PREMIOS_BASE,
        "premios_mais10": PREMIOS_MAIS10,
        "matplotlib": matplotlib.__version__ if TEM_MPL else "não instalado",
    }
    with open(os.path.join(saida, "parametros.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------------
# Programa principal
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=AVISO)
    ap.add_argument("--rodada", action="store_true",
                    help="mostra uma única rodada e termina")
    ap.add_argument("--seed", type=int, default=None,
                    help="semente para --rodada (padrão: aleatória)")
    ap.add_argument("--saida", default="resultados",
                    help="pasta de saída dos CSVs e gráficos")
    args = ap.parse_args()

    if args.rodada:
        rng = random.Random(args.seed)
        mostrar_rodada(*rodada(rng))
        return

    os.makedirs(args.saida, exist_ok=True)
    print(f"*** {AVISO} ***")
    print(f"Python {platform.python_version()} | random.Random (Mersenne Twister)")
    if not TEM_MPL:
        print("Aviso: matplotlib não encontrado; apenas os CSVs serão gerados.")

    # Uma rodada de demonstração (semente fixa só para a demonstração ser repetível)
    mostrar_rodada(*rodada(random.Random(2026)))

    registrar_parametros(args.saida)

    dados_e1, e1 = experimento1(args.saida)
    print("[E1] 10.000 rodadas, semente 2026")
    print(f"     lucro médio = {e1['media']:.4f} (teórico -0,1600)")
    print(f"     RTP observado = {100 * e1['rtp']:.2f}% (teórico 84%)")
    print(f"     rodadas premiadas = {100 * e1['prop']:.2f}% (teórico 4%)")
    print(f"     desvio-padrão amostral = {e1['desvio']:.4f} créditos")

    e2 = experimento2(args.saida, dados_e1)
    print("[E2] médias acumuladas (100 / 1.000 / 10.000 rodadas)")
    for linha in e2["medias"]:
        print(f"     semente {linha[0]:>6}: {linha[1]}  {linha[2]}  {linha[3]}")
    print(f"     reprodução da semente 2026 (10 primeiros): "
          f"{'reproduzida' if e2['reproduziu'] else 'NÃO reproduzida'}")

    e3 = experimento3(args.saida)
    print("[E3] 100 participantes, saldo 100, até 500 rodadas, semente 42")
    print(f"     ganho {e3['ganho']}% | empate {e3['empate']}% | perda {e3['perda']}% "
          f"| esgotamento {e3['esgot']}%")
    print(f"     saldo final: média {e3['media']:.2f}, mediana {e3['mediana']:.2f}")

    e4 = experimento4(args.saida, dados_e1)
    print(f"[E4] {e4['total_pares']} pares consecutivos")
    for chave, (pares, premios) in e4["grupos"].items():
        prop = e4["props"][chave]
        txt = "não estimável" if prop is None else f"{100 * prop:.2f}%"
        print(f"     {chave}: {premios}/{pares} = {txt} (referência 4%)")

    e5 = experimento5(args.saida, dados_e1)
    print("[E5] mesmos 10.000 resultados, duas tabelas de pagamento")
    for nome, (teo, obs) in e5.items():
        print(f"     {nome}: RTP teórico {100 * teo:.2f}% | observado {100 * obs:.2f}% "
              f"| E[X] teórico {teo - 1:.3f}")

    conferir(e1, e2, e3, e4)
    print("\nConferências automáticas: OK")
    print(f"Resultados salvos em: {os.path.abspath(args.saida)}")


if __name__ == "__main__":
    main()
