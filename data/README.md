# Datos

El programa usa dos conjuntos de datos: **tandas de penales reales** (para
analizar y calibrar el modelo) y **planteles** (la entrada que carga quien usa
el simulador).

## 1. Tandas históricas: `tandas_historicas.csv` y `tandas_historicas.json`

### Procedencia

| | |
|---|---|
| Fuente | RSSSF – *Penalty Shootout Statistics at Major Tournaments* |
| URL | https://rsssf.org/miscellaneous/penaltiestour.html |
| Responsable | Roberto Di Maggio y RSSSF (Rec.Sport.Soccer Statistics Foundation) |
| Condiciones de uso | La página autoriza copiar el documento total o parcialmente siempre que se reconozca al autor ("You are free to copy this document in whole or part provided that proper acknowledgement is given to the author"). |
| Última actualización de la fuente | 28/08/2026 |
| Fecha de consulta | 11/11/2026 |
| Control cruzado | Wikipedia, *List of FIFA World Cup penalty shoot-outs* (CC BY-SA 4.0) |

**Cómo se obtuvieron:** se transcribieron a mano las listas de los apartados
*World Cup*, *European Nations' Cup* y *Copa América* (resultado del partido,
marcador de la tanda y cantidad de tiros de cada equipo, que RSSSF indica como
"5 and 4 shots"). El `id` se agregó con el formato `TORNEO-AÑO-NN`.

**Control de la transcripción:** para cada Mundial de 1982 a 2022, la suma de
penales convertidos y pateados coincide exactamente con la tabla por torneo de
Wikipedia (por ejemplo, 2022: 26 convertidos de 41). Para 2026, Wikipedia
(versión consultada) lista 2 tandas y RSSSF 4. Se usó RSSSF, que está
actualizada a agosto de 2026. Además, el programa comprueba que cada marcador
pueda darse con el reglamento (ver "Validaciones" en el README principal), y
las 97 tandas pasan esa comprobación.

### Unidad de análisis

Cada fila es **una tanda de penales** jugada en la fase final de un Mundial
(1982–2026), una Eurocopa (1976–2024) o una Copa América (1993–2024).

- **97 tandas** (39 de Mundiales, 25 de Eurocopas y 33 de Copas América).
- **935 penales** en total. Cada uno es un ensayo convertido/errado, y con ellos
  se estima la efectividad.

### Variables

| variable | tipo | descripción |
|---|---|---|
| id | texto | `MUN`/`EUR`/`CAM` + año + número de orden, ej. `MUN-2022-05` |
| torneo | texto | Mundial, Eurocopa o Copa America |
| anio | entero | año del torneo (Eurocopa 2020 figura como 2020, aunque se jugó en 2021) |
| ronda | texto | F, SF, QF, 3/4 o 1R/2R/3R (eliminatorias previas, según la fuente) |
| ganador / perdedor | texto | selecciones, con los nombres en inglés de la fuente |
| resultado_partido | texto | resultado tras el alargue, ej. `3-3` (siempre empate) |
| goles_ganador / goles_perdedor | entero | penales convertidos en la tanda |
| tiros_ganador / tiros_perdedor | entero | penales pateados (atajados, errados y convertidos) |

Las dos versiones (CSV y JSON) tienen los mismos registros; en el JSON los
números son números y en el CSV llegan como texto. Una prueba comprueba que las
dos lecturas dan exactamente las mismas tandas.

### Limitaciones y sesgos

- **Solo selecciones masculinas en torneos grandes.** No incluye clubes, torneos
  femeninos ni otras confederaciones. La conversión de otros contextos puede ser
  distinta.
- **Muestra chica por grupo.** Hay 97 tandas en total, pero la década de 1970
  tiene 1 y la de 1980, 6. Las diferencias entre décadas deben leerse con sus
  intervalos de confianza.
- **No se sabe siempre quién pateó primero.** Solo se deduce cuando un equipo
  pateó un penal más que el otro (39 tandas). Ese subconjunto está sesgado, porque
  excluye las tandas con igual cantidad de tiros, así que no sirve para medir
  la ventaja de patear primero.
- **No hay datos penal por penal.** No se sabe qué jugador pateó cada penal ni
  en qué orden se erró. Por eso el efecto de la presión no se puede estimar con
  estos datos y en el modelo es un supuesto.
- La fuente es mantenida por voluntarios. Se mitigó con el control cruzado
  descripto arriba.

## 2. Planteles: `planteles.csv` y `planteles.json`

### Procedencia

**Datos sintéticos** creados por el autor (Juan Manuel Rodon, 11/11/2026). Son dos
equipos ficticios, *Atletico Norte* (NOR) y *Deportivo Sur* (SUR), que
representan lo que cargaría un cuerpo técnico con sus propias estadísticas de
entrenamiento. No representan jugadores reales. Se usan para demostrar el
simulador y se pueden reemplazar por datos propios con el mismo formato.

### Unidad de análisis

Cada fila es **un jugador disponible** para la tanda (pateador o arquero).

| variable | tipo | descripción |
|---|---|---|
| codigo_equipo | texto | tres letras mayúsculas, ej. `NOR` |
| equipo | texto | nombre del equipo |
| rol | texto | `pateador` o `arquero` |
| nombre | texto | nombre del jugador (único dentro del equipo) |
| efectividad | 0–1 | probabilidad de convertir contra un arquero promedio (solo pateadores) |
| temple | 0–1 | resistencia a la presión: 1 = no le afecta, 0 = le afecta al máximo |
| factor_atajada | −0.3 a 0.3 | cuántos puntos le baja el arquero a la efectividad del rival (solo arqueros) |

### Valores faltantes (a propósito, para mostrar cómo se tratan)

- `Funes` (NOR) y `Paz` (SUR) no tienen efectividad. Se les asigna la
  **efectividad base calibrada con las tandas reales** y quedan marcados como
  estimados. No se usa cero, porque un dato desconocido no es un jugador que
  nunca convierte.
- `Gimenez` (NOR) y `Paz` (SUR) no tienen temple. Se usa 0.5 (neutro).
- Un arquero sin `factor_atajada` se considera promedio (0).

## 3. Archivo de demostración de la limpieza: `tandas_con_errores.csv`

Tiene 12 registros: 2 válidos y 10 con un error distinto cada uno:

- id repetido;
- id mal formado;
- partido sin empate;
- más goles que tiros;
- marcador imposible según el reglamento;
- id que no corresponde al torneo;
- ronda desconocida;
- equipo vacío;
- valor no numérico;
- año anterior a las tandas.

Sirve para ver cómo el programa los rechaza y registra:

    python -m src.main historico --historico data/tandas_con_errores.csv
