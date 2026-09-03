/* ============================================================
   LOICA — el mapa, compartido por cinco páginas
   ------------------------------------------------------------
   Vivía dentro de mapa.html. Salió a este archivo cuando fiestas, teatro,
   música y charlas pasaron a tener pestaña propia: cada una es ESTE mismo
   mapa con la categoría fija, y cuatro copias de 800 líneas se habrían
   desalineado en la primera corrección.

   Las dos constantes las declara cada página en un <script> ANTES de cargar
   este archivo:
     const PAGINA = "fiestas.html", CATEGORIA_FIJA = "fiesta";
   PAGINA es su propio nombre de archivo (para la barra y para volver de la
   ficha) y CATEGORIA_FIJA la categoría que muestra, o null en el mapa
   general. Se leen con typeof para que una página que olvide declararlas se
   comporte como el mapa general en vez de morir en la primera línea.
   Lleva ?v=N como loica.js: si se toca, se sube el número en las cinco
   páginas (ver README, "sube el cache-buster").
   ============================================================ */
const PAGINA_MAPA = typeof PAGINA === "string" ? PAGINA : "mapa.html";
const CAT_FIJA = typeof CATEGORIA_FIJA === "string" && CATEGORIAS[CATEGORIA_FIJA]
  ? CATEGORIA_FIJA : null;
// Quién atiende esta página: el animal guía de la categoría fija. En el mapa
// general es null y atiende la Loica, que atiende a todos.
const QUIEN_FIJO = CAT_FIJA ? CATEGORIAS[CAT_FIJA] : null;

// filtroCat arranca en la categoría fija y nunca la suelta: así pintarEstado
// y el disco de "quién atiende" muestran al animal sin ningún caso especial.
let EVENTOS = [], filtroCat = CAT_FIJA, soloGratis = false, cuando = "todo", publicoFiltro = null;
let busqueda = "", filtroSub = null;
let listaActual = [], seleccionado = null, mapa = null, hayMapa = false;

pintarBarra(PAGINA_MAPA);
pintarCabezaCat();

/* Teselas CARTO en vez de OpenStreetMap crudo: el estilo por defecto de OSM
   mete más de 25 íconos propios en pantalla y el producto pierde contra su
   propio fondo. Además hay versión oscura, y la marca dice que el modo oscuro
   es de primera clase porque la app se usa de noche. */
const TESELAS = {
  claro:"https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png",
  claroEtiquetas:"https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
  oscuro:"https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
  oscuroEtiquetas:"https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png",
};
// Las teselas siguen al tema elegido y NADA más. Antes miraban también el
// `prefers-color-scheme` del aparato, y desde que el sitio arranca claro por
// defecto eso dejaba el mapa negro dentro de una página crema.
const esOscuro = () => document.documentElement.dataset.tema === "oscuro";

const urlesTeselas = clave => ["a","b","c"].map(s =>
  TESELAS[clave].replace("{s}", s).replace("{r}", devicePixelRatio > 1.5 ? "@2x" : ""));

function estiloMapa(){
  const t = esOscuro() ? ["oscuro","oscuroEtiquetas"] : ["claro","claroEtiquetas"];
  return {version:8,
    sources:{
      base:{type:"raster", tiles:urlesTeselas(t[0]), tileSize:256,
            attribution:'© OpenStreetMap © CARTO'},
      etiquetas:{type:"raster", tiles:urlesTeselas(t[1]), tileSize:256},
    },
    layers:[{id:"base",type:"raster",source:"base"},
            {id:"etiquetas",type:"raster",source:"etiquetas"}]};
}

/* El mapa se crea desde el ARRANQUE, después de pintar la cabecera, y no al
   cargar el script. MapLibre mide el contenedor al nacer: si nace con la
   cabecera a medio pintar (58 px) y después la cabecera crece a 150, el
   primer cuadro de teselas queda calculado para el tamaño viejo y en celular
   quedaba una banda crema de ~60 px bajo los filtros, que un resize() no
   borraba. Con la cabecera lista antes, nace del tamaño definitivo.

   Si el aparato no tiene WebGL, MapLibre tira una excepción y antes se caía
   la página entera: quedaba una pantalla en blanco sin lista y sin
   explicación. Pasa en iPhone viejos y con la aceleración por hardware
   apagada. Ahora la lista sigue siendo un producto completo. */
function crearMapa(){
try{
  mapa = new maplibregl.Map({
    container:"mapa", style:estiloMapa(),
    center:[-70.645,-33.437], zoom:12.2, attributionControl:{compact:true}
  });
  hayMapa = true;
}catch(e){
  document.getElementById("mapa").innerHTML =
    `<div class="vacio" style="padding-top:var(--e-12)">${cuerpo("loica","var(--acento)",96,{pose:"durmiendo"})}
     <p><b>Este navegador no puede dibujar el mapa</b><br>
     La lista de abajo funciona igual.</p></div>`;
  return;
}
{
  mapa.addControl(new maplibregl.NavigationControl({showCompass:false}), "top-left");

  // El mapa nace antes de que su caja tenga tamaño final. Se compara el
  // tamaño anterior porque redimensionar vuelve a disparar al observador.
  (() => {
    const caja = document.getElementById("mapa");
    let ancho = 0, alto = 0;
    new ResizeObserver(() => {
      if(caja.clientWidth === ancho && caja.clientHeight === alto) return;
      ancho = caja.clientWidth; alto = caja.clientHeight;
      mapa.resize();
    }).observe(caja);
  })();

  mapa.on("error", e => {
    if(String(e.error?.message || "").match(/tile|fetch|network/i))
      avisar(IDIOMA === "en" ? "Map is loading slowly — the list still works"
           : IDIOMA === "pt" ? "O mapa está lento — a lista continua funcionando"
           : "El mapa va lento — la lista igual funciona");
  });
  montarEventosDelMapa();
}
}

function avisar(texto, quien = "loica"){
  const caja = document.getElementById("aviso");
  caja.innerHTML = `${carita(quien,"var(--acento)",22)} <span>${escapar(texto)}</span>`;
  caja.hidden = false;
}

/* ============================================================
   PINES: capa de símbolos, un pin-animal por evento, no 288 divs
   ------------------------------------------------------------
   Antes cada evento era un <div> con un SVG adentro. 288 marcadores DOM
   sobre un canvas WebGL significan 288 elementos reposicionados en cada
   cuadro mientras arrastras: en celular el mapa se movía a tirones. Ahora
   los pines viven dentro del motor del mapa.

   Sin agrupación, a propósito: cada evento es SIEMPRE su propio pin,
   aunque en el centro se encimen (icon-allow-overlap). Al filtrar,
   refrescar() manda la lista nueva con setData() y los pines filtrados
   desaparecen. Para que el traslape de lejos moleste menos, el pin crece
   con el zoom, y los gratis se dibujan encima del resto.

   Los íconos se registran ANTES de que exista la capa que los usa. Antes se
   dibujaban a pedido, escuchando `styleimagemissing`, y eso no puede
   funcionar: MapLibre dispara el evento y vuelve a leer la imagen en la línea
   siguiente, sin ceder el turno. Como pasar un SVG a mapa de bits obliga a
   esperar el onload de una Image, el oyente nunca llegaba a tiempo y la
   consola juntaba un aviso "could not be loaded" por categoría —veinte en una
   carga común—. Los pines igual aparecían un tic después, así que era ruido,
   pero ruido que tapa los avisos de verdad.
   ============================================================ */
const ESCALA_PIN = 2;

function svgAImagen(svg, ancho, alto){
  return new Promise(resolve => {
    const img = new Image();
    img.onload = () => {
      const lienzo = document.createElement("canvas");
      lienzo.width = ancho * ESCALA_PIN; lienzo.height = alto * ESCALA_PIN;
      const ctx = lienzo.getContext("2d");
      ctx.drawImage(img, 0, 0, lienzo.width, lienzo.height);
      resolve(ctx.getImageData(0, 0, lienzo.width, lienzo.height));
    };
    img.onerror = () => resolve(null);
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  });
}

/* El disco interior del pin es crema SIEMPRE (también de noche), así que acá
   la tinta va fija en azul: si usara var(--contorno), en modo oscuro sería
   crema sobre crema y la carita perdería el contorno. */
const TINTA_PIN = "#1E2A4A";

function svgPin(clave, gratis){
  const info = CATEGORIAS[clave] || CATEGORIAS.otros;
  const tono = gratis ? "#0E8757" : info.hex;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 42" width="34" height="42">
    <path d="M17 1C8.7 1 2 7.7 2 16c0 10.5 12.6 23 14.1 24.4.5.5 1.3.5 1.8 0C19.4 39 32 26.5 32 16 32 7.7 25.3 1 17 1z"
          fill="${tono}" stroke="${TINTA_PIN}" stroke-width="2.5"/>
    <circle cx="17" cy="15.6" r="11" fill="#FAF3E7"/>
    <g transform="translate(4.4 3)scale(1.05)">${CARITAS[info.mascota](tono, TINTA_PIN, "posada", true)}</g>
  </svg>`;
}

function datosGeo(lista){
  return {type:"FeatureCollection", features: lista
    .filter(ev => ev.lat != null)
    .map(ev => ({type:"Feature",
      geometry:{type:"Point", coordinates:[ev.lon, ev.lat]},
      properties:{id:ev.id, cat:CATEGORIAS[ev.categoria] ? ev.categoria : "otros",
                  gratis:!!ev.gratis}}))};
}

/* Las 13 categorías por dos (pagado y gratis) son 26 dibujos de 34×42 que se
   generan una sola vez, en paralelo, mientras todavía viaja eventos.json. No
   se guarda la promesa: cambiar de tema puede llevarse las imágenes junto con
   el estilo, y hasImage() vuelve a decir la verdad después de cada setStyle. */
function prepararPines(){
  return Promise.all(Object.keys(CATEGORIAS).flatMap(clave =>
    [false, true].map(async gratis => {
      const id = `pin-${clave}${gratis ? "-g" : ""}`;
      if(mapa.hasImage(id)) return;
      const datos = await svgAImagen(svgPin(clave, gratis), 34, 42);
      if(datos && !mapa.hasImage(id)) mapa.addImage(id, datos, {pixelRatio:ESCALA_PIN});
    })));
}

/* Montar la capa pasó a ser asíncrono, así que `load` y `styledata` pueden
   entrar los dos mientras se dibujan los íconos: sin esta tranca se agregaba
   la fuente dos veces y MapLibre tiraba error. */
let montandoCapas = false;

async function montarCapas(){
  if(!hayMapa || montandoCapas || mapa.getSource("eventos")) return;
  montandoCapas = true;
  try{
    await prepararPines();
    if(mapa.getSource("eventos")) return;
    mapa.addSource("eventos", {type:"geojson", data:datosGeo(listaActual)});
    mapa.addLayer({
      id:"pines", type:"symbol", source:"eventos",
      layout:{
        "icon-image":["concat","pin-",["get","cat"],["case",["get","gratis"],"-g",""]],
        // De lejos chico, de cerca pleno. Antes iba de .4 a .55 sobre un
        // dibujo de 34×42: un pin de 15 px con una carita de 11 que no se leía
        // (la dirección visual pide 28 px de carita). Ahora al zoom inicial el
        // pin mide ~25 px y la carita ~19, y desde el zoom 15 la carita llega a
        // los 28 del contrato. El traslape del centro a zoom bajo se ordena
        // con symbol-sort-key: gratis encima.
        "icon-size":["interpolate",["linear"],["zoom"],11,.62,13,.85,15,1.05,17,1.2],
        "icon-anchor":"bottom",
        "icon-allow-overlap":true, "icon-ignore-placement":true,
        // Con allow-overlap, la clave más alta se dibuja encima: gratis gana
        "symbol-sort-key":["case",["get","gratis"],1,0],
      },
    });
    // El toque sobre un pin se resuelve en el manejador general del mapa (al
    // final del archivo), con una caja de tolerancia alrededor del dedo.
    mapa.on("mouseenter", "pines", () => mapa.getCanvas().style.cursor = "pointer");
    mapa.on("mouseleave", "pines", () => mapa.getCanvas().style.cursor = "");
  }catch(e){
    /* Esperar los íconos abre una rendija que antes no existía: si el tema
       cambia justo ahí, el estilo se rehace y addSource cae con "Style is not
       done loading". No se hace nada acá a propósito —el styledata del estilo
       nuevo vuelve a llamar a montarCapas y la capa queda igual—. */
  } finally { montandoCapas = false; }
}

function montarEventosDelMapa(){
  mapa.on("load", montarCapas);
  // Cambiar de tema reconstruye el estilo y con él se van fuentes y capas
  mapa.on("styledata", () => { if(!mapa.getSource("eventos")) montarCapas(); });
  new MutationObserver(() => mapa.setStyle(estiloMapa()))
    .observe(document.documentElement, {attributes:true, attributeFilter:["data-tema"]});
}

/* ---------- FILTROS ----------

   El orden de la lista NO es el del archivo. `eventos.json` viene ordenado por
   fecha de inicio, que es lo correcto para "Todos" y lo peor posible para
   "Hoy": una muestra que abrió en abril de 2025 tiene una fecha de inicio muy
   anterior a la del concierto de esta noche, así que encabezaba la lista y lo
   que de verdad pasa hoy quedaba enterrado treinta tarjetas más abajo. Con
   Arte apretado, las 36 temporadas iban antes que los 4 eventos del día.

   Así que lo que ya está corriendo va al final: primero lo que EMPIEZA dentro
   del rango, en orden de hora, y después lo que se puede ir a ver igual. */
const ordenarParaLeer = lista => lista.slice().sort((a, b) =>
  (enCartelera(a) ? 1 : 0) - (enCartelera(b) ? 1 : 0)
  || new Date(a.inicio) - new Date(b.inicio));

const visibles = () => ordenarParaLeer(EVENTOS.filter(ev =>
  (!soloGratis || ev.gratis) &&
  (!filtroCat || ev.categoria === filtroCat) &&
  (!filtroSub || ev.subcategoria === filtroSub) &&
  (!publicoFiltro || ev.publico === publicoFiltro) &&
  coincideBusqueda(ev, busqueda) &&
  sesionEnRango(ev, cuando)));

/* Los mismos eventos pero ignorando UN filtro, para poder contar cuántos
   quedarían si lo tocaras. Sin esto los números de los chips se cuentan sobre
   la base entera y mienten: un "Reggaetón 40" que al tocarlo muestra 3 es peor
   que no poner número. */
const visiblesSalvo = salvo => EVENTOS.filter(ev =>
  (!soloGratis || ev.gratis) &&
  (salvo === "cat" || !filtroCat || ev.categoria === filtroCat) &&
  (salvo === "sub" || !filtroSub || ev.subcategoria === filtroSub) &&
  (!publicoFiltro || ev.publico === publicoFiltro) &&
  coincideBusqueda(ev, busqueda) &&
  sesionEnRango(ev, cuando));

// En una página de categoría, la categoría no cuenta como filtro: es la
// página. Si contara, "Limpiar" estaría siempre prendido sin nada que limpiar.
const hayFiltros = () => busqueda || (filtroCat && filtroCat !== CAT_FIJA) || filtroSub
  || soloGratis || publicoFiltro || cuando !== "todo";

function limpiarFiltros(){
  busqueda = ""; filtroCat = CAT_FIJA; filtroSub = null;
  soloGratis = false; publicoFiltro = null; cuando = "todo";
  const campo = document.getElementById("buscar");
  campo.value = "";
  document.getElementById("riel-fecha").classList.remove("buscando");
  sincronizarBuscador();
}

function pintarFiltros(){
  /* --- Riel 1: cuándo. Una sola respuesta, por eso es segmentado ---
     "Hoy" y "este finde" dejaban un hoyo: un martes, el finde son cuatro
     días más y no había forma de preguntar por mañana. */
  const fechas = document.getElementById("fechas");
  fechas.innerHTML = "";
  fechas.setAttribute("aria-label", t("filtrosCuando"));
  [["todo", t("cuandoLargo").todo], ["hoy", t("hoy")], ["manana", t("manana")],
   ["semana", t("semana")], ["finde", t("finde")]].forEach(([clave, etiqueta]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = etiqueta;
    b.setAttribute("aria-pressed", cuando === clave);
    b.onclick = e => {
      cuando = clave;
      pintarFiltros(); refrescar();
      volarDesde(e.currentTarget);
    };
    fechas.appendChild(b);
  });
  document.getElementById("cuenta-rango").innerHTML =
    `${carita("loica","var(--acento)",22)} ${escapar(t("cuandoLargo")[cuando])}`;

  /* --- Riel 2: precio, público y tipo. Se combinan entre sí --- */
  const cont = document.getElementById("filtros");
  cont.innerHTML = "";
  cont.setAttribute("aria-label", t("filtrosRapidos") + " · " + t("filtrosTipo"));

  const agregar = (contenido, activo, alPulsar, clase="") => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip " + clase;
    b.innerHTML = contenido;
    b.setAttribute("aria-pressed", activo);
    b.onclick = e => { alPulsar(); pintarFiltros(); refrescar(); volarDesde(e.currentTarget); };
    cont.appendChild(b);
    return b;
  };

  // El Degú es la mascota de lo gratis: el filtro estrella tiene cara propia.
  // Era el Pudú, que se quedó con el aire libre cuando entró el Guarén.
  agregar(`${carita("degu", soloGratis ? "#fff" : "#2E7D5B", 22)} ${t("gratis")}`,
          soloGratis, () => soloGratis = !soloGratis, "es-gratis");
  // Público: responde "¿puedo llevar a mi hijo?" y "¿es de mayores?"
  agregar(`${carita("pudu", publicoFiltro === "ninos" ? "#fff" : "#0E8757", 22)} ${t("ninos")}`,
          publicoFiltro === "ninos",
          () => publicoFiltro = publicoFiltro === "ninos" ? null : "ninos");
  agregar(`${carita("culpeo", publicoFiltro === "adultos" ? "#fff" : "#7A3FE0", 22)} ${t("mas18")}`,
          publicoFiltro === "adultos",
          () => publicoFiltro = publicoFiltro === "adultos" ? null : "adultos");

  /* El separador entre "precio y público" y lo que viene después: son dos
     preguntas distintas metidas en un solo riel para ahorrar alto. */
  const separador = () => {
    const sep = document.createElement("div");
    sep.className = "separa-chips";
    sep.setAttribute("aria-hidden","true");
    cont.appendChild(sep);
  };

  if(CAT_FIJA){
    /* Página de UNA categoría: el riel de animales no tiene sentido —serían
       once chips para elegir lo que ya está elegido— y su lugar lo toman los
       géneros de esa categoría, que en el mapa general viven bajo el contador
       (pintarAfinar). Arriba se ven sin abrir la hoja, que en un teléfono es
       la diferencia entre encontrar el chip de cumbia y no saber que existe.
       Mismo piso y mismo orden que abajo: sale todo de opcionesDeSubcategoria. */
    const {base, cuantos, opciones} = opcionesDeSubcategoria();
    if(opciones.length >= 2){
      separador();
      const conCuenta = (texto, n) => `${escapar(texto)} <span class="cuenta">${n}</span>`;
      agregar(conCuenta(t("afinarTodo"), base.length), !filtroSub, () => filtroSub = null);
      opciones.forEach(s => agregar(conCuenta(subcat(s), cuantos[s]), filtroSub === s,
        () => filtroSub = filtroSub === s ? null : s));
    }
    pintarAfinar();
    pintarEstado();
    return;
  }

  separador();

  /* Las categorías van ordenadas por CUÁNTAS HAY, de mayor a menor, y ya no
     alfabéticamente. El orden alfabético dejaba "Aire libre" (9 eventos) de
     primero y "Deporte" (1.071) en el sexto lugar, detrás del borde de la
     pantalla: el riel se desplaza de lado y en un teléfono se ven cuatro chips.
     Ordenar por volumen pone al alcance del pulgar lo que de verdad hay esta
     semana. El desempate sigue siendo alfabético para que el orden no baile
     entre dos categorías empatadas. */
  const cuantosPorCat = {};
  visiblesSalvo("cat").forEach(e => cuantosPorCat[e.categoria] = (cuantosPorCat[e.categoria] || 0) + 1);
  [...new Set(EVENTOS.map(e => e.categoria))]
    .sort((a,b) => (cuantosPorCat[b] || 0) - (cuantosPorCat[a] || 0)
                || cat(a)[IDIOMA].localeCompare(cat(b)[IDIOMA]))
    .forEach(c => {
      const info = cat(c);
      agregar(`${carita(info.mascota, filtroCat === c ? "#fff" : info.hex, 22)} ${info[IDIOMA]}`,
              filtroCat === c, () => {
                // Soltar o cambiar de categoría BORRA la subcategoría. Sin esto,
                // filtrar Fiestas → Reggaetón y después tocar Teatro deja un
                // `filtroSub` colgado que no existe en teatro: la pantalla queda
                // en cero y parece que la app se rompió.
                filtroCat = filtroCat === c ? null : c;
                filtroSub = null;
              });
    });

  pintarAfinar();
  pintarEstado();
}

/* ---------- AFINAR: subcategorías y tamaño, dentro del panel ----------
   Van bajo el contador y no en la cabecera: es donde los pidió el dueño, y la
   cabecera ya tiene dos rieles. Las opciones salen de los DATOS y no de una
   lista escrita a mano, así que si el clasificador estrena un género mañana
   aparece solo. */

/* Un chip por subcategoría es una elección solo si hay algo que elegir. Bajo
   este piso el chip ocupa lugar y no lleva a ninguna parte: música tiene nueve
   géneros y cuatro de ellos son de un evento. Se muestran los que tengan 3 o
   más, y si eso deja menos de dos opciones no se dibuja la fila entera.
   Tres y no dos: con dos, "Pop 2" ocupa el mismo ancho que "Rock 106" y sugiere
   que son dos escenas comparables. */
const MIN_SUB = 3;

/* Los géneros que se pueden elegir dentro de la categoría puesta, con cuántos
   hay de cada uno. Lo usan la fila de afinar del panel (mapa general) y el
   riel de la cabecera (páginas de una categoría), y por eso está aparte: los
   dos tienen que contar igual o un mismo chip diría dos números. */
function opcionesDeSubcategoria(){
  if(!filtroCat) return {base:[], cuantos:{}, opciones:[]};
  const base = visiblesSalvo("sub").filter(ev => ev.categoria === filtroCat);
  const cuantos = {};
  base.forEach(ev => { if(ev.subcategoria) cuantos[ev.subcategoria] = (cuantos[ev.subcategoria] || 0) + 1; });
  // El que está puesto se dibuja siempre, aunque su cuenta caiga bajo el
  // piso al combinarse con otros filtros: si no, el chip que acabas de tocar
  // desaparece y no hay forma de soltarlo.
  const opciones = Object.keys(cuantos)
    .filter(s => cuantos[s] >= MIN_SUB || s === filtroSub)
    .sort((a,b) => cuantos[b] - cuantos[a] || subcat(a).localeCompare(subcat(b)));
  return {base, cuantos, opciones};
}

function pintarAfinar(){
  const caja = document.getElementById("afinar");
  caja.innerHTML = "";

  const fila = (etiqueta, ariaEtiqueta) => {
    const f = document.createElement("div");
    f.className = "afinar-fila";
    f.setAttribute("role", "group");
    f.setAttribute("aria-label", ariaEtiqueta);
    if(etiqueta){
      const et = document.createElement("span");
      et.className = "afinar-et";
      et.textContent = etiqueta;
      et.setAttribute("aria-hidden", "true");
      f.appendChild(et);
    }
    caja.appendChild(f);
    return f;
  };
  const chip = (fila, texto, cuenta, activo, alPulsar, titulo="") => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.innerHTML = escapar(texto)
      + (cuenta === null ? "" : ` <span class="cuenta">${cuenta}</span>`);
    b.setAttribute("aria-pressed", activo);
    if(titulo) b.title = titulo;
    b.onclick = e => { alPulsar(); pintarFiltros(); refrescar(); volarDesde(e.currentTarget); };
    fila.appendChild(b);
  };

  // --- Subcategorías: solo con una categoría elegida, y solo en el mapa
  //     general. En las páginas de una categoría viven en la cabecera.
  if(filtroCat && !CAT_FIJA){
    const {base, cuantos, opciones} = opcionesDeSubcategoria();

    if(opciones.length >= 2){
      const f = fila(t("filtrosAfinar"), t("filtrosAfinar"));
      chip(f, t("afinarTodo"), base.length, !filtroSub, () => filtroSub = null);
      opciones.forEach(s =>
        chip(f, subcat(s), cuantos[s], filtroSub === s,
             () => filtroSub = filtroSub === s ? null : s));
    }
  }

  // --- Limpiar: la salida de emergencia con seis filtros combinables ---
  if(hayFiltros()){
    const f = fila("", t("filtrosLimpiar"));
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.textContent = "✕ " + t("filtrosLimpiar");
    b.onclick = e => { limpiarFiltros(); pintarFiltros(); refrescar(); volarDesde(e.currentTarget); };
    f.appendChild(b);
  }
}

/* La línea que contesta "¿por qué veo 12 eventos?". Se arma con lo que está
   puesto, en el orden en que se toca. */
function pintarEstado(){
  const partes = [];
  if(cuando !== "todo") partes.push(t("cuandoLargo")[cuando]);
  if(busqueda) partes.push(`“${busqueda}”`);
  if(soloGratis) partes.push(t("gratis"));
  if(publicoFiltro === "ninos") partes.push(t("ninos"));
  if(publicoFiltro === "adultos") partes.push(t("mas18"));
  // La categoría fija no se anuncia: es el título de la página.
  if(filtroCat && filtroCat !== CAT_FIJA) partes.push(cat(filtroCat)[IDIOMA]);
  if(filtroSub) partes.push(subcat(filtroSub));
  document.getElementById("conteo-estado").textContent = partes.join(" · ");
  const quien = filtroCat ? cat(filtroCat) : null;
  document.getElementById("atiende").innerHTML = quien
    ? carita(quien.mascota, quien.hex, 30)
    : carita("loica", "var(--acento)", 30);
}

/* ---------- LA CABECERA DE LA CATEGORÍA ----------
   Solo en las páginas de una categoría: el animal guía con su nombre, que es
   lo que dice "acá estás en Fiestas" antes de leer ningún chip. Es el <h1>
   porque es el único título que tiene la página. En el mapa general el
   elemento no existe y la función no hace nada. Se vuelve a pintar al
   cambiar de idioma. */
function pintarCabezaCat(){
  const caja = document.getElementById("cabeza-cat");
  if(!caja || !QUIEN_FIJO) return;
  const bajada = (t("catBajada") || {})[CAT_FIJA] || "";
  caja.innerHTML = `
    <span class="cabeza-cat-masc" aria-hidden="true">${carita(QUIEN_FIJO.mascota, QUIEN_FIJO.hex, 30)}</span>
    <h1>${escapar(QUIEN_FIJO[IDIOMA])}</h1>
    ${bajada ? `<p class="cabeza-cat-bajada">${escapar(bajada)}</p>` : ""}`;
}

/* ---------- EL BUSCADOR ----------
   Los filtros por animal contestan "¿qué tipo de cosa quiero hacer?". No
   contestan "¿qué hay en el Blondie?", que es como busca quien ya sabe lo que
   anda trucando. */
function sincronizarBuscador(){
  const campo = document.getElementById("buscar");
  campo.placeholder = t("buscar");
  campo.setAttribute("aria-label", t("buscarEtiqueta"));
  const lupa = document.getElementById("lupa");
  lupa.setAttribute("aria-label", t("buscarEtiqueta"));
  lupa.classList.toggle("activo", !!busqueda);
  lupa.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="2.4" stroke-linecap="round" aria-hidden="true">
      <circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.4 15.4 21 21"/></svg>`;
  const borrar = document.getElementById("borra-buscar");
  borrar.hidden = !campo.value;
  borrar.setAttribute("aria-label", t("buscarBorrar"));
}

function montarBuscador(){
  const campo = document.getElementById("buscar");
  const riel = document.getElementById("riel-fecha");

  /* 180 ms de espera antes de filtrar. Sin esto cada tecla vuelve a pintar la
     lista y a mandarle 2.283 puntos al mapa: escribir "blondie" son siete
     redibujados completos y el campo se traba en un teléfono. */
  let temporizador = null;
  campo.oninput = () => {
    document.getElementById("borra-buscar").hidden = !campo.value;
    clearTimeout(temporizador);
    temporizador = setTimeout(() => {
      busqueda = campo.value.trim();
      pintarFiltros(); refrescar();
    }, 180);
  };
  campo.onkeydown = e => {
    if(e.key !== "Escape") return;
    // Escape borra; si ya estaba vacío, cierra el campo en celular.
    if(campo.value){ campo.value = ""; campo.dispatchEvent(new Event("input")); }
    else riel.classList.remove("buscando");
  };
  document.getElementById("borra-buscar").onclick = () => {
    campo.value = "";
    campo.dispatchEvent(new Event("input"));
    campo.focus();
  };
  document.getElementById("lupa").onclick = () => {
    riel.classList.add("buscando");
    campo.focus();
  };
  // El <input> medía 22 px dentro de una cápsula de 38: tocar el borde no
  // enfocaba. Ahora la cápsula entera es el campo.
  document.querySelector(".campo-buscar").onclick = () => campo.focus();
  sincronizarBuscador();
}

/* ---------- LA LOICA QUE VUELA ---------- */
function volarLoica(desde, hasta, ms = 700){
  if(!hayMapa || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const el = document.getElementById("loica-vuelo");
  if(!el.innerHTML) el.innerHTML = cuerpo("loica", "var(--acento)", 56, {pose:"volando"});
  const cx = (desde.x + hasta.x) / 2;
  const cy = Math.min(desde.y, hasta.y) - 90;   // el arco sube: esquiva pines
  el.style.offsetPath = `path("M ${desde.x} ${desde.y} Q ${cx} ${cy} ${hasta.x} ${hasta.y}")`;
  el.style.setProperty("--dur-vuelo", ms + "ms");
  el.classList.remove("vuela");
  void el.offsetWidth;
  el.classList.add("vuela");
}
const centroDe = el => {
  const r = el.getBoundingClientRect(), m = document.getElementById("mapa").getBoundingClientRect();
  return {x: r.left + r.width/2 - m.left, y: r.top + r.height/2 - m.top};
};
// Al filtrar la Loica vuela del chip que tocaste al contador y suelta el número
const volarDesde = chip =>
  volarLoica(centroDe(chip), centroDe(document.getElementById("conteo")), 480);

/* ---------- LISTA POR TANDAS ----------
   345 tarjetas con 298 imágenes remotas de una sola vez es lo que hacía que
   el panel llegara trabado a la primera pasada de dedo. Se pintan de a 24 y
   el resto entra cuando el centinela asoma. */
const TANDA = 24;
let pintados = 0, observador = null;

function refrescar(){
  listaActual = visibles();
  const conteoEl = document.getElementById("conteo");
  if(conteoEl.textContent !== String(listaActual.length)){
    conteoEl.classList.remove("pop"); void conteoEl.offsetWidth; conteoEl.classList.add("pop");
  }
  conteoEl.textContent = listaActual.length;
  document.getElementById("conteo-txt").textContent =
    listaActual.length === 1 ? t("evento") : t("eventos");

  if(hayMapa && mapa.getSource("eventos")) mapa.getSource("eventos").setData(datosGeo(listaActual));

  const cont = document.getElementById("lista");
  cont.innerHTML = "";
  pintados = 0;
  observador?.disconnect();

  if(!listaActual.length){
    /* Buscar una palabra que no existe y filtrar hasta quedar en cero son dos
       callejones distintos, y la salida también: de uno se sale cambiando la
       palabra, del otro soltando un chip. Decir "prueba sacando algún filtro"
       a quien escribió "asdfgh" no ayuda a nadie. */
    const porPalabra = !!busqueda;
    cont.innerHTML = `<div class="vacio">${cuerpo("loica","var(--acento)",76,{pose:"durmiendo"})}
      <p><b>${porPalabra ? t("buscarSin") : t("vacio")}</b><br>${
        porPalabra ? t("buscarSinPista") : t("vaciopista")}</p></div>`;
    /* En reposo el panel muestra 130 px de lista: la cabeza de la Loica y
       ningún texto. Sube a la altura media para que se lea la salida.
       Pero si el usuario ESCONDIÓ la hoja para ver el mapa, no se le devuelve
       sola: quedarse en cero es una respuesta que ya está dada —el mapa sin
       pines y el botón diciendo "0 eventos"— y hacerla saltar sería pisarle
       una decisión que tomó a propósito. */
    if(hoja && hoja.indice > HOJA_OCULTA) fijarPanel(1);
    return;
  }
  cont.scrollTop = 0;
  // La clase se pone solo para la primera tanda: si quedara puesta, cada
  // vez que entran 24 más se reanimarían las de arriba al hacer scroll
  cont.classList.add("lista-anima");
  masTarjetas();
  setTimeout(() => cont.classList.remove("lista-anima"), 500);

  const centinela = document.createElement("div");
  centinela.className = "fin-lista";
  centinela.id = "centinela";
  cont.appendChild(centinela);
  observador = new IntersectionObserver(e => { if(e[0].isIntersecting) masTarjetas(); },
                                        {root:cont, rootMargin:"420px"});
  observador.observe(centinela);
}

function masTarjetas(){
  const cont = document.getElementById("lista");
  const centinela = document.getElementById("centinela");
  const trozo = listaActual.slice(pintados, pintados + TANDA);
  const caja = document.createDocumentFragment();
  trozo.forEach(ev => caja.appendChild(tarjetaEvento(ev, abrirFicha)));
  cont.insertBefore(caja, centinela);
  pintados += trozo.length;
  if(centinela && pintados >= listaActual.length){
    centinela.textContent = "·";
    observador?.disconnect();
  }
}

/* ---------- FICHA ---------- */
function abrirFicha(ev, direccion = 0){
  const idx = listaActual.findIndex(x => x.id === ev.id);
  seleccionado = ev;
  const info = cat(ev.categoria);
  const fecha = ev.fecha.toLocaleDateString(localeDe(),
                  {weekday:"long", day:"numeric", month:"long"});
  const hora = (ev.fecha.getHours() || ev.fecha.getMinutes())
    ? ev.fecha.toLocaleTimeString(localeDe(),{hour:"2-digit",minute:"2-digit",hour12:false}) : "";
  const flecha = d => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${d}"
      fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  const ficha = document.getElementById("ficha");
  ficha.innerHTML = `
    <div class="ficha-nav">
      <button class="nav-ev" id="ev-prev" ${idx <= 0 ? "disabled" : ""}>
        ${flecha("M14 5l-7 7 7 7")}<span>${t("anteriorEv")}</span></button>
      <span class="ficha-pos">${idx + 1} ${t("deN")} ${listaActual.length}</span>
      <button class="nav-ev" id="ev-sig" ${idx >= listaActual.length - 1 ? "disabled" : ""}>
        <span>${t("siguienteEv")}</span>${flecha("M10 5l7 7-7 7")}</button>
      <button class="cerrar-ficha" id="ev-cerrar" aria-label="${t("cerrar")}">×</button>
    </div>
    <div class="ficha-scroll">
      ${urlSegura(ev.imagen) ? `<div class="ficha-foto">
          <img src="${escapar(urlSegura(ev.imagen))}" alt="" onerror="this.parentElement.remove()">
        </div>` : ""}
      <div class="ficha-cuerpo">
        <span class="mascota-nombre" style="color:${info.tintaVar}">
          ${carita(info.mascota, info.hex, 22)} ${info[IDIOMA]}</span>
        <h2>${escapar(ev.titulo)}</h2>
        ${urlSegura(ev.url) ? `<a class="boton bloque" href="${escapar(urlSegura(ev.url))}"
           target="_blank" rel="noopener nofollow">${t("ir")} ↗</a>` : ""}
        <div class="dato" style="margin-top:var(--e-4)"><span class="et">${t("cuando")}</span>
          <span>${fecha}${hora ? " · " + hora : ""}</span></div>
        <div class="dato"><span class="et">${t("donde")}</span>
          <span>${escapar(ev.lugar)}${ev.comuna ? ", " + escapar(ev.comuna) : ""}
          ${ev.precision === "comuna" ? `<br><span class="aprox">${t("aprox")}</span>` : ""}
          ${ev.precision === "sin_ubicar" ? `<br><span class="aprox">${t("sinUbicar")}</span>` : ""}</span></div>
        <div class="dato"><span class="et">${t("precio")}</span>
          <span class="precio${ev.gratis ? " libre" : ""}">${ev.gratis ? t("libre") : textoPrecio(ev)}</span></div>
        ${ev.descripcion ? `<div class="dato"><span class="et"></span>
          <span>${escapar(ev.descripcion)}</span></div>` : ""}
        <div id="compartir-ficha" style="margin-top:var(--e-4)"></div>
        <div class="fuente-pie">${t("fuente")} <b>${escapar(ev.fuente)}</b></div>
      </div>
    </div>`;

  ficha.style.setProperty("--desde", (direccion ? direccion * 18 : 0) + "px");
  ficha.classList.remove("cambiando"); void ficha.offsetWidth;
  if(direccion) ficha.classList.add("cambiando");
  ficha.classList.add("visible");
  document.getElementById("panel").classList.add("oculto");
  history.replaceState(null, "", "#/e/" + ev.id);
  document.getElementById("compartir-ficha").appendChild(botonesCompartir(ev));

  document.getElementById("ev-prev").onclick = () => moverFicha(-1);
  document.getElementById("ev-sig").onclick  = () => moverFicha(1);
  document.getElementById("ev-cerrar").onclick = cerrarFicha;

  if(hayMapa && ev.lat != null){
    /* Vuela a donde el pin VA A QUEDAR, no a donde está: el flyTo lo lleva al
       centro menos los 90 px de offset. Antes se proyectaba la posición vieja
       y la Loica aterrizaba a 130 px del pin, a veces fuera de la pantalla. */
    const caja = document.getElementById("mapa").getBoundingClientRect();
    volarLoica({x: caja.width/2, y: caja.height + 20},
               {x: caja.width/2, y: caja.height/2 - 90}, 650);
    mapa.flyTo({center:[ev.lon, ev.lat], zoom:Math.max(mapa.getZoom(), 15),
                offset:[0,-90], speed:1.5});
  }
}

// paso = -1 anterior, +1 siguiente. Es lo mismo que usan el botón, el swipe
// y las flechas del teclado, así los tres se comportan igual.
function moverFicha(paso){
  if(!seleccionado) return;
  const i = listaActual.findIndex(x => x.id === seleccionado.id);
  const siguiente = listaActual[i + paso];
  if(siguiente) abrirFicha(siguiente, paso);
}

function cerrarFicha(){
  document.getElementById("ficha").classList.remove("visible");
  document.getElementById("panel").classList.remove("oculto");
  if(location.hash.startsWith("#/e/")) history.replaceState(null, "", location.pathname);
  seleccionado = null;
}

/* Deslizar de lado para cambiar de evento. Solo cuenta si el gesto es
   claramente horizontal: si no, robaría el scroll vertical de la ficha. */
(() => {
  const ficha = document.getElementById("ficha");
  let x0 = 0, y0 = 0, activo = false;
  ficha.addEventListener("pointerdown", e => {
    if(e.pointerType === "mouse") return;
    activo = true; x0 = e.clientX; y0 = e.clientY;
  });
  ficha.addEventListener("pointerup", e => {
    if(!activo) return;
    activo = false;
    const dx = e.clientX - x0, dy = e.clientY - y0;
    if(Math.abs(dx) > 64 && Math.abs(dx) > Math.abs(dy) * 1.8) moverFicha(dx < 0 ? 1 : -1);
  });
  ficha.addEventListener("pointercancel", () => activo = false);
})();

/* --- La hoja de la lista: cuatro topes, agarre ancho y botón de vuelta ---
   El arrastre ya no vive acá. Era un bloque copiado y pegado en las cuatro
   páginas con mapa (mapa, cine, descuentos, talleres) y con el mismo defecto
   en las cuatro: solo enganchaba en el tirador, 29 px de alto que el pulgar
   no encuentra. Ahora lo hace `montarHoja()` en loica.js, que agrega el agarre
   desde la cabecera del contador y desde la lista, el tope OCULTA para ver el
   mapa entero, y el botón flotante que la trae de vuelta con el conteo vivo.
   Las otras tres páginas usan exactamente esto mismo; el contrato para
   portarlas está en notas/hoja-movil-contrato.md.

   El rótulo del botón lo pone ESTA página: la hoja no sabe si cuenta eventos,
   películas o descuentos, y "128" solo no es una respuesta. */
const hoja = montarHoja({
  rotulo: () => `${document.getElementById("conteo").textContent} ` +
                `${document.getElementById("conteo-txt").textContent}`,
});

/* ---------- ARRANQUE ----------
   La cabecera se pinta ANTES de pedir el JSON. El riel de fechas y los tres
   chips fijos no dependen de los datos, y pintarlos al tiro deja el header en
   su alto definitivo desde el primer cuadro: antes crecía de 78 a 150 px
   cuando llegaba eventos.json, el mapa ya había dibujado sus teselas para el
   alto viejo y quedaba una banda crema de ~60 px bajo los filtros en cuatro
   de cada cinco cargas en celular. La lista mientras tanto late con tres
   filas vacías en vez de decir "0 eventos". */
montarBuscador();
pintarFiltros();
document.getElementById("lista").innerHTML = esqueleto(3);
// El panel midió su reposo con la cabecera a medio pintar; ahora que tiene
// el alto definitivo, se vuelve a medir. Y recién ahora nace el mapa.
if(window.fijarPanel) fijarPanel(0);
crearMapa();
cargarEventos()
  .then(evs => {
    /* En una página de categoría el catálogo se recorta al entrar, no solo
       en visibles(): los números de los chips y el conteo cuentan sobre
       EVENTOS, y contar fiestas en la página de teatro sería mentir. */
    EVENTOS = CAT_FIJA ? evs.filter(ev => ev.categoria === CAT_FIJA) : evs;
    pintarFiltros(); refrescar();
    if(hayMapa) requestAnimationFrame(() => { mapa.resize(); mapa.triggerRepaint(); });
    const enlace = location.hash.match(/^#\/e\/(.+)$/);
    if(enlace){
      const ev = EVENTOS.find(e => e.id === enlace[1]);
      if(ev) abrirFicha(ev);
      /* Un link a una ficha que no es de esta categoría —lo mandó alguien
         desde otra página, o el clasificador cambió de idea después de que
         se compartió— no se deja caer en una lista sin ella: se reenvía al
         mapa general, que sí la tiene. */
      else if(CAT_FIJA && evs.some(e => e.id === enlace[1]))
        location.replace("mapa.html#/e/" + enlace[1]);
    }
  })
  .catch(() => {
    document.getElementById("lista").innerHTML =
      `<div class="vacio">${cuerpo("loica","var(--acento)",88,{pose:"durmiendo"})}
       <p><b>${IDIOMA === "en" ? "Couldn't load events" :
               IDIOMA === "pt" ? "Não consegui carregar os eventos" :
               "No pude cargar los eventos"}</b><br>
       <button class="boton secundario" style="margin-top:12px"
         onclick="location.reload()">${IDIOMA === "en" ? "Try again" :
           IDIOMA === "pt" ? "Tentar de novo" : "Reintentar"}</button></p></div>`;
  });

window.addEventListener("loica:idioma", () => {
  sincronizarBuscador(); pintarCabezaCat();
  pintarFiltros(); refrescar(); if(seleccionado) abrirFicha(seleccionado);
});

/* Un solo manejador para el toque en el mapa, con una caja de ±14 px alrededor
   del dedo. El pin se dibuja con la punta en la coordenada y el dedo toca el
   cuerpo, no la punta: antes MapLibre consultaba el píxel exacto y a 12 px del
   centro ya no abría nada. Si caen varios en la caja gana el último dibujado,
   que por symbol-sort-key es el gratis. Tocar mapa pelado cierra la ficha. */
if(hayMapa) mapa.on("click", e => {
  if(!mapa.getLayer("pines")) return cerrarFicha();
  const r = 14, p = e.point;
  const tocados = mapa.queryRenderedFeatures([[p.x - r, p.y - r], [p.x + r, p.y + r]],
                                             {layers:["pines"]});
  if(!tocados.length) return cerrarFicha();
  const ev = EVENTOS.find(x => x.id === tocados[tocados.length - 1].properties.id);
  if(ev) abrirFicha(ev);
});
addEventListener("keydown", e => {
  if(e.key === "Escape") cerrarFicha();
  if(!seleccionado) return;
  if(e.key === "ArrowRight"){ e.preventDefault(); moverFicha(1); }
  if(e.key === "ArrowLeft"){ e.preventDefault(); moverFicha(-1); }
});
