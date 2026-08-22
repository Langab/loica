# Arma propuesta.html a partir de propuesta.src.html inyectando v1.js y v2.js
# en línea (el artefacto no puede pedir archivos externos).
import pathlib, re
S = pathlib.Path(__file__).parent
src = (S / "propuesta.src.html").read_text(encoding="utf-8")
for nombre in ["v1.js", "v2.js"]:
    js = (S / nombre).read_text(encoding="utf-8").replace("</script", "<\\/script")
    src = src.replace(f"<!-- INLINE:{nombre} -->", f"<script>\n{js}\n</script>")
(S / "propuesta.html").write_text(src, encoding="utf-8")
print("propuesta.html:", len(src), "bytes")
