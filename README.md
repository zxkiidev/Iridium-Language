# 💎 Iridium (Ir) Language

> **Next-Gen Backend & AI-Focused Programming Language**

![Iridium Banner](https://img.shields.io/badge/Version-1.4.6-blueviolet?style=for-the-badge)
![Python](https://img.shields.io/badge/Powered%20by-Python%203.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)
![VSCode](https://img.shields.io/badge/Official-Extension-007acc?style=for-the-badge&logo=visual-studio-code&logoColor=white)

Iridium es un lenguaje de programación de **tipado híbrido** diseñado específicamente para la resiliencia en entornos de **Backend e Inteligencia Artificial**. Nace con la misión de simplificar la gestión de datos sensibles y la conexión con modelos de ciencia de datos.

[🌐 Explora la Documentación Oficial](https://zxkiidev.github.io/Iridium-Language/)

---

## 🚀 Características Principales

- **🛡️ Secure Blocks**: Protección nativa de datos sensibles. Las variables dentro de un bloque `secure:` se cifran visualmente en la salida estándar.
- **🧽 Operador Sponge (`~>`)**: Gestión de errores inteligente. Si una operación falla, el sistema asigna un valor de respaldo sin detener la ejecución.
- **🪞 Mirror Log (`>> out`)**: Sistema de depuración técnica que muestra el estado de las variables con un prefijo de sistema limpio.
- **🤖 IA-Ready**: Estructura optimizada para la carga de tensores y datasets mediante bibliotecas integradas (en desarrollo).

---

## 🛠️ Estructura del Proyecto

```text
IridiumProject/
├── src/                # Motor de ejecución (IridiumEngine)
├── docs/               # Documentación web y manuales
├── examples/           # Archivos .iri de ejemplo
└── iridium.bat         # Comando global para Windows
```

<pre class="vditor-reset" placeholder="" contenteditable="true" spellcheck="false"><hr data-block="0"/></pre>

## 💻 Ejemplo de Código

**Fragmento de código**

```python
// Definición de variables
var modelo: string = "Neural-7"
var precision: float = 0.98

// Bloque de seguridad para claves de API
secure:
    var api_key = "AI-77-99-PRO"
    out "Estado de red: Conectado"
    out "Clave: {api_key}" // Salida: Clave: ********
end

// Resiliencia con el operador Sponge
var conexion = network.check() ~> 0.0
```

---

## ⚙️ Instalación

1. **Clona el repositorio:**
   **Bash**

   ```
   git clone [https://github.com/zxkiidev/Iridium-Language.git](https://github.com/zxkiidev/Iridium-Language.git)
   ```

2. **Configura el comando global:**
   Añade la ruta de la carpeta al PATH de Windows o usa el archivo `iridium.bat`.
3. **Instala la extensión de VS Code:**
   Localiza el archivo `.vsix` en la pagina oficial e instálalo manualmente en Visual Studio Code para disfrutar del resaltado de sintaxis.

---

## 👨‍💻 Autor

**Zadquiel Tardío** - [zxkiidev](https://www.google.com/search?q=https://github.com/zxkiidev)
