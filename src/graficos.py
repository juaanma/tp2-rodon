"""Gráficos opcionales (requieren matplotlib).

El programa funciona sin matplotlib: si no está instalado, se avisa y se
siguen generando las tablas en CSV/JSON.
"""


def _pyplot():
    try:
        import matplotlib
        matplotlib.use("Agg")  # genera archivos sin abrir ventanas
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        return None


def graficar_distribucion(comparacion, ruta):
    """Barras: proporción de tandas según cantidad total de tiros, real vs
    simulado. Devuelve la ruta o None si no hay matplotlib."""
    plt = _pyplot()
    if plt is None:
        return None
    filas = [f for f in comparacion if f["medida"].startswith("prop_tandas_de_")]
    etiquetas = [f["medida"].split("_")[3] for f in filas]
    posiciones = range(len(filas))
    ancho = 0.4
    figura, eje = plt.subplots(figsize=(8, 4.5))
    eje.bar([p - ancho / 2 for p in posiciones], [f["real"] for f in filas],
            ancho, label="Tandas reales", color="#2a6f97")
    eje.bar([p + ancho / 2 for p in posiciones], [f["simulado"] for f in filas],
            ancho, label="Simulador calibrado", color="#e09f3e")
    eje.set_xticks(list(posiciones), etiquetas)
    eje.set_xlabel("Penales pateados en total en la tanda")
    eje.set_ylabel("Proporción de tandas")
    eje.set_title("Duración de las tandas: datos reales vs. simulación")
    eje.spines[["top", "right"]].set_visible(False)
    eje.legend(frameon=False)
    figura.tight_layout()
    figura.savefig(ruta, dpi=120)
    plt.close(figura)
    return ruta


def graficar_ranking(ranking, ruta, cantidad=10):
    """Barras horizontales con IC 95 % de los mejores órdenes y el peor."""
    plt = _pyplot()
    if plt is None:
        return None
    filas = ranking[:cantidad] + [ranking[-1]]
    etiquetas = [f"#{r['posicion']}: " + " → ".join(r["orden"]) for r in filas]
    valores = [100 * r["prob_ganar"] for r in filas]
    errores = [[100 * (r["prob_ganar"] - r["ic95"][0]) for r in filas],
               [100 * (r["ic95"][1] - r["prob_ganar"]) for r in filas]]
    figura, eje = plt.subplots(figsize=(10, 0.45 * len(filas) + 1.5))
    eje.barh(range(len(filas)), valores, xerr=errores, color="#2a6f97",
             error_kw={"ecolor": "#555555", "capsize": 3})
    eje.set_yticks(range(len(filas)), etiquetas, fontsize=8)
    eje.invert_yaxis()
    eje.set_xlabel("Probabilidad de ganar la tanda (%) con IC 95 %")
    eje.set_title("Órdenes de pateadores: los 10 mejores y el peor")
    eje.set_xlim(min(valores) - 8, max(valores) + 8)
    eje.spines[["top", "right"]].set_visible(False)
    figura.tight_layout()
    figura.savefig(ruta, dpi=120)
    plt.close(figura)
    return ruta
