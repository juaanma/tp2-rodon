"""Punto de entrada: analizador de tandas reales y asistente para elegir el
orden de pateadores.

Operaciones (subcomandos):
  historico        analiza las tandas reales (con filtros por torneo y años)
  validar-modelo   compara el simulador calibrado con las tandas reales
  simular          probabilidad de que un equipo le gane la tanda a otro
  recomendar-orden ranking de los 120 órdenes posibles de 5 pateadores
"""

import argparse
import sys
from pathlib import Path

from src.fuentes import elegir_fuente
from src.graficos import graficar_distribucion, graficar_ranking
from src.pipeline import (COLUMNAS_HISTORICO, COLUMNAS_PLANTELES,
                          analizar_historico, buscar_equipo, comparar_con_modelo,
                          construir_equipos, elegir_pateadores, filtrar_historico,
                          guardar_csv, guardar_json, inspeccionar,
                          limpiar_historico, validar_esquema, verificar_ranking)
from src.simulacion import (ModeloPenales, calibrar_efectividad,
                            diferencia_pareada, recomendar_orden,
                            simular_enfrentamiento)

HISTORICO_POR_DEFECTO = "data/tandas_historicas.csv"
PLANTELES_POR_DEFECTO = "data/planteles.csv"


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(
        description="Tandas de penales: análisis de datos reales y simulación "
                    "para decidir el orden de los pateadores.")
    sub = parser.add_subparsers(dest="operacion", required=True)

    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--historico", default=HISTORICO_POR_DEFECTO,
                         help="tandas reales (.csv o .json)")
    comunes.add_argument("--salida", default="outputs",
                         help="carpeta de resultados (por defecto: outputs)")
    comunes.add_argument("--torneo", choices=["Mundial", "Eurocopa", "Copa America"],
                         help="usar solo las tandas reales de ese torneo")
    comunes.add_argument("--desde", type=int, help="año inicial de las tandas reales")
    comunes.add_argument("--hasta", type=int, help="año final de las tandas reales")

    simulacion = argparse.ArgumentParser(add_help=False)
    simulacion.add_argument("--repeticiones", type=int, default=5000)
    simulacion.add_argument("--semilla", type=int, default=2026)
    simulacion.add_argument("--presion", type=float, default=0.25,
                            help="caída de efectividad bajo presión (0 = sin efecto)")

    sub.add_parser("historico", parents=[comunes], help="analiza las tandas reales")

    sub.add_parser("validar-modelo", parents=[comunes, simulacion],
                   help="compara el simulador con las tandas reales")

    for nombre, ayuda in (("simular", "probabilidad de ganar A vs B"),
                          ("recomendar-orden", "mejor orden de pateadores")):
        p = sub.add_parser(nombre, parents=[comunes, simulacion], help=ayuda)
        p.add_argument("--planteles", default=PLANTELES_POR_DEFECTO)
        p.add_argument("--equipo", required=True, help="código, ej: NOR")
        p.add_argument("--rival", required=True, help="código, ej: SUR")
        p.add_argument("--pateadores", nargs="*",
                       help="5 nombres en orden (por defecto: los 5 mejores)")
        p.add_argument("--empieza", choices=["A", "B", "sorteo"], default="sorteo",
                       help="quién patea primero (A = --equipo)")

    args = parser.parse_args(argv)
    if getattr(args, "repeticiones", 1) <= 0:
        parser.error("--repeticiones debe ser mayor que 0")
    return args


def cargar(ruta, requeridas):
    """Lee, inspecciona y valida el esquema de un archivo de entrada."""
    filas = elegir_fuente(ruta).cargar(ruta)
    info = inspeccionar(filas)
    con_vacios = {c: n for c, n in info["vacios_por_columna"].items() if n}
    print(f"Leído {ruta}: {info['registros']} registros, "
          f"{len(info['columnas'])} columnas. Vacíos: {con_vacios or 'ninguno'}")
    validar_esquema(filas, requeridas)
    return filas


def cargar_historico(args):
    filas = cargar(args.historico, COLUMNAS_HISTORICO)
    tandas, rechazos = limpiar_historico(filas)
    ruta = guardar_csv(rechazos, Path(args.salida) / "historico_rechazos.csv",
                       ["registro", "id", "motivo"])
    print(f"Tandas válidas: {len(tandas)} | rechazadas: {len(rechazos)} (ver {ruta})")
    for r in rechazos[:5]:
        print(f"  - registro {r['registro']} ({r['id']}): {r['motivo']}")
    seleccion = filtrar_historico(tandas, args.torneo, args.desde, args.hasta)
    if len(seleccion) != len(tandas):
        print(f"Filtro aplicado: {len(seleccion)} tandas seleccionadas")
    if not seleccion:
        raise ValueError("ninguna tanda cumple los filtros indicados")
    return seleccion


def calibrar(args, tandas):
    """Efectividad base que reproduce la conversión real con este modelo."""
    modelo = ModeloPenales(args.presion)
    conversion = analizar_historico(tandas)["general"]["conversion"]
    base = calibrar_efectividad(modelo, conversion, semilla=args.semilla)
    print(f"Conversión real: {conversion:.1%} → efectividad base calibrada "
          f"(presión {args.presion}): {base:.1%}")
    return modelo, base


def op_historico(args):
    analisis = analizar_historico(cargar_historico(args))
    analisis["filtros"] = {"torneo": args.torneo, "desde": args.desde,
                           "hasta": args.hasta}
    salida = Path(args.salida)
    guardar_json(analisis, salida / "historico_resumen.json")
    guardar_csv(analisis["por_grupo"], salida / "historico_por_grupo.csv")

    g = analisis["general"]
    print(f"\n{g['tandas']} tandas, {g['penales_pateados']} penales: conversión "
          f"{g['conversion']:.1%} (IC 95 %: {g['conversion_ic95'][0]:.1%}–"
          f"{g['conversion_ic95'][1]:.1%})")
    print(f"Penales por tanda: {g['tiros_promedio']} | llegan a muerte súbita: "
          f"{g['prop_muerte_subita']:.1%}\n")
    print(f"{'grupo':<14}{'tandas':>7}{'conversión':>12}{'muerte súbita':>15}")
    for fila in analisis["por_grupo"]:
        print(f"{fila['grupo']:<14}{fila['tandas']:>7}{fila['conversion']:>12.1%}"
              f"{fila['prop_muerte_subita']:>15.1%}")
    p = analisis["quien_patea_primero"]
    if p["tandas_con_dato"]:
        print(f"\nCon dato de quién empezó ({p['tandas_con_dato']} tandas): ganó el "
              f"que pateó primero en {p['proporcion']:.1%} (subconjunto sesgado)")
    print(f"\nResultados en {salida}/historico_resumen.json y historico_por_grupo.csv")


def op_validar_modelo(args):
    tandas = cargar_historico(args)
    modelo, base = calibrar(args, tandas)
    comparacion = comparar_con_modelo(tandas, modelo, base,
                                      args.repeticiones, args.semilla)
    salida = Path(args.salida)
    guardar_csv(comparacion, salida / "validacion_modelo.csv")
    print(f"\n{'medida':<28}{'real':>8}{'simulado':>10}{'dif.':>8}")
    for f in comparacion:
        print(f"{f['medida']:<28}{f['real']:>8.3f}{f['simulado']:>10.3f}"
              f"{f['diferencia']:>+8.3f}")
    grafico = graficar_distribucion(comparacion, salida / "validacion_modelo.png")
    print(f"\nTabla en {salida}/validacion_modelo.csv"
          + (f"; gráfico en {grafico}" if grafico else
             " (gráfico omitido: matplotlib no está instalado)"))


def preparar_equipos(args):
    tandas = cargar_historico(args)
    modelo, base = calibrar(args, tandas)
    filas = cargar(args.planteles, COLUMNAS_PLANTELES)
    equipos, rechazos = construir_equipos(filas, base)
    ruta = guardar_csv(rechazos, Path(args.salida) / "planteles_rechazos.csv",
                       ["registro", "equipo", "motivo"])
    print(f"Equipos válidos: {', '.join(sorted(equipos)) or 'ninguno'} | "
          f"registros rechazados: {len(rechazos)} (ver {ruta})")
    equipo = buscar_equipo(equipos, args.equipo)
    rival = buscar_equipo(equipos, args.rival)
    if equipo is rival:
        raise ValueError("el equipo y el rival deben ser distintos")
    estimados = [p.nombre for p in equipo.pateadores if p.efectividad_estimada]
    if estimados:
        print(f"Sin dato de efectividad en {equipo.codigo} (se usa {base:.1%}): "
              f"{', '.join(estimados)}")
    return modelo, equipo, rival


def op_simular(args):
    modelo, equipo, rival = preparar_equipos(args)
    orden = elegir_pateadores(equipo, args.pateadores)
    tandas, resumen = simular_enfrentamiento(
        modelo, equipo, rival, args.repeticiones, args.semilla,
        orden_a=orden, empieza=args.empieza)
    salida = Path(args.salida)
    nombre = f"simulacion_{equipo.codigo}_vs_{rival.codigo}"
    guardar_csv(tandas, salida / f"{nombre}_tandas.csv")
    guardar_json({"equipo": equipo.codigo, "rival": rival.codigo,
                  "orden": [p.nombre for p in orden],
                  "parametros": {"repeticiones": args.repeticiones,
                                 "semilla": args.semilla, "presion": args.presion,
                                 "empieza": args.empieza},
                  "resultado": resumen}, salida / f"{nombre}.json")
    print(f"\n{equipo.nombre} ({' → '.join(p.nombre for p in orden)}) vs "
          f"{rival.nombre}")
    print(f"Probabilidad de ganar: {resumen['prob_gana_a']:.1%} (IC 95 %: "
          f"{resumen['ic95_gana_a'][0]:.1%}–{resumen['ic95_gana_a'][1]:.1%})")
    print(f"Resultados en {salida}/{nombre}.json")


def op_recomendar_orden(args):
    modelo, equipo, rival = preparar_equipos(args)
    candidatos = elegir_pateadores(equipo, args.pateadores)
    print(f"Probando los 120 órdenes de: {', '.join(p.nombre for p in candidatos)} "
          f"({args.repeticiones} tandas cada uno)...")
    ranking = recomendar_orden(modelo, equipo, rival, candidatos,
                               args.repeticiones, args.semilla, args.empieza)
    verificar_ranking(ranking)
    salida = Path(args.salida)
    nombre = f"orden_{equipo.codigo}_vs_{rival.codigo}"
    filas = [{"posicion": r["posicion"], "orden": " > ".join(r["orden"]),
              "prob_ganar": r["prob_ganar"], "ic95_inf": r["ic95"][0],
              "ic95_sup": r["ic95"][1]} for r in ranking]
    guardar_csv(filas, salida / f"{nombre}.csv")
    grafico = graficar_ranking(ranking, salida / f"{nombre}.png")

    actual = next(r for r in ranking if r["orden"] == [p.nombre for p in candidatos])
    mejor, peor = ranking[0], ranking[-1]
    print(f"\nMejor orden:  {' → '.join(mejor['orden'])}  {mejor['prob_ganar']:.1%}")
    print(f"Orden actual: {' → '.join(actual['orden'])}  {actual['prob_ganar']:.1%} "
          f"(puesto {actual['posicion']})")
    print(f"Peor orden:   {' → '.join(peor['orden'])}  {peor['prob_ganar']:.1%}")

    # Elegir el máximo entre 120 órdenes favorece al que tuvo suerte en la
    # simulación. Por eso se vuelve a simular el mejor y el actual con otra
    # semilla y se compara tanda a tanda.
    otra_semilla = args.semilla + 1
    nuevos = {}
    for clave, fila in (("mejor", mejor), ("actual", actual)):
        orden = [equipo.pateador(n) for n in fila["orden"]]
        tandas, _ = simular_enfrentamiento(modelo, equipo, rival, args.repeticiones,
                                           otra_semilla, orden_a=orden,
                                           empieza=args.empieza)
        nuevos[clave] = [t["gana_a"] for t in tandas]
    mejora = diferencia_pareada(nuevos["mejor"], nuevos["actual"])
    significativa = mejora["ic95"][0] > 0
    print(f"\nVerificación con otra semilla ({otra_semilla}): el mejor orden supera "
          f"al actual por {100 * mejora['diferencia']:+.1f} puntos "
          f"(IC 95 %: {100 * mejora['ic95'][0]:+.1f} a {100 * mejora['ic95'][1]:+.1f}).")
    print("Conclusión: " + ("cambiar el orden mejora la probabilidad de ganar."
                            if significativa else
                            "la diferencia no es concluyente; el orden actual "
                            "rinde parecido."))
    guardar_json({"equipo": equipo.codigo, "rival": rival.codigo,
                  "parametros": {"repeticiones": args.repeticiones,
                                 "semilla": args.semilla, "presion": args.presion,
                                 "empieza": args.empieza},
                  "mejor": {k: mejor[k] for k in ("orden", "prob_ganar", "ic95")},
                  "actual": {k: actual[k] for k in ("orden", "prob_ganar", "ic95",
                                                    "posicion")},
                  "peor": {k: peor[k] for k in ("orden", "prob_ganar", "ic95")},
                  "verificacion": {"semilla": otra_semilla, **mejora,
                                   "mejora_significativa": significativa}},
                 salida / f"{nombre}.json")
    print(f"\nRanking completo en {salida}/{nombre}.csv"
          + (f"; gráfico en {grafico}" if grafico else ""))


OPERACIONES = {"historico": op_historico, "validar-modelo": op_validar_modelo,
               "simular": op_simular, "recomendar-orden": op_recomendar_orden}


def main(argv=None):
    args = leer_argumentos(argv)
    try:
        OPERACIONES[args.operacion](args)
    except (ValueError, FileNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
