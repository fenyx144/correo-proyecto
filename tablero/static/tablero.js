(() => {
  "use strict";

  const INTERVALO_MS = 60000;
  const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  const COLORES_ESTADO = {
    "En curso": "#3b6ea5",
    "En espera": "#b7791f",
    "Vencida": "#c53030",
    "Hecha": "#2f855a",
    "Cancelada": "#9aa3af",
  };

  const moneda = new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN", minimumFractionDigits: 2 });
  const entero = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 0 });
  const decimal = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 1 });
  const hora = new Intl.DateTimeFormat("es-PE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  const graficos = {};
  const valoresKpi = new Map();
  const raiz = document.documentElement;

  const temaGuardado = localStorage.getItem("tema");
  if (temaGuardado) raiz.dataset.tema = temaGuardado;

  const css = (nombre) => getComputedStyle(raiz).getPropertyValue(nombre).trim();
  const num = (valor) => Number(valor) || 0;
  const escapar = (texto) => String(texto ?? "").replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

  function etiquetaMes(iso) {
    const [anio, mes] = iso.split("-");
    return `${MESES[Number(mes) - 1]} ${anio}`;
  }

  function duracion(minutos) {
    if (minutos === null || minutos === undefined) return "Sin datos";
    const m = num(minutos);
    if (m < 60) return `${decimal.format(m)} min`;
    if (m < 1440) return `${decimal.format(m / 60)} h`;
    return `${decimal.format(m / 1440)} d`;
  }

  function animarNumero(elemento, destino) {
    const formato = elemento.dataset.formato === "moneda" ? moneda : entero;
    const origen = valoresKpi.get(elemento) ?? 0;
    valoresKpi.set(elemento, destino);
    const inicio = performance.now();
    const duracionMs = 1200;
    const paso = (ahora) => {
      const t = Math.min((ahora - inicio) / duracionMs, 1);
      const suavizado = 1 - Math.pow(1 - t, 3);
      elemento.textContent = formato.format(origen + (destino - origen) * suavizado);
      if (t < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }

  function configurarChart() {
    Chart.defaults.font.family = css("--fuente");
    Chart.defaults.color = css("--texto-suave");
    Chart.defaults.borderColor = css("--pista");
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.pointStyle = "circle";
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 12;
    Chart.defaults.plugins.tooltip.backgroundColor = "rgba(15, 20, 40, 0.9)";
    Chart.defaults.animation.duration = 1200;
    Chart.defaults.animation.easing = "easeOutQuart";
  }

  function dibujar(id, config) {
    if (graficos[id]) graficos[id].destroy();
    graficos[id] = new Chart(document.getElementById(id), config);
  }

  function pintarKpis(datos) {
    const resumen = datos.resumen[0] || {};
    document.querySelectorAll("[data-kpi]").forEach((el) => animarNumero(el, num(resumen[el.dataset.kpi])));

    const correo = datos["conversion-por-origen"].find((f) => f.origen === "Correo automático");
    document.getElementById("kpi-conversion").textContent = correo
      ? `${decimal.format(num(correo.tasa_conversion_pct))} % de conversión`
      : "Sin oportunidades por correo";

    const ventas = datos["ventas-por-mes"];
    const confirmadas = ventas.reduce((s, f) => s + num(f.ventas_confirmadas), 0);
    const montoConfirmado = ventas.reduce((s, f) => s + num(f.monto_confirmado), 0);
    const cotizado = ventas.reduce((s, f) => s + num(f.monto_cotizado), 0);
    document.getElementById("kpi-ticket").textContent = confirmadas
      ? `Ticket promedio ${moneda.format(montoConfirmado / confirmadas)}`
      : "Sin ventas confirmadas";
    document.getElementById("kpi-cotizado").textContent = `${moneda.format(cotizado)} en cotizaciones abiertas`;

    const proyectos = datos.proyectos;
    const pendientes = proyectos.reduce((s, f) => s + num(f.pendientes), 0);
    const vencidas = proyectos.reduce((s, f) => s + num(f.vencidas), 0);
    document.getElementById("kpi-tareas").textContent =
      `${entero.format(pendientes)} tareas pendientes, ${entero.format(vencidas)} vencidas`;
  }

  function pintarOportunidades(filas) {
    const meses = [...new Set(filas.map((f) => f.mes))].sort();
    const origenes = ["Correo automático", "Manual"];
    const colores = [css("--acento-1"), css("--acento-2")];
    dibujar("g-oportunidades", {
      type: "bar",
      data: {
        labels: meses.map(etiquetaMes),
        datasets: origenes.map((origen, i) => ({
          label: origen,
          data: meses.map((m) => filas.filter((f) => f.mes === m && f.origen === origen).reduce((s, f) => s + num(f.oportunidades), 0)),
          backgroundColor: colores[i],
          borderRadius: 6,
          borderSkipped: false,
          maxBarThickness: 46,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { delay: (ctx) => (ctx.type === "data" ? ctx.dataIndex * 90 + ctx.datasetIndex * 140 : 0) },
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } },
        },
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  function pintarVentas(filas) {
    dibujar("g-ventas", {
      data: {
        labels: filas.map((f) => etiquetaMes(f.mes)),
        datasets: [
          {
            type: "bar",
            label: "Monto confirmado",
            data: filas.map((f) => num(f.monto_confirmado)),
            backgroundColor: css("--acento-1"),
            borderRadius: 6,
            borderSkipped: false,
            maxBarThickness: 46,
            order: 2,
          },
          {
            type: "line",
            label: "Monto cotizado",
            data: filas.map((f) => num(f.monto_cotizado)),
            borderColor: css("--acento-3"),
            backgroundColor: css("--acento-3"),
            pointBackgroundColor: css("--acento-3"),
            pointRadius: 5,
            pointHoverRadius: 8,
            tension: 0.3,
            fill: false,
            borderDash: [6, 4],
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { delay: (ctx) => (ctx.type === "data" ? ctx.dataIndex * 110 : 0) },
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: { callback: (v) => moneda.format(v).replace(/\.00$/, "") } },
        },
        plugins: {
          legend: { position: "bottom" },
          tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${moneda.format(c.parsed.y)}` } },
        },
      },
    });
  }

  function pintarTareas(filas) {
    const total = filas.reduce((s, f) => s + num(f.tareas), 0);
    document.getElementById("total-tareas").textContent = entero.format(total);
    dibujar("g-tareas", {
      type: "doughnut",
      data: {
        labels: filas.map((f) => f.estado),
        datasets: [{
          data: filas.map((f) => num(f.tareas)),
          backgroundColor: filas.map((f) => COLORES_ESTADO[f.estado] || "#9aa3af"),
          borderWidth: 0,
          borderRadius: 8,
          spacing: 4,
          hoverOffset: 10,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "72%",
        animation: { animateRotate: true, animateScale: true },
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  function barra(porcentaje, completa) {
    return `<div class="barra${completa ? " completa" : ""}"><span data-ancho="${Math.min(Math.max(porcentaje, 0), 100)}"></span></div>`;
  }

  function animarBarras(contenedor) {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      contenedor.querySelectorAll(".barra span").forEach((s) => { s.style.width = `${s.dataset.ancho}%`; });
    }));
  }

  function pintarConversion(filas) {
    const el = document.getElementById("conversion");
    if (!filas.length) {
      el.innerHTML = '<p class="vacio">Sin oportunidades registradas</p>';
      return;
    }
    el.innerHTML = filas.map((f) => `
      <div class="origen-fila">
        <div class="origen-cabecera"><span>${escapar(f.origen)}</span><strong>${decimal.format(num(f.tasa_conversion_pct))} %</strong></div>
        ${barra(num(f.tasa_conversion_pct), num(f.tasa_conversion_pct) >= 100)}
        <div class="origen-detalle">
          <span>${entero.format(num(f.oportunidades))} oportunidades</span>
          <span>${entero.format(num(f.ganadas))} ganadas</span>
          <span>${entero.format(num(f.perdidas))} perdidas</span>
          <span>${moneda.format(num(f.monto_vendido))} vendido</span>
          <span>${moneda.format(num(f.ingreso_ponderado_abierto))} ponderado abierto</span>
        </div>
      </div>`).join("");
    animarBarras(el);
  }

  function pintarCiclo(filas) {
    const f = filas[0] || {};
    const pasos = [
      ["Oportunidades ganadas", entero.format(num(f.oportunidades_ganadas))],
      ["Correo a oportunidad ganada", duracion(f.minutos_correo_a_ganada)],
      ["Correo a venta confirmada", duracion(f.minutos_correo_a_venta)],
      ["Correo a proyecto creado", duracion(f.minutos_correo_a_proyecto)],
    ];
    document.getElementById("ciclo").innerHTML = pasos
      .map(([titulo, valor]) => `<li><span>${titulo}</span><strong>${valor}</strong></li>`).join("");
  }

  function pintarProyectos(filas) {
    const el = document.getElementById("proyectos");
    if (!filas.length) {
      el.innerHTML = '<li class="vacio">Sin proyectos activos</li>';
      return;
    }
    const ordenadas = [...filas].sort((a, b) => (num(a.avance_pct) >= 100) - (num(b.avance_pct) >= 100) || num(b.vencidas) - num(a.vencidas));
    el.innerHTML = ordenadas.map((f) => {
      const avance = num(f.avance_pct);
      const vencimiento = f.proximo_vencimiento
        ? new Date(`${f.proximo_vencimiento}T00:00:00`).toLocaleDateString("es-PE", { day: "2-digit", month: "short" })
        : null;
      return `
        <li>
          <div class="proyecto-cabecera">
            <div><strong>${escapar(f.proyecto)}</strong><br><span>${escapar(f.cliente || "Sin cliente")}</span></div>
            <strong>${decimal.format(avance)} %</strong>
          </div>
          ${barra(avance, avance >= 100)}
          <div class="etiquetas">
            <span class="etiqueta">${entero.format(num(f.hechas))} de ${entero.format(num(f.tareas))} tareas</span>
            ${num(f.vencidas) ? `<span class="etiqueta peligro">${entero.format(num(f.vencidas))} vencidas</span>` : ""}
            ${vencimiento ? `<span class="etiqueta">Próximo vencimiento ${vencimiento}</span>` : ""}
          </div>
        </li>`;
    }).join("");
    animarBarras(el);
  }

  function pintarStock(filas) {
    const el = document.getElementById("stock");
    if (!filas.length) {
      el.innerHTML = '<tr><td colspan="4" class="vacio">Todos los pedidos tienen stock disponible</td></tr>';
      return;
    }
    el.innerHTML = filas.map((f) => `
      <tr>
        <td title="${escapar(f.documentos)}">${escapar(f.producto)}<small>${escapar(f.codigo || "")} · ${entero.format(num(f.pedidos))} ${num(f.pedidos) === 1 ? "pedido" : "pedidos"}</small></td>
        <td>${decimal.format(num(f.cantidad_solicitada))}</td>
        <td>${decimal.format(num(f.stock_a_mano))}</td>
        <td class="faltante">${decimal.format(num(f.faltante))}</td>
      </tr>`).join("");
  }

  let ultimosDatos = null;

  function pintar(datos) {
    pintarKpis(datos);
    pintarOportunidades(datos["oportunidades-por-mes"]);
    pintarConversion(datos["conversion-por-origen"]);
    pintarVentas(datos["ventas-por-mes"]);
    pintarTareas(datos["tareas-por-estado"]);
    pintarCiclo(datos["tiempos-ciclo"]);
    pintarProyectos(datos.proyectos);
    pintarStock(datos["stock-insuficiente"]);
  }

  async function actualizar() {
    const estado = document.getElementById("estado");
    try {
      const respuesta = await fetch("/api/tablero", { cache: "no-store" });
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const datos = await respuesta.json();
      ultimosDatos = datos;
      if (datos.metabase_url) document.getElementById("enlace-metabase").href = datos.metabase_url;
      pintar(datos);
      estado.className = "estado ok";
      document.getElementById("actualizado").textContent = `Actualizado ${hora.format(new Date(datos.actualizado))}`;
    } catch (error) {
      estado.className = "estado error";
      document.getElementById("actualizado").textContent = "Sin conexión con la base de datos";
    }
  }

  document.getElementById("tema").addEventListener("click", () => {
    raiz.dataset.tema = raiz.dataset.tema === "oscuro" ? "claro" : "oscuro";
    localStorage.setItem("tema", raiz.dataset.tema);
    configurarChart();
    if (ultimosDatos) pintar(ultimosDatos);
  });

  configurarChart();
  actualizar();
  setInterval(actualizar, INTERVALO_MS);
})();
