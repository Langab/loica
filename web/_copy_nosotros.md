# Copy de "Nosotros" — versión en primera persona

Reemplaza el objeto `TX` de `nosotros.html` (líneas 120-205 de la versión actual).
Misma estructura de claves, mismo orden, mismos colores: se pega y funciona sin tocar el JS de pintado.

**Qué cambia respecto del copy anterior**

- Pasa de "nosotros" a "yo". Hay una persona, no un equipo, y ahora se nota.
- Los datos son reales y verificables contra el pipeline: 31 fuentes activas, ~100 eventos en la categoría "otros", seis comunas bien cubiertas, el caso del concierto de Talca colado.
- Se baja la promesa de "menos de 48 horas" a algo que una persona sola puede cumplir un viernes a las 23:00.
- Se agrega una sección opcional donde se admite lo que todavía no funciona (ver punto 5). Es lo que más lo aleja de sonar a texto generado.

---

## 1. Cambios fuera de `TX`

En el `<head>` de `nosotros.html`:

```html
<title>Quién hace Loica</title>
<meta name="description" content="Loica la hace una persona, en Santiago, después de la pega. Acá está por qué existe, cómo se llena el mapa y qué todavía no funciona.">
```

En el nav (`loica.js`, líneas 107, 119, 131 y 190-192): la etiqueta "Nosotros" contradice el texto en primera persona. Sugerencia, si quieres cerrar el círculo:

| idioma | actual | propuesta |
|---|---|---|
| es | Nosotros | Quién hace esto |
| en | About | Who makes this |
| pt | Sobre nós / Sobre | Quem faz isso |

(En la barra inferior, donde el espacio es poco: `es: "Quién"`, `en: "Who"`, `pt: "Quem"`.)

---

## 2. Titulares alternativos

El actual — "Una ciudad se usa o se pierde" — es el que más delata IA: sentencia redonda, sujeto impersonal, tono de marca grande. Todas las opciones de abajo son en primera persona y ninguna promete nada.

| # | es-CL | en | pt-BR | Cuándo usarlo |
|---|---|---|---|---|
| **1 (recomendado)** | Me aburrí de enterarme al día siguiente | I got tired of finding out the day after | Cansei de descobrir no dia seguinte | Cuenta el origen real en siete palabras. Es queja, no manifiesto. |
| 2 | Santiago pasa igual, te enteres o no | Santiago happens whether you find out or not | Santiago acontece você sabendo ou não | Más ancho, sirve si quieres algo menos anecdótico. |
| 3 | Esto lo hago yo, después de la pega | I make this after work | Isso aqui eu faço depois do trabalho | El más honesto y el más desarmante. Funciona si la foto/mascota acompaña. |
| 4 | Un mapa de lo que está pasando hoy | A map of what is on today | Um mapa do que rola hoje | El más funcional, cero personalidad. Plan B si el resto suena demasiado íntimo. |
| 5 | Hola, soy Benjamín | Hi, I am Benjamín | Oi, eu sou o Benjamín | Solo si en algún momento hay una foto tuya en la portada. |

---

## 3. Bloque `es` (original)

```js
  es:{
    tit:"Me aburrí de enterarme al día siguiente",
    entrada:"Me llamo Benjamín, vivo en Santiago y trabajo en el sector público. Loica partió de una molestia chica: quedarme un sábado en la casa y el lunes cachar por Instagram que a diez cuadras hubo una tocata gratis a la que habría ido feliz. Armé esto en las tardes, después de la pega. Es un mapa de lo que está pasando en la ciudad, ordenado para que decidas en dos minutos y salgas.",
    tCre:"Por qué está hecha así", sCre:"Decisiones que tomé al principio y que no pienso mover.",
    cre:[
      ["Lo gratis va primero","En casi todas las plataformas de eventos existe lo que se vende y el resto no aparece. Pero buena parte de lo bueno de Santiago no tiene entrada: el taller municipal, el cuentacuentos de la biblioteca, el ciclo de cine de una universidad, la clase de la plaza. Nada de eso tiene plata para difundirse. Por eso el filtro de gratis está arriba de todo — hoy casi un tercio de lo que aparece no cuesta nada — y quien organiza algo gratis no me va a pagar nunca, ni ahora ni si esto crece.","var(--rojo-loica)"],
      ["No vendo entradas","Cada panorama termina en un botón que te saca de Loica y te deja en el sitio del organizador, en su Instagram o en su ticketera. Sí, eso significa que la gente se va. Me parece mejor que ponerme al medio de una plata que no es mía.","var(--amarillo-micro)"],
      ["El mapa es para salir","Prefiero que uses la app dos minutos y salgas, a que te quedes scrolleando media hora. Una plaza con gente se camina distinto de noche; no tengo un estudio que lo pruebe, pero cualquiera que haya vuelto de una feria a las once sabe de qué hablo.","var(--verde-cerro)"],
    ],
    tCom:"Cómo se llena esto", sCom:"No hay redacción ni equipo. Hay un programa que busca y estoy yo revisando.",
    pasos:[
      ["A las seis de la mañana","Un programa que escribí revisa 31 agendas: municipios, centros culturales, teatros, universidades y un par de ticketeras chicas. No entra a Instagram ni a los sitios que piden por escrito que no los rastreen, aunque sean la puerta más fácil."],
      ["Después, a mano","Nada se publica solo. Todo entra como borrador y lo miro yo. Hay fuentes que publican sus talleres sin fecha — el CEINA es la clásica — y esos quedan en una lista aparte que completo uno por uno, abriendo la página."],
      ["Y te mando a la fuente","Cada ficha guarda el link de donde salió. Si Loica se equivocó en la hora, ahí está el original para confirmarlo. Es el mismo botón que aprieto yo cuando dudo."],
    ],
    tEle:"Los bichos", sEle:"Cada categoría tiene un animal chileno, así reconoces de qué se trata sin leer nada: sirve si andas apurado, y sirve más todavía si no hablas español. Los dibujos los hice yo y se nota. Algún día los va a hacer alguien que sepa dibujar.",
    ele:[
      ["loica","La Loica","Tu guía","El pájaro que le da el nombre a la app. Pecho rojo, parada en los postes de cualquier camino del campo chileno. Convertirla en el pin del mapa era demasiado obvio para no hacerlo."],
      ["culpeo","El Culpeo","Fiestas y carrete","El zorro chileno. Anda de noche, se mueve por donde nadie está mirando y le da lo mismo la hora. Le tocaron las fiestas."],
      ["pudu","El Pudú","Gratis y aire libre","El ciervo más chico del mundo: no llega al medio metro. Cuida los panoramas que no cuestan nada, que son los que más se comparten."],
      ["chincol","El Chincol","Clases y talleres","Canta en cualquier plaza de Santiago a las siete de la mañana, se lo hayas pedido o no. Justo donde pasan las clases de barrio."],
      ["condor","El Cóndor","Conciertos grandes","Para lo masivo: estadios, festivales, lo que se ve desde lejos."],
      ["chinchilla","La Chinchilla","Cultura","Chilena, nocturna y en peligro. Le tocó lo de adentro: teatro, cine, museos y exposiciones."],
    ],
    tCie:"¿Organizas algo?", sCie:"Si haces clases en una plaza, tocas, montas una obra o armas un taller de barrio, súbelo. Es gratis y va a seguir siendo gratis. Lo reviso yo, así que a veces me demoro dos días y a veces cuatro. Si pasa una semana y no aparece, insiste: se me pasó.",
    cta1:"Subir un panorama", cta2:"Ir al mapa",
    pie:"Loica la hago yo, en Santiago, fuera de mi horario de trabajo y con mis propias herramientas. Si ves algo malo, dime y lo arreglo.",
  },
```

---

## 4. Bloque `en`

No es traducción literal: se cambió lo que en inglés sonaría raro ("panorama", "la pega", "carrete") por su equivalente natural, y se mantuvo el ritmo desparejo del original.

```js
  en:{
    tit:"I got tired of finding out the day after",
    entrada:"My name is Benjamín. I live in Santiago, I have a day job in the public sector, and Loica started as a small annoyance: staying home on a Saturday, then finding out on Monday, on Instagram, that there had been a free gig ten blocks away. I built this in the evenings after work. It is a map of what is on in the city, put together so you can decide in two minutes and get out the door.",
    tCre:"Why it works the way it does", sCre:"A few calls I made early on and do not plan to change.",
    cre:[
      ["Free things come first","On almost every events platform, what sells is what exists and the rest is invisible. But a lot of the good stuff in Santiago has no ticket at all: the council workshop, the storytelling hour at the library, a university film season, the class in the square. None of it has money for promotion. So the free filter sits at the top — right now close to a third of what you see costs nothing — and anyone running a free event will never pay me, not now and not later.","var(--rojo-loica)"],
      ["I do not sell tickets","Every listing ends in a button that takes you out of Loica and drops you on the organiser's own page, their Instagram or their ticket seller. Yes, that means people leave. I prefer that to standing in the middle of money that is not mine.","var(--amarillo-micro)"],
      ["The map is for leaving the house","I would rather you use the app for two minutes and go out than scroll it for half an hour. A square with people in it feels different to walk through at night. I have no study to prove that, but anyone who has walked home from a street fair at eleven knows what I mean.","var(--verde-cerro)"],
    ],
    tCom:"How the map gets filled", sCom:"No newsroom, no team. There is a program that searches and there is me, checking.",
    pasos:[
      ["Six in the morning","A program I wrote goes through 31 listings: councils, cultural centres, theatres, universities and a couple of small ticket sites. It does not touch Instagram, and it stays away from sites whose rules ask crawlers not to come in, even when that is the easy door."],
      ["Then by hand","Nothing publishes itself. Everything arrives as a draft and I look at it. Some places post their workshops with no date at all — CEINA does this every time — and those go into a separate pile I fill in one by one, opening each page."],
      ["Then I send you to the source","Every listing keeps the link it came from. If Loica got the time wrong, the original is right there to check. It is the same button I press myself when I am not sure."],
    ],
    tEle:"The animals", sEle:"Every category has a Chilean animal, so you can tell what something is without reading a word — useful in a hurry, and more useful if you do not speak Spanish. I drew them myself and it shows. One day someone who can actually draw will redo them.",
    ele:[
      ["loica","The Loica","Your guide","The bird the app is named after. Red breast, sits on fence posts along any country road in Chile. Turning it into the map pin was too obvious to skip."],
      ["culpeo","The Culpeo","Parties and nights out","The Chilean fox. Out at night, moving through the parts of town nobody is watching, with no regard for the hour. It got the parties."],
      ["pudu","The Pudú","Free and outdoors","The smallest deer in the world, under half a metre tall. It looks after everything that costs nothing, which is what people share the most."],
      ["chincol","The Chincol","Classes and workshops","Sings in every square in Santiago at seven in the morning, whether you asked for it or not. Which is exactly where the neighbourhood classes happen."],
      ["condor","The Cóndor","Big concerts","For the large stuff: stadiums, festivals, things you can see from far away."],
      ["chinchilla","The Chinchilla","Culture","Chilean, nocturnal and endangered. It got the indoor things: theatre, film, museums and exhibitions."],
    ],
    tCie:"Running something?", sCie:"If you teach a class in a square, play a gig, put on a play or run a workshop in your neighbourhood, put it up. It is free and it will stay free. I review these myself, so sometimes it takes two days and sometimes four. If a week goes by and nothing appears, nudge me — I missed it.",
    cta1:"Post something", cta2:"Open the map",
    pie:"Loica is made by one person, in Santiago, outside working hours and on my own gear. If something is wrong, tell me and I will fix it.",
  },
```

---

## 5. Bloque `pt`

Portugués de Brasil, no traducción del español. "Panorama" no existe en pt-BR con ese sentido: se usa "rolê" y "programa".

```js
  pt:{
    tit:"Cansei de descobrir no dia seguinte",
    entrada:"Meu nome é Benjamín. Moro em Santiago, trabalho no setor público e a Loica nasceu de uma chateação pequena: passar o sábado em casa e descobrir na segunda, pelo Instagram, que teve um show de graça a dez quadras dali. Montei isso à noite, depois do trabalho. É um mapa do que está rolando na cidade, organizado para você decidir em dois minutos e sair de casa.",
    tCre:"Por que ela é assim", sCre:"Decisões que tomei no começo e que não pretendo mudar.",
    cre:[
      ["O que é de graça vem primeiro","Em quase toda plataforma de eventos existe o que se vende, e o resto não aparece. Só que boa parte do que é bom em Santiago não tem ingresso: a oficina da prefeitura, a hora do conto na biblioteca, a mostra de cinema de uma universidade, a aula na praça. Nada disso tem verba de divulgação. Por isso o filtro de graça fica no topo — hoje quase um terço do que aparece não custa nada — e quem organiza evento gratuito nunca vai me pagar, nem agora nem se isso crescer.","var(--rojo-loica)"],
      ["Não vendo ingresso","Cada rolê termina num botão que te tira da Loica e te deixa no site de quem organiza, no Instagram dele ou na bilheteria. Sim, isso significa que as pessoas vão embora. Prefiro assim do que me meter no meio de um dinheiro que não é meu.","var(--amarillo-micro)"],
      ["O mapa é para sair de casa","Prefiro que você use o app dois minutos e saia, em vez de ficar meia hora rolando a tela. Uma praça com gente se atravessa de outro jeito à noite. Não tenho estudo que prove isso, mas quem já voltou de uma feira às onze da noite sabe do que estou falando.","var(--verde-cerro)"],
    ],
    tCom:"Como isso se enche", sCom:"Não tem redação nem equipe. Tem um programa que busca e tem eu, conferindo.",
    pasos:[
      ["Às seis da manhã","Um programa que eu escrevi passa por 31 agendas: prefeituras, centros culturais, teatros, universidades e umas bilheterias pequenas. Não entra no Instagram nem nos sites que pedem por escrito para não serem rastreados, mesmo quando essa seria a porta mais fácil."],
      ["Depois, na mão","Nada é publicado sozinho. Tudo entra como rascunho e eu olho. Tem lugar que publica as oficinas sem data nenhuma — o CEINA é o clássico — e esses vão para uma lista à parte que eu completo um por um, abrindo cada página."],
      ["E te mando para a fonte","Cada ficha guarda o link de onde saiu. Se a Loica errou o horário, o original está ali para conferir. É o mesmo botão que eu aperto quando fico na dúvida."],
    ],
    tEle:"Os bichos", sEle:"Cada categoria tem um animal chileno, então dá para saber do que se trata sem ler nada: ajuda na pressa e ajuda mais ainda se você não fala espanhol. Os desenhos fui eu que fiz e dá para notar. Um dia alguém que saiba desenhar vai refazer.",
    ele:[
      ["loica","A Loica","Seu guia","O pássaro que dá nome ao app. Peito vermelho, pousado nos postes de qualquer estrada de campo no Chile. Virar o pin do mapa era óbvio demais para deixar passar."],
      ["culpeo","O Culpeo","Festas e noite","A raposa chilena. Anda de noite, circula por onde ninguém está olhando e não liga para a hora. Ficou com as festas."],
      ["pudu","O Pudú","De graça e ao ar livre","O menor cervo do mundo: não chega a meio metro. Cuida do que não custa nada, que é justamente o que mais se compartilha."],
      ["chincol","O Chincol","Aulas e oficinas","Canta em qualquer praça de Santiago às sete da manhã, você tendo pedido ou não. Bem onde acontecem as aulas de bairro."],
      ["condor","O Cóndor","Shows grandes","Para o que é grande: estádios, festivais, o que dá para ver de longe."],
      ["chinchilla","A Chinchilla","Cultura","Chilena, noturna e ameaçada de extinção. Ficou com o que acontece dentro: teatro, cinema, museus e exposições."],
    ],
    tCie:"Organiza alguma coisa?", sCie:"Se você dá aula numa praça, toca, monta uma peça ou faz uma oficina de bairro, sobe aqui. É de graça e vai continuar sendo. Quem revisa sou eu, então às vezes demora dois dias e às vezes quatro. Se passar uma semana e não aparecer, me cutuque: passou batido.",
    cta1:"Publicar um rolê", cta2:"Abrir o mapa",
    pie:"A Loica é feita por uma pessoa só, em Santiago, fora do horário de trabalho e com equipamento próprio. Se tiver algo errado, me avise que eu conserto.",
  },
```

---

## 6. Sección opcional: "Lo que todavía no funciona"

Es la parte que más aleja el texto de sonar a IA, porque ninguna marca escribe esto. Reutiliza el estilo `.creencias` que ya existe, así que solo hay que agregar la sección al HTML y tres líneas al `pintar()`.

**HTML** (entre la sección de "cómo se llena esto" y la de los bichos):

```html
<section>
  <h2 id="t-falta"></h2>
  <p class="sub" id="s-falta"></p>
  <div class="creencias" id="falta"></div>
</section>
```

**JS** (dentro de `pintar()`):

```js
  document.getElementById("t-falta").textContent = x("tFal");
  document.getElementById("s-falta").textContent = x("sFal");
  document.getElementById("falta").innerHTML = x("fal").map(([t,d]) =>
    `<article class="creencia" style="--tono:var(--tinta-tenue)"><h3>${t}</h3><p>${d}</p></article>`).join("");
```

**Claves nuevas** (se agregan a cada idioma; el arreglo `fal` puede tener distinto largo por idioma, el render lo recorre igual):

```js
    // es
    tFal:"Lo que todavía no funciona", sFal:"Lo escribo acá para no tener que fingir después.",
    fal:[
      ["Un tercio queda en “otros”","El programa clasifica solo y muchas veces no cacha qué encontró: hoy hay más de cien panoramas en la categoría “otros”. Lo estoy arreglando de a poco, con reglas nuevas y a mano."],
      ["Faltan comunas","La provincia de Santiago tiene 32 comunas. Loica cubre bien seis o siete — Santiago Centro, Providencia, Ñuñoa, Recoleta, Las Condes, Estación Central — y casi nada de Puente Alto, Maipú o La Florida. Eso me molesta a mí más que a ti."],
      ["Se cuelan errores","Una vez apareció un concierto en Talca porque la ticketera no decía la ciudad. Si ves algo raro, avísame: no hay equipo de moderación, hay una persona con un teléfono."],
    ],

    // en
    tFal:"What does not work yet", sFal:"Writing it down here so I do not have to pretend later.",
    fal:[
      ["A third of it lands in “other”","The program sorts events on its own and often has no idea what it just found: right now more than a hundred listings sit in the “other” category. I am fixing it slowly, with new rules and by hand."],
      ["Whole districts are missing","The province of Santiago has 32 comunas. Loica covers six or seven properly — Santiago Centro, Providencia, Ñuñoa, Recoleta, Las Condes, Estación Central — and almost nothing in Puente Alto, Maipú or La Florida. That bothers me more than it bothers you."],
      ["Things slip through","A concert in Talca once showed up here because the ticket site never mentioned the city. If you see something odd, tell me. There is no moderation team, there is one person with a phone."],
      ["Most listings are in Spanish","The interface is translated, but event descriptions stay in the language the organiser wrote them in, which is nearly always Spanish. Translating them automatically would mean publishing things I have not read, and I would rather not."],
    ],

    // pt
    tFal:"O que ainda não funciona", sFal:"Escrevo aqui para não ter que fingir depois.",
    fal:[
      ["Um terço cai em “outros”","O programa classifica sozinho e muitas vezes não faz ideia do que achou: hoje tem mais de cem eventos na categoria “outros”. Estou consertando aos poucos, com regras novas e na mão."],
      ["Faltam bairros inteiros","A província de Santiago tem 32 comunas. A Loica cobre bem umas seis ou sete — Santiago Centro, Providencia, Ñuñoa, Recoleta, Las Condes, Estación Central — e quase nada de Puente Alto, Maipú ou La Florida. Isso me incomoda mais do que a você."],
      ["Escapa erro","Uma vez apareceu um show em Talca porque a bilheteria não dizia a cidade. Se você vir algo estranho, me avisa. Não existe equipe de moderação, existe uma pessoa com um celular."],
      ["Quase tudo está em espanhol","A interface está traduzida, mas a descrição de cada evento fica na língua em que quem organiza escreveu, que quase sempre é espanhol. Traduzir automático seria publicar coisa que eu não li, e prefiro não."],
    ],
```

---

## 7. Datos que hay que mantener al día

Los números son lo que hace que el texto suene a persona y no a marca, pero envejecen. Revisión sugerida: cada vez que agregues fuentes.

| Dato en el copy | Valor hoy (10-ago-2026) | De dónde sale |
|---|---|---|
| "31 agendas" | 31 fuentes con `activa: true` (de 84 registradas) | `config/fuentes.yaml` |
| "casi un tercio ... no cuesta nada" | 86 gratis de 271 (32%) | `web/eventos.json` |
| "más de cien panoramas en 'otros'" | 102 de 271 | `web/eventos.json` |
| "seis o siete comunas" | Santiago 116, Providencia 49, Las Condes 18, Estación Central 13, Recoleta 13, Ñuñoa 10 | `web/eventos.json` |
| "el CEINA publica sin fecha" | Está anotado en las notas de la fuente `ceina` | `config/fuentes.yaml` |
| "un concierto en Talca" | Evento real de PortalTickets con "TALCA" en el título y comuna vacía | `web/eventos.json` |

---

## 8. Tres decisiones de copy que conviene que confirmes

1. **Aparece tu nombre de pila, no tu apellido ni tu empleador.** El texto dice "trabajo en el sector público" y nada más: no nombra el servicio, no usa correo institucional y no da a entender ningún vínculo entre el proyecto y tu trabajo. Es lo que pide la higiene de funcionario del plan maestro. Si prefieres no aparecer con nombre, el bloque funciona igual borrando "Me llamo Benjamín," del `entrada` y usando el titular 4.
2. **Se cayó la promesa de "menos de 48 horas".** Ahora dice "a veces dos días y a veces cuatro; si pasa una semana, insiste". Es más creíble y es la que puedes cumplir con fiebre un viernes. Si prefieres mantener el compromiso duro, cámbialo, pero entonces hay que cumplirlo siempre.
3. **El texto admite que los dibujos son tuyos y provisorios.** Suma mucho en credibilidad y desactiva la crítica antes de que llegue. Cuando contrates al ilustrador, esa frase se borra sola.
