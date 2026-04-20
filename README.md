# Logica de `detectar_pastillas.ipynb`

Este README documenta solo la logica del notebook `detectar_pastillas.ipynb`.

## 1. Flujo general

En cada frame de camara el pipeline hace:
1. Define una ROI central.
2. Estima el color del fondo (papel) con las 4 esquinas de la ROI.
3. Segmenta el objeto por distancia de color al fondo (en LAB).
4. Filtra contornos y elige el candidato principal.
5. Clasifica forma.
6. Clasifica color (mono o bicolor).
7. Asigna marca segun reglas.
8. Dibuja resultados en overlay.

## 2. Parametros clave

- `CAM_INDEX`: camara a usar.
- `ROI_W`, `ROI_H`: tamano relativo de ROI.
- `MIN_AREA_FLOOR`, `MIN_AREA_RATIO`: piso de area para descartar ruido.
- `INTERNAL_EDGE_CANNY_LOW/HIGH`: sensibilidad de bordes internos.
- `INTERNAL_EDGE_DENSITY_THRESHOLD`: umbral para activar logica bicolor.
- `SHAPE_NAMES`: `desconocida`, `circular`, `capleta`, `pastilla`.

## 3. Segmentacion del objeto

1. Convierte ROI a LAB.
2. Calcula la distancia por pixel entre ROI y el color estimado de papel.
3. Aplica Otsu + ajuste y mascara binaria.
4. Limpia con morfologia (`OPEN`, `CLOSE`).
5. Erosiona (`mask_sep`) para separar objetos cercanos.

## 4. Seleccion de contorno principal

Los contornos se filtran por:
- area minima,
- relacion de relleno,
- aspecto extremo,
- toque de borde (para evitar blobs enormes pegados al marco).

Si hay dos contornos principales compatibles, los une en un solo objeto (`convexHull`) para manejar pastillas partidas visualmente.

Si no hay fusion, elige el mejor por score:
- mayor area normalizada,
- cercania al centro,
- penalizacion por tamano excesivo.

## 5. Clasificacion de forma

Sobre el contorno final calcula:
- `circularity = 4*pi*area / perimetro^2`
- `aspect` con `minAreaRect`.

Con reglas geometricas asigna:
- `circular`
- `capleta`
- `pastilla`
- `desconocida`

Tambien aplica ajustes de correccion para reducir cambios inestables entre clases.

## 6. Clasificacion de color

1. Convierte ROI a HSV.
2. Toma mascara interna del objeto para evitar contaminar con bordes.
3. Clasifica pixeles con `classify_hsv_pixels()` usando `COLOR_RANGOS` y `COLOR_ORDER`.
4. Obtiene color dominante por conteo.
5. Usa `classify_hsv_scalar()` como fallback robusto con el color central.

Resultado:
- `primary_color`
- `secondary_color` (si aplica)
- `is_bicolor`

## 7. Deteccion bicolor

Solo intenta bicolor cuando:
- la forma es `pastilla` o `capleta`,
- y el objeto tiene aspecto alargado o suficiente borde interno.

Proceso:
1. Divide la mascara interna en 2 mitades.
2. Clasifica color por cada mitad.
3. Verifica proporciones minimas por lado.
4. Si ambas mitades son validas y de colores distintos, marca bicolor y fuerza `shape_label = 'pastilla'`.

## 8. Reglas de marca

Funcion: `infer_brand(shape_label, primary_color, secondary_color, is_bicolor)`.

Reglas actuales:
- `pastilla` + `naranja/amarillo` -> `Teva Pharmaceuticals USA`
- `pastilla` + `azul/naranja` -> `Alembic Pharmaceuticals`
- `negro/amarillo` -> `Zydus Pharmaceuticals`
- `circular` + `rojo` -> `Glaxo SmithKline`
- `circular` + `azul` -> `Glaxo SmithKline`
- `capleta` + `azul` -> `Glaxo SmithKline`
- `capleta` + `cafe` -> `Heritage Pharmaceuticals`
- `circular` + (`cafe` o `rojo` o `naranja`) -> `Cipla USA Inc.`

Nota: la regla `circular + rojo -> Glaxo SmithKline` esta antes que la regla general de `Cipla` para resolver conflicto.

## 9. Salida visual en tiempo real

En `roi_result` se dibuja:
- contorno y caja del objeto,
- `color | forma | tamano`,
- `Marca: ...` (si hay match),
- metricas (`H,S,V`, densidad de borde interno y relacion de area).

Ventanas de debug activas:
- `camera`
- `roi_result`

Se sale del loop con tecla `q`.
