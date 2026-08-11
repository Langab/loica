/* ============================================================
   LOICA — módulo compartido
   Mascotas (SVG), traducciones, datos y utilidades comunes.
   ============================================================ */

/* ---------- MASCOTAS ----------
   Seis animales chilenos dibujados con formas simples para que se lean
   a 20px en un pin del mapa y a 80px en un estado vacío.
   `color` pinta el cuerpo; el acento va fijo para conservar identidad. */
const MASCOTAS = {
  // La Loica: guía de la app. El pecho rojo es lo único que no cambia de
  // color nunca — es el pin del mapa y toda la idea de la marca.
  loica: (c="currentColor") => `
    <path d="M3.1 9.3c-.5-.3-1.1.3-.8.8l2 3.2c.1 2.9 1.9 5.4 4.5 6.6l-.5 1.7c-.1.4.2.7.6.7h1.1c.3 0 .5-.2.6-.4l.4-1.3c.5.1 1 .1 1.5.1 4.3 0 7.7-3.3 7.7-7.4 0-1.6-.5-3.1-1.4-4.3l-.1-.2c0-2.1-1.7-3.8-3.8-3.8-1.6 0-3 1-3.6 2.4-1.7.2-3.2.9-4.4 2L3.1 9.3z" fill="${c}"/>
    <path d="M8.8 19.9c-2.6-1.2-4.4-3.7-4.5-6.6l.7-.2c.7-.2 1.4-.3 2.1-.3 3.4 0 6.1 2.6 6.4 5.9-.5.2-1.1.3-1.7.3-1.1 0-2.1-.2-3-.6l-.5 1.5h.5z" fill="#E8442E"/>
    <path d="M4.3 13.3c.9-.4 1.9-.6 2.9-.6 3.4 0 6.2 2.6 6.5 5.9-2.6.9-5.6.1-7.4-2.1-.9-1-1.5-2.1-2-3.2z" fill="#E8442E"/>
    <circle cx="15.6" cy="7.6" r="1" fill="#FAF3E7"/>
    <circle cx="15.6" cy="7.6" r=".4" fill="#1E2A4A"/>
    <path d="M18.9 6.5l3.9-.8-3.6 2.5z" fill="#F5B52E"/>`,

  // El Cóndor: eventos grandes. Alas abiertas, collar blanco.
  condor: (c="currentColor") => `
    <path d="M12 8.6c1.1 0 2 .8 2.2 1.8l6.9-3.2c.5-.2 1 .3.8.8l-2.6 6c-.6 1.4-2 2.3-3.5 2.3h-.9l-1.2 3.3c-.3.7-1.3.7-1.6 0l-1.2-3.3h-.9c-1.5 0-2.9-.9-3.5-2.3l-2.6-6c-.2-.5.3-1 .8-.8l6.9 3.2c.2-1 1.1-1.8 2.2-1.8z" fill="${c}"/>
    <path d="M9.9 10.2c.4-.9 1.2-1.5 2.1-1.5s1.7.6 2.1 1.5c-.6.5-1.3.8-2.1.8s-1.5-.3-2.1-.8z" fill="#FAF3E7"/>
    <circle cx="12" cy="6.3" r="2.4" fill="${c}"/>
    <circle cx="11.1" cy="5.9" r=".8" fill="#FAF3E7"/>
    <path d="M13.9 6.1l2.1-.6-1.9 1.5z" fill="#F5B52E"/>`,

  // El Culpeo: fiestas y noche. Zorro de frente, orejas puntudas.
  culpeo: (c="currentColor") => `
    <path d="M4.4 4.1c-.4-.2-.8.1-.8.5l.3 5.1c.1 1.4.5 2.7 1.3 3.8l-.5.3c-.4.2-.4.7 0 .9l1.2.7c1.4 2.5 3.6 4.1 6.1 4.1s4.7-1.6 6.1-4.1l1.2-.7c.4-.2.4-.7 0-.9l-.5-.3c.8-1.1 1.2-2.4 1.3-3.8l.3-5.1c0-.4-.4-.7-.8-.5l-4.6 2.5c-.9-.3-1.9-.5-3-.5s-2.1.2-3 .5L4.4 4.1z" fill="${c}"/>
    <path d="M8.6 15.3c.9-.7 2.1-1.1 3.4-1.1s2.5.4 3.4 1.1c-.9 1.7-2.1 2.7-3.4 2.7s-2.5-1-3.4-2.7z" fill="#FAF3E7" opacity=".92"/>
    <circle cx="9.3" cy="11.2" r="1.15" fill="#1E2A4A"/>
    <circle cx="14.7" cy="11.2" r="1.15" fill="#1E2A4A"/>
    <path d="M12 15.4c-.6 0-1.1.4-1.1.9s.5.9 1.1.9 1.1-.4 1.1-.9-.5-.9-1.1-.9z" fill="#1E2A4A"/>`,

  // El Pudú: gratis y aire libre. El ciervo más chico del mundo: orejas
  // enormes y redondas a los lados, cuernitos apenas insinuados.
  pudu: (c="currentColor") => `
    <path d="M9.2 4.6c-.2-.6-1.1-.4-1 .2l.3 2.1c-.3.2-.6.5-.8.8l-.4-.1M15 4.8c.2-.6 1.1-.4 1 .2l-.3 2"
          stroke="${c}" stroke-width="1.5" stroke-linecap="round" fill="none"/>
    <ellipse cx="3.8" cy="11.2" rx="2.9" ry="2.2" transform="rotate(-24 3.8 11.2)" fill="${c}"/>
    <ellipse cx="20.2" cy="11.2" rx="2.9" ry="2.2" transform="rotate(24 20.2 11.2)" fill="${c}"/>
    <ellipse cx="4.2" cy="11.2" rx="1.5" ry="1" transform="rotate(-24 4.2 11.2)" fill="#F2778C" opacity=".5"/>
    <ellipse cx="19.8" cy="11.2" rx="1.5" ry="1" transform="rotate(24 19.8 11.2)" fill="#F2778C" opacity=".5"/>
    <path d="M12 6.1c-3.4 0-6.1 2.5-6.1 5.8 0 2.3.9 4.3 2.4 5.6 1 .9 2.3 1.4 3.7 1.4s2.7-.5 3.7-1.4c1.5-1.3 2.4-3.3 2.4-5.6 0-3.3-2.7-5.8-6.1-5.8z" fill="${c}"/>
    <ellipse cx="12" cy="16.2" rx="3" ry="2.4" fill="#FAF3E7" opacity=".92"/>
    <circle cx="9.2" cy="11.6" r="1.25" fill="#1E2A4A"/>
    <circle cx="14.8" cy="11.6" r="1.25" fill="#1E2A4A"/>
    <circle cx="9.6" cy="11.2" r=".4" fill="#fff"/>
    <circle cx="15.2" cy="11.2" r=".4" fill="#fff"/>
    <ellipse cx="12" cy="15.6" rx="1.1" ry=".85" fill="#1E2A4A"/>`,

  // El Chincol: clases y talleres de barrio. Se reconoce por dos cosas: el
  // copete parado y el collar castaño en el cuello.
  chincol: (c="currentColor") => `
    <path d="M13.4 2.4c-.2-.4-.8-.3-.9.2l-.5 2.3-1.3-1.4c-.3-.4-.9 0-.8.5l.5 2.2c-.9.5-1.6 1.3-2 2.2l-.2.5" fill="${c}"/>
    <path d="M3.4 11.6c-.5-.2-1 .4-.7.8l2.1 2.8c.2 3 2.5 5.4 5.5 5.9l-.3 1.3c-.1.4.2.7.6.7h1.1c.3 0 .5-.2.6-.4l.4-1.2c3.9-.5 6.9-3.6 6.9-7.4 0-4.1-3.5-7.4-7.8-7.4-2.8 0-5.3 1.4-6.6 3.5l-1.8 1.4z" fill="${c}"/>
    <path d="M6.3 8.6c1.2-1.4 3-2.3 5.1-2.4.4 1 .5 2 .4 3-1.9.4-3.9.2-5.5-.6z" fill="#B0561F"/>
    <path d="M4.8 15.2c1.2-1 2.8-1.6 4.5-1.6 2.6 0 4.8 1.4 5.7 3.4-1.3 1.1-3 1.8-4.9 1.8-2.4 0-4.5-1.4-5.3-3.6z" fill="#F5B52E" opacity=".92"/>
    <circle cx="14.6" cy="10.4" r="1" fill="#FAF3E7"/>
    <circle cx="14.6" cy="10.4" r=".42" fill="#1E2A4A"/>
    <path d="M18.4 9.6l3.4-.6-3.2 2.2z" fill="#E8442E"/>`,

  // La Chinchilla: cultura. Orejas redondas enormes, cola tupida.
  chinchilla: (c="currentColor") => `
    <ellipse cx="6.2" cy="8.4" rx="3.1" ry="3.5" fill="${c}"/>
    <ellipse cx="17.8" cy="8.4" rx="3.1" ry="3.5" fill="${c}"/>
    <ellipse cx="6.2" cy="8.6" rx="1.5" ry="1.9" fill="#F2778C" opacity=".55"/>
    <ellipse cx="17.8" cy="8.6" rx="1.5" ry="1.9" fill="#F2778C" opacity=".55"/>
    <path d="M12 6.2c-3.7 0-6.6 2.9-6.6 6.4 0 3.4 2.9 6.2 6.6 6.2s6.6-2.8 6.6-6.2c0-3.5-2.9-6.4-6.6-6.4z" fill="${c}"/>
    <circle cx="9.5" cy="11.9" r="1.2" fill="#1E2A4A"/>
    <circle cx="14.5" cy="11.9" r="1.2" fill="#1E2A4A"/>
    <path d="M12 14.1c-.7 0-1.2.4-1.2.9 0 .6.5 1 1.2 1s1.2-.4 1.2-1c0-.5-.5-.9-1.2-.9z" fill="#1E2A4A"/>
    <path d="M4.6 14.6l-3 1.4M4.7 16.3l-2.6 2M19.4 14.6l3 1.4M19.3 16.3l2.6 2"
          stroke="${c}" stroke-width="1.1" stroke-linecap="round" opacity=".55"/>`,
};

function mascota(nombre, color, tamano=24){
  const dibujo = MASCOTAS[nombre] || MASCOTAS.loica;
  return `<svg viewBox="0 0 24 24" width="${tamano}" height="${tamano}"
            aria-hidden="true" focusable="false">${dibujo(color)}</svg>`;
}

/* ---------- CATEGORÍAS ----------
   Cada categoría tiene su mascota, su color y su nombre en 3 idiomas.
   Sale de estrategia_marca.md: la mascota ES la señalética de la categoría. */
const CATEGORIAS = {
  fiesta:    {mascota:"culpeo",     color:"var(--c-fiesta)",  hex:"#7A4FCF", es:"Fiestas",   en:"Parties",  pt:"Festas"},
  musica:    {mascota:"condor",     color:"var(--c-musica)",  hex:"#E8442E", es:"Música",    en:"Music",    pt:"Música"},
  teatro:    {mascota:"chinchilla", color:"var(--c-cultura)", hex:"#2F6FB5", es:"Teatro",    en:"Theatre",  pt:"Teatro"},
  arte:      {mascota:"chinchilla", color:"var(--c-cultura)", hex:"#2F6FB5", es:"Arte",      en:"Art",      pt:"Arte"},
  cine:      {mascota:"chinchilla", color:"var(--c-cultura)", hex:"#2F6FB5", es:"Cine",      en:"Film",     pt:"Cinema"},
  charla:    {mascota:"chinchilla", color:"var(--c-cultura)", hex:"#2F6FB5", es:"Charlas",   en:"Talks",    pt:"Palestras"},
  clases:    {mascota:"chincol",    color:"var(--c-clases)",  hex:"#E08A1E", es:"Clases",    en:"Classes",  pt:"Aulas"},
  idiomas:   {mascota:"chincol",    color:"var(--c-clases)",  hex:"#E08A1E", es:"Idiomas",   en:"Languages",pt:"Idiomas"},
  familia:   {mascota:"pudu",       color:"var(--c-libre)",   hex:"#2E7D5B", es:"Familia",   en:"Family",   pt:"Família"},
  aire_libre:{mascota:"pudu",       color:"var(--c-libre)",   hex:"#2E7D5B", es:"Aire libre",en:"Outdoors", pt:"Ar livre"},
  otros:     {mascota:"loica",      color:"var(--c-otros)",   hex:"#E8442E", es:"Otros",     en:"Other",    pt:"Outros"},
};
const cat = c => CATEGORIAS[c] || CATEGORIAS.otros;

/* ---------- TRADUCCIONES ---------- */
const TEXTOS = {
  es:{
    lema:"Santiago está pasando",
    mapa:"Mapa", calendario:"Calendario", agregar:"Agrega tu evento", nosotros:"Nosotros",
    eventos:"eventos", evento:"evento", gratis:"Gratis", hoy:"Hoy", finde:"Este finde",
    cuando:"Cuándo", donde:"Dónde", precio:"Precio", ir:"Ver en la fuente original",
    vacio:"No hay eventos con esos filtros", vaciopista:"Prueba sacando algún filtro",
    aprox:"Ubicación aproximada: centro de la comuna", sinUbicar:"Dirección por confirmar — revísala en la fuente", fuente:"Información publicada por",
    libre:"Entrada liberada", verMapa:"Ver en el mapa", cerrar:"Cerrar",
    meses:["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"],
    dias:["lun","mar","mié","jue","vie","sáb","dom"], mesesCortos:["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"],
    hoyBoton:"Hoy", anterior:"Mes anterior", siguiente:"Mes siguiente",
  },
  en:{
    lema:"Santiago is happening",
    mapa:"Map", calendario:"Calendar", agregar:"Add your event", nosotros:"About",
    eventos:"events", evento:"event", gratis:"Free", hoy:"Today", finde:"This weekend",
    cuando:"When", donde:"Where", precio:"Price", ir:"View original source",
    vacio:"No events match these filters", vaciopista:"Try removing a filter",
    aprox:"Approximate location: district centre", sinUbicar:"Address to be confirmed — check the source", fuente:"Information published by",
    libre:"Free entry", verMapa:"See on the map", cerrar:"Close",
    meses:["January","February","March","April","May","June","July","August","September","October","November","December"],
    dias:["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], mesesCortos:["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"],
    hoyBoton:"Today", anterior:"Previous month", siguiente:"Next month",
  },
  pt:{
    lema:"Santiago está acontecendo",
    mapa:"Mapa", calendario:"Calendário", agregar:"Adicione seu evento", nosotros:"Sobre nós",
    eventos:"eventos", evento:"evento", gratis:"Grátis", hoy:"Hoje", finde:"Neste fim de semana",
    cuando:"Quando", donde:"Onde", precio:"Preço", ir:"Ver na fonte original",
    vacio:"Nenhum evento com esses filtros", vaciopista:"Tente remover algum filtro",
    aprox:"Localização aproximada: centro da comuna", sinUbicar:"Endereço a confirmar — veja na fonte", fuente:"Informação publicada por",
    libre:"Entrada gratuita", verMapa:"Ver no mapa", cerrar:"Fechar",
    meses:["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"],
    dias:["seg","ter","qua","qui","sex","sáb","dom"], mesesCortos:["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"],
    hoyBoton:"Hoje", anterior:"Mês anterior", siguiente:"Próximo mês",
  },
};

let IDIOMA = localStorage.getItem("loica-idioma") || "es";
const t = clave => TEXTOS[IDIOMA][clave];

function fijarIdioma(nuevo){
  IDIOMA = nuevo;
  localStorage.setItem("loica-idioma", nuevo);
  document.documentElement.lang = nuevo;
}

/* ---------- TEMA ---------- */
function temaGuardado(){ return localStorage.getItem("loica-tema"); }
function aplicarTema(tema){
  if(tema) document.documentElement.dataset.tema = tema;
  else delete document.documentElement.dataset.tema;
  localStorage.setItem("loica-tema", tema || "");
}
function alternarTema(){
  const actual = document.documentElement.dataset.tema
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro");
  aplicarTema(actual === "oscuro" ? "claro" : "oscuro");
  return document.documentElement.dataset.tema;
}
aplicarTema(temaGuardado() || null);

/* ---------- CABECERA COMPARTIDA ---------- */
// Íconos de la navegación inferior. Simples a propósito: compiten con las
// mascotas y a 22px la mascota no se lee.
const ICONOS_NAV = {
  mapa:`<path d="M9 3 3 5.4v15.1l6-2.4 6 2.4 6-2.4V2.9l-6 2.4L9 3z" fill="none"
        stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M9 3v15.1M15 5.4v15.1" stroke="currentColor" stroke-width="1.8"/>`,
  calendario:`<rect x="3" y="4.8" width="18" height="16.2" rx="2.6" fill="none"
        stroke="currentColor" stroke-width="1.8"/>
        <path d="M3 9.6h18M8 3v3.6M16 3v3.6" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round"/><circle cx="8.4" cy="14" r="1.2" fill="currentColor"/>
        <circle cx="12.6" cy="14" r="1.2" fill="currentColor"/>`,
  agregar:`<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/>
        <path d="M12 8.2v7.6M8.2 12h7.6" stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round"/>`,
  nosotros:`<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/>
        <path d="M12 10.8v5.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="12" cy="7.9" r="1.15" fill="currentColor"/>`,
};
const PAGINAS = [["index.html","mapa"],["calendario.html","calendario"],
                 ["agrega.html","agregar"],["nosotros.html","nosotros"]];
// En la barra inferior el espacio es de 4 columnas: etiquetas de una palabra
const CORTOS = {
  es:{mapa:"Mapa", calendario:"Calendario", agregar:"Publicar", nosotros:"Nosotros"},
  en:{mapa:"Map", calendario:"Calendar", agregar:"Post", nosotros:"About"},
  pt:{mapa:"Mapa", calendario:"Agenda", agregar:"Publicar", nosotros:"Sobre"},
};

function pintarBarra(paginaActual){
  const logo = `<a class="logo" href="index.html" aria-label="Loica">
      ${mascota("loica", "var(--tinta)", 32)}<b>loica</b></a>`;
  const enlaces = PAGINAS
    .map(([url,clave]) => `<a href="${url}" data-tr="${clave}"
        ${url===paginaActual?'aria-current="page"':""}>${t(clave)}</a>`).join("");

  // Barra inferior: en celular es la navegación de verdad
  const inferior = document.getElementById("nav-inferior");
  if(inferior){
    inferior.innerHTML = PAGINAS.map(([url,clave]) =>
      `<a href="${url}" ${url===paginaActual?'aria-current="page"':""}>
         ${url===paginaActual?'<span class="punto"></span>':""}
         <svg viewBox="0 0 24 24" aria-hidden="true">${ICONOS_NAV[clave]}</svg>
         <span data-corto="${clave}">${CORTOS[IDIOMA][clave]}</span></a>`).join("");
  }
  const oscuro = document.documentElement.dataset.tema === "oscuro"
    || (!document.documentElement.dataset.tema && matchMedia("(prefers-color-scheme: dark)").matches);

  document.getElementById("barra").innerHTML = `${logo}
    <nav class="nav">${enlaces}</nav>
    <div class="barra-fin">
      <button class="tema" id="btn-tema" aria-label="Cambiar tema">${oscuro ? "☀" : "☾"}</button>
      <div class="idiomas" role="group" aria-label="Idioma">
        ${["es","en","pt"].map(i => `<button data-idioma="${i}"
            aria-pressed="${i===IDIOMA}">${i.toUpperCase()}</button>`).join("")}
      </div>
    </div>`;

  document.getElementById("btn-tema").onclick = e => {
    e.currentTarget.textContent = alternarTema() === "oscuro" ? "☀" : "☾";
  };
  document.querySelectorAll(".idiomas button").forEach(b => b.onclick = () => {
    fijarIdioma(b.dataset.idioma);
    document.querySelectorAll(".idiomas button").forEach(o =>
      o.setAttribute("aria-pressed", o === b));
    document.querySelectorAll("[data-tr]").forEach(el => el.textContent = t(el.dataset.tr));
    document.querySelectorAll("[data-corto]").forEach(el =>
      el.textContent = CORTOS[IDIOMA][el.dataset.corto]);
    window.dispatchEvent(new CustomEvent("loica:idioma"));
  });
}

/* ---------- DATOS ---------- */
async function cargarEventos(){
  const r = await fetch("eventos.json");
  const d = await r.json();
  return d.eventos.map(ev => ({...ev, fecha: new Date(ev.inicio)}));
}

/* ---------- UTILIDADES ---------- */
const escapar = s => String(s ?? "").replace(/[&<>"]/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

const localeDe = () => IDIOMA === "es" ? "es-CL" : IDIOMA === "pt" ? "pt-BR" : "en-GB";

/* En Chile las horas se leen 19:30, no 07:30 p. m. — y es-CL por defecto
   entrega el formato de 12 horas. */
const horaDe = fecha => fecha.toLocaleTimeString(localeDe(),
  {hour:"2-digit", minute:"2-digit", hour12:false});

function textoPrecio(ev){
  if(ev.gratis) return t("gratis");
  return ev.precio ? "$" + ev.precio.toLocaleString("es-CL") : "—";
}
const mismaFecha = (a,b) => a.toDateString() === b.toDateString();
const claveDia = f => `${f.getFullYear()}-${String(f.getMonth()+1).padStart(2,"0")}-${String(f.getDate()).padStart(2,"0")}`;

/* Cuándo es, dicho como lo diría una persona */
function etiquetaDia(fecha){
  const hoy = new Date();
  const manana = new Date(hoy); manana.setDate(hoy.getDate() + 1);
  if(mismaFecha(fecha, hoy))
    return {texto: IDIOMA === "en" ? "TODAY" : IDIOMA === "pt" ? "HOJE" : "HOY", pronto: true};
  if(mismaFecha(fecha, manana))
    return {texto: IDIOMA === "en" ? "TOMORROW" : IDIOMA === "pt" ? "AMANHÃ" : "MAÑANA", pronto: true};
  return {texto: `${fecha.getDate()} ${t("mesesCortos")[fecha.getMonth()]}`, pronto: false};
}

/* Tarjeta de evento reutilizada por el mapa y el calendario */
function tarjetaEvento(ev, alPulsar){
  const info = cat(ev.categoria);
  const dia = etiquetaDia(ev.fecha);
  const hora = (ev.fecha.getHours() || ev.fecha.getMinutes()) ? horaDe(ev.fecha) : "";
  const precio = ev.gratis ? t("gratis") : (ev.precio ? "$" + ev.precio.toLocaleString("es-CL") : "");

  const boton = document.createElement("button");
  boton.className = "tarjeta" + (ev.gratis ? " tarjeta-gratis" : "");
  boton.type = "button";
  boton.innerHTML = `
    <div class="miniatura">
      ${mascota(info.mascota, info.hex, 34)}
      ${ev.imagen ? `<img src="${escapar(ev.imagen)}" alt="" loading="lazy"
                       onerror="this.remove()">` : ""}
      <span class="dia${dia.pronto ? " pronto" : ""}">${dia.texto}</span>
    </div>
    <div class="tarjeta-cuerpo">
      ${hora ? `<div class="hora">${hora}</div>` : ""}
      <h3>${escapar(ev.titulo)}</h3>
      <div class="tarjeta-meta">
        <span>${escapar(ev.lugar)}</span>
        ${ev.comuna ? `<span>· ${escapar(ev.comuna)}</span>` : ""}
      </div>
    </div>
    <div class="precio${ev.gratis ? " libre" : precio ? "" : " sin-dato"}">${precio || "—"}</div>`;

  boton.onclick = () => alPulsar(ev);
  return boton;
}
