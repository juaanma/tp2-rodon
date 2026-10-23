"""Punto de entrada: simulador de tandas de penales."""

import argparse
import sys

from src.fuentes import elegir_fuente
from src.pipeline import (ejecutar_escenario, guardar_experimento,
                          guardar_rechazos, limpiar_escenarios,
                          resumir_experimento, seleccionar, validar_esquema)


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(
        description="Simula tandas de penales a partir de escenarios CSV o JSON.")
    parser.add_argument("--entrada", required=True,
                        help="archivo de escenarios (.csv o .json)")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--escenario", help="id a ejecutar, por ejemplo ESC-001")
    grupo.add_argument("--todos", action="store_true",
                       help="ejecutar todos los escenarios validos")
    parser.add_argument("--salida", default="outputs",
                        help="carpeta de resultados (por defecto: outputs)")
    return parser.parse_args(argv)


def main(argv=None):
    args = leer_argumentos(argv)
    try:
        fuente = elegir_fuente(args.entrada)
        filas = fuente.cargar(args.entrada)
        validar_esquema(filas)
        validos, rechazos = limpiar_escenarios(filas)
        elegidos = seleccionar(validos, None if args.todos else args.escenario)
    except (ValueError, FileNotFoundError) as error:
        print(f"Error: {error}")
        return 1

    for escenario in elegidos:
        tandas = ejecutar_escenario(escenario)
        guardar_experimento(escenario, tandas, args.salida)
        r = resumir_experimento(tandas)
        print(f"{escenario.id}: A gana {r['porcentaje_a']}% | "
              f"B gana {r['porcentaje_b']}% | "
              f"promedio de penales: {r['promedio_penales']}")

    guardar_rechazos(rechazos, args.salida)
    print(f"Escenarios rechazados: {len(rechazos)} (ver {args.salida}/rechazos.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())