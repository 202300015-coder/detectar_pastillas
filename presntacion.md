# Presentacion del proyecto: Drug Wizard

## Titulo: Problema que resuelve
### Explicacion:
Muchas personas tienen dificultades para identificar una pastilla cuando no tienen el empaque, la receta o el nombre visible. Este proyecto busca ayudar a reconocer medicamentos a partir de una imagen para reducir errores y mejorar la seguridad.

## Titulo: Que hace la aplicacion
### Explicacion:
La aplicacion recibe una imagen o usa la camara, analiza el color y la forma de la pastilla, y luego compara la informacion con una base de datos de referencias para encontrar coincidencias posibles.

## Titulo: Como funciona la deteccion
### Explicacion:
Primero se prepara la imagen y se busca la zona de interes. Despues se crean mascaras de color con HSV, se detectan contornos y se calculan caracteristicas como area, solidez y proporcion. Con eso se decide si el objeto parece una pastilla.

## Titulo: Herramientas usadas
### Explicacion:
El proyecto usa Python, OpenCV, NumPy, Pandas y archivos JSON/CSV para procesar imagenes y guardar resultados. Tambien puede apoyarse en OCR y APIs externas cuando se necesita mas informacion.

## Titulo: Flujo general del programa
### Explicacion:
El flujo normal es: capturar imagen, analizar color y forma, filtrar candidatos, comparar con referencias y mostrar el resultado final. Si hay datos extra, como texto impreso, se usan para mejorar la coincidencia.

## Titulo: Paso 1 - Captura de la imagen
### Explicacion:
El proceso comienza cuando el usuario toma una foto o usa la camara en vivo. En este paso es importante que la imagen tenga buena luz, enfoque correcto y que la pastilla se vea lo mas centrada posible.

## Titulo: Paso 2 - Preparacion de la imagen
### Explicacion:
Antes de analizar, la imagen se suaviza y se transforma a espacios de color que facilitan la deteccion. Esto ayuda a reducir ruido y a separar mejor el objeto del fondo.

## Titulo: Paso 3 - Busqueda de la zona util
### Explicacion:
El programa intenta encontrar la region donde realmente esta la pastilla. Asi evita analizar todo el fondo de la foto y se enfoca solo en la parte que puede contener informacion importante.

## Titulo: Paso 4 - Deteccion por color
### Explicacion:
Se crean mascaras usando rangos HSV para colores conocidos como rojo, verde, azul, amarillo, blanco o cafe. Con eso el sistema identifica que partes de la imagen coinciden con colores de pastillas.

## Titulo: Paso 5 - Deteccion por forma
### Explicacion:
Ademas del color, el programa revisa contornos, area, solidez y proporcion. Esto permite distinguir entre una pastilla redonda, ovalada o una forma que no corresponde a un medicamento.

## Titulo: Paso 6 - Filtrado de candidatos
### Explicacion:
No todo lo que aparece en la imagen se considera una pastilla. El sistema aplica reglas para descartar objetos muy pequenos, demasiado grandes, poco compactos o que no encajan con las caracteristicas esperadas.

## Titulo: Paso 7 - Combinacion de resultados
### Explicacion:
Cuando el sistema ya encontro candidatos, junta la informacion de color, forma y, si existe, texto impreso. Esa combinacion mejora la precision de la identificacion final.

## Titulo: Paso 8 - Comparacion con referencias
### Explicacion:
El resultado se contrasta con referencias guardadas en archivos como CSV o con imagenes calibradas. Asi se obtiene una coincidencia probable y se puede mostrar un resultado mas util para el usuario.

## Titulo: Paso 9 - Visualizacion del resultado
### Explicacion:
Finalmente, el programa dibuja recuadros, etiquetas y paneles de depuracion para mostrar lo detectado. Esto ayuda a entender por que una pastilla fue reconocida de cierta manera.

## Titulo: Paso 10 - Ajuste y calibracion
### Explicacion:
Si la deteccion no es precisa, se ajustan los rangos de color, los umbrales geometricos o los parametros de filtrado. Esta parte es clave para mejorar la calidad del sistema con distintas imagenes y condiciones.

## Titulo: Limitaciones del proceso
### Explicacion:
El sistema depende mucho de la iluminacion, el angulo de la foto y la calidad de la base de datos. Si la pastilla esta borrosa o el fondo es muy parecido al color del medicamento, la deteccion puede fallar.

## Titulo: Cierre
### Explicacion:
El proceso completo va desde capturar la imagen hasta mostrar una posible identificacion. La idea del proyecto es convertir una foto en una ayuda rapida para reconocer pastillas de forma mas segura.




