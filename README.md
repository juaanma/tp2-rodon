# Simulador de tandas de penales

TP2 individual – Programación Orientada a Datos (UCA)
Autor: Juan Manuel Rodon

## Problema, usuario y solución

En una tanda de penales hay mucho azar, y con un solo partido no se puede
sacar ninguna conclusión. Para responder preguntas como "¿cuánto cambia la
probabilidad de ganar si un equipo convierte mejor sus penales?" hay que
repetir la tanda muchas veces con distintos parámetros, y poder reproducir el
resultado.

Lo puede usar un hincha, un estudiante o un analista deportivo que quiera
comparar escenarios. El programa carga escenarios desde un archivo CSV o JSON,
valida sus parámetros, simula muchas tandas con una semilla fija y guarda los
resultados.

## Funcionalidades

- Leer escenarios desde CSV o JSON.
- Validar los escenarios y registrar los rechazados con su motivo.
- Ejecutar un escenario por su id, o todos los válidos.
- Guardar las tandas simuladas, un resumen por escenario y los rechazos.

Alcance de la primera versión: tandas de 5 penales por equipo con muerte
súbita si hay empate; probabilidad fija de convertir para cada equipo.
Queda afuera: diferencias entre jugadores o arqueros, presión, orden de los
pateadores, interfaz web y gráficos.

## Datos

Datos sintéticos: los escenarios fueron inventados por el autor y no
representan estadísticas reales. Las tandas se generan con el módulo `random`.
Fuente, variables, unidad de análisis y limitaciones: ver `data/README.md`.

## Instalación y uso

Requiere Python <Python 3.14.5> (solo biblioteca estándar, no hay dependencias).

```
git clone https://github.com/juaanma/tp2-rodon.git
cd tp2-rodon
```

Ejecutar un escenario:

```
python -m src.main --entrada data/escenarios.csv --escenario ESC-001
```

Ejecutar todos los escenarios válidos desde el JSON:

```
python -m src.main --entrada data/escenarios.json --todos
```

Opcionalmente, `--salida carpeta` cambia la carpeta de resultados
(por defecto, `outputs/`).

Ejecutar las pruebas:

```
python -m unittest
```

## Organización del código

- `src/fuentes.py`: `FuenteDatos` (clase base abstracta), `FuenteCSV` y
  `FuenteJSON`. Ambas devuelven una lista de diccionarios.
- `src/modelos.py`: clase `Escenario`, que valida y convierte los parámetros.
  Usa la expresión regular `ESC-\d{3}` para el id.
- `src/pipeline.py`: validación de esquema, limpieza, simulación, resumen y
  guardado de resultados.
- `src/main.py`: argumentos de consola y coordinación del flujo.
- `tests/`: pruebas con `unittest`.

Flujo: leer → validar esquema → limpiar → simular → resumir y guardar.

## Ejemplo de resultado

```
ESC-001: A gana 59.9% | B gana 40.1% | promedio de penales: 5.69
ESC-002: A gana 50.4% | B gana 49.6% | promedio de penales: 5.77
ESC-003: A gana 100.0% | B gana 0.0% | promedio de penales: 5.0
ESC-004: A gana 51.0% | B gana 49.0% | promedio de penales: 5.52
Escenarios rechazados: 0 (ver outputs/rechazos.csv)
```

Archivos generados en `outputs/` (no se versionan):
`<id>_tandas.csv`, `<id>_resumen.json` y `rechazos.csv`.

## Decisiones de limpieza

- Una fila inválida se rechaza y se registra con número de fila, id y motivo.
- Se rechaza un id que no cumpla `ESC-\d{3}`. La expresión regular solo valida
  el formato del texto, no que el escenario exista.
- Si un id está repetido, se conserva el primero y se rechazan los siguientes.
- Se rechazan probabilidades fuera de [0, 1], repeticiones no positivas y
  semilla faltante (sin semilla no hay reproducibilidad).
- Se rechaza que ambas probabilidades sean 0 o ambas 1, porque la muerte súbita
  nunca desempataría.

## Interpretación y limitaciones

El porcentaje de victorias es una estimación: con 1000 repeticiones el error
estándar ronda los 1,6 puntos porcentuales (el margen al 95% es de unos
±3 puntos), por eso dos equipos parejos dan valores cercanos a 50% pero no
exactamente 50%.

Como las probabilidades son supuestas, los resultados solo valen para esos
supuestos y no sirven para predecir partidos reales. Se asume que cada penal es
independiente y que todos los pateadores tienen la misma probabilidad. La
reproducibilidad está garantizada con la misma versión de Python.