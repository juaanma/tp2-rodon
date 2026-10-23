# Datos

## Procedencia
Todos los datos de este trabajo son sintéticos. Los escenarios (probabilidades
de convertir un penal, repeticiones y semilla) fueron inventados por el autor
para ilustrar el funcionamiento del programa y no representan estadísticas
reales de ningún equipo ni jugador.

Autor: Juan Manuel Rodon. Fecha de creación: 22/10/2026.

## Unidad de análisis
Cada fila de los archivos de escenarios es un escenario de simulación.

## Variables
- id: identificador del escenario, formato ESC-001
- prob_gol_a: probabilidad (0 a 1) de que el equipo A convierta un penal
- prob_gol_b: probabilidad (0 a 1) de que el equipo B convierta un penal
- repeticiones: cantidad de tandas a simular
- semilla: número entero para reproducir los resultados

## Limitaciones
- Las probabilidades son supuestas, por lo que los resultados solo valen
  para esos supuestos.
- Se asume que cada penal es independiente y que todos los pateadores de un
  equipo tienen la misma probabilidad de convertir.

## Archivo de demostración de la limpieza
`escenarios_con_errores.csv` contiene 8 filas: 2 válidas y 6 con errores
distintos (id mal formado, id repetido, probabilidad fuera de rango,
repeticiones en cero, semilla faltante y valor no numérico). Se usa para
mostrar cómo el programa los rechaza y los registra.

## Observaciones: tandas simuladas

Las observaciones del trabajo son las tandas que genera la simulación. No se
versionan completas (la carpeta `outputs/` está en el `.gitignore`), pero se
regeneran de forma idéntica ejecutando el programa con la misma semilla:

    python -m src.main --entrada data/escenarios.csv --todos

Cada escenario produce entre 100 y 1000 observaciones (una por repetición).
Con los escenarios de ejemplo se generan 3100 tandas en total.

Unidad de análisis de las tandas: cada fila es una tanda de penales simulada.

| variable | tipo | descripción |
|---|---|---|
| id_escenario | texto | escenario al que pertenece la tanda |
| nro_tanda | entero | número de repetición dentro del escenario |
| goles_a | entero | penales convertidos por el equipo A |
| goles_b | entero | penales convertidos por el equipo B |
| penales_pateados | entero | penales por equipo (5 más los de muerte súbita) |
| ganador | texto | A o B (nunca hay empate) |

### Muestra incluida en el repositorio

`muestra_tandas.csv` contiene 100 tandas del escenario ESC-001 (semilla 42),
para poder ver el formato de las observaciones sin ejecutar el programa.



