
Un pequeño programa en python para ayudar con la traducción de mangas en japones usando [manga-ocr](https://github.com/kha-white/manga-ocr)


# Instalar

Para instalarlo primero se necesita tener instalado el [gestor de paquetes para python uv](https://github.com/astral-sh/uv?tab=readme-ov-file#installation)

Una vez instalado ejecutar los siguientes comandos en orden:

```
git clone https://github.com/Calaverd/Gomata.git
cd Gomata
uv run main-gui.py
```

uv en la primera ejecución creara un entorno virtual y bajara las dependencias necesarias para correr el proyecto.

# Uso

Se puede cargar una imagen o todas las imagenes en una carpeta con el menu de archivo. 
Una vez se ha cargado el archivo, al mantener presionado click izquierdo el mouse y arrastrandolo, se pueden crear selecciones
en el areas.
Las selecciones pueden ser movidas cuando se presiona y arrastra con el click izquierdo en el centro de las mismas.
Las selecciones pueden modificar su tamaño cuando se presiona y arrastra con el click izquierdo en
las esquinas.
Las selecciones pueden ser borradas al dar click sobre ellas y después apretar "Ctrl + X"

Una vez una seleccion es creada, esta pasara a ser procesada con manga-ocr y después se usara el traductor de google
para dar una traducción por maquina apropiada.

## Atajos de teclado 

 * **Ctrl + O** Abrir un archivo gomata (gmt) con información de traducción.
 * **Ctrl + S** Guardar los cambios actuales a un nuevo archivo gmt o al ultimo archivo guardado
 * **Ctrl + F** Agregar todas las imagenes en una carpeta.
 * **Ctrl + I** Agregar una unica imagen 
 * **Ctrl + Scroll** Hacer zoom en una región de la imagen.
 * **Ctrl + X** La seleccion sobre la imagen activa sera borrada, solo funciona mientras la imagen este en foco.

# Detalles y observaciones.

Manga-ocr puede aveces no reconocer los caracteres en la imagen de forma apropiada, y si el texto esta muy amontonado.

# Roadmap

 * Mejorar como se muestra el texto traduccido sobre las selecciones.
 * Agregar boton para refrescar los caracteres selecionados y otro para la traducción por maquina.
 * Permitir algunas operaciones de edición basicas para reducir el indice de error en el reconocimiento de texto.
 * Permitir agregar anotaciones sobre el texto seleccionado.

# Iconos

Los iconos fueron tomados de [Tabler Icons](https://tablericons.com/)