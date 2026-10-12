// CHANGED: Admin/User dashboard charts — lightweight dependency-free canvas chart helper.
// Used by admin.js and dashboard.js. Handles empty datasets gracefully and shows tooltips.

const CHART_COLORS = {
    primary: '#2563eb',
    accent: '#3b82f6',
    success: '#16a34a',
    danger: '#dc2626',
    warning: '#d97706',
    grid: '#e2e8f0',
    text: '#64748b',
    muted: '#94a3b8',
};

function initChartCanvas(canvas) {
    if (!canvas) return null;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(rect.width || 300, 200);
    const computedHeight = rect.height || canvas.clientHeight || canvas.offsetHeight || 180;
    const h = Math.max(computedHeight, 150);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx, w, h, canvas };
}

// CHANGED: Admin/User dashboard charts — wrap long empty-state / axis text into lines.
function wrapChartText(ctx, text, maxWidth) {
    const words = String(text).split(/\s+/);
    const lines = [];
    let line = '';
    for (const word of words) {
        const candidate = line ? line + ' ' + word : word;
        if (ctx.measureText(candidate).width > maxWidth && line) {
            lines.push(line);
            line = word;
        } else {
            line = candidate;
        }
    }
    if (line) lines.push(line);
    return lines;
}

// CHANGED: Admin/User dashboard charts — friendly message when a metric has no data.
function drawEmptyChart(canvas, message) {
    const ready = initChartCanvas(canvas);
    if (!ready) return;
    const { ctx, w, h } = ready;
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = CHART_COLORS.text;
    ctx.font = '13px -apple-system, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const lines = wrapChartText(ctx, message || 'No data available yet.', w - 48);
    const lineHeight = 18;
    const startY = (h - lines.length * lineHeight) / 2 + lineHeight / 2;
    lines.forEach((line, i) => {
        ctx.fillText(line, w / 2, startY + i * lineHeight);
    });
}

function computeNiceMax(value) {
    if (!value || value <= 0) return 1;
    const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
    const norm = value / magnitude;
    let step;
    if (norm <= 1) step = 1;
    else if (norm <= 2) step = 2;
    else if (norm <= 5) step = 5;
    else step = 10;
    return step * magnitude;
}

function attachChartTooltip(canvas, resolver) {
    if (!canvas || canvas.__chartTooltip) return;
    const tip = document.createElement('div');
    tip.className = 'chart-tooltip';
    document.body.appendChild(tip);
    canvas.__chartTooltip = tip;
    canvas.addEventListener('mousemove', (e) => {
        const text = resolver(e);
        if (!text) {
            tip.style.display = 'none';
            return;
        }
        tip.textContent = text;
        tip.style.display = 'block';
        tip.style.left = (e.clientX + 14) + 'px';
        tip.style.top = (e.clientY - 12) + 'px';
    });
    canvas.addEventListener('mouseleave', () => {
        tip.style.display = 'none';
    });
}

function drawChartAxes(ready, niceMax, xLabel, yLabel) {
    const { ctx, w, h } = ready;
    const padL = 44, padR = 14, padT = 18, padB = 34;
    const plotW = w - padL - padR;
    const plotH = h - padT - padB;
    const TICKS = 4;

    ctx.strokeStyle = CHART_COLORS.grid;
    ctx.fillStyle = CHART_COLORS.muted;
    ctx.font = '10px -apple-system, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';

    for (let k = 0; k <= TICKS; k++) {
        const value = (niceMax * k) / TICKS;
        const y = padT + plotH - (value / niceMax) * plotH;
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(padL + plotW, y);
        ctx.stroke();
        ctx.fillText(String(Math.round(value)), padL - 8, y);
    }

    ctx.fillStyle = CHART_COLORS.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'alphabetic';
    if (xLabel) {
        ctx.font = '11px -apple-system, "Segoe UI", Roboto, sans-serif';
        ctx.fillText(xLabel, padL + plotW / 2, h - 6);
    }
    if (yLabel) {
        ctx.save();
        ctx.translate(14, padT + plotH / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.textAlign = 'center';
        ctx.font = '11px -apple-system, "Segoe UI", Roboto, sans-serif';
        ctx.fillText(yLabel, 0, 0);
        ctx.restore();
    }

    return { padL, padR, padT, padB, plotW, plotH };
}

// CHANGED: Admin/User dashboard charts — line / time-series chart.
function drawLineChart(canvas, config) {
    const ready = initChartCanvas(canvas);
    if (!ready) return;
    const labels = (config.labels || []).map((l) => String(l));
    const values = (config.values || []).map((v) => Number(v) || 0);
    if (labels.length === 0) {
        drawEmptyChart(canvas, config.emptyMessage || 'No data available yet.');
        return;
    }

    const { ctx, w, h } = ready;
    const niceMax = computeNiceMax(Math.max.apply(null, values));
    const { padL, padR, padT, plotW, plotH } = drawChartAxes(ready, niceMax, config.xLabel, config.yLabel);
    const n = labels.length;

    const xFor = (i) => (n === 1 ? padL + plotW / 2 : padL + (i / (n - 1)) * plotW);
    const yFor = (v) => padT + plotH - (v / niceMax) * plotH;

    ctx.strokeStyle = CHART_COLORS.primary;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.beginPath();
    values.forEach((v, i) => {
        const x = xFor(i);
        const y = yFor(v);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.fillStyle = CHART_COLORS.primary;
    values.forEach((v, i) => {
        ctx.beginPath();
        ctx.arc(xFor(i), yFor(v), 3.5, 0, Math.PI * 2);
        ctx.fill();
    });

    const labelStep = n > 12 ? Math.ceil(n / 12) : 1;
    ctx.fillStyle = CHART_COLORS.muted;
    ctx.font = '10px -apple-system, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    labels.forEach((label, i) => {
        if (i % labelStep !== 0 && i !== n - 1) return;
        ctx.fillText(label, xFor(i), padT + plotH + 8);
    });

    attachChartTooltip(canvas, (e) => {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        if (x < padL - 6 || x > padL + plotW + 6 || y < padT - 6 || y > padT + plotH + 6) return null;
        const frac = Math.max(0, Math.min(1, (x - padL) / plotW));
        const idx = n === 1 ? 0 : Math.round(frac * (n - 1));
        return labels[idx] + ': ' + values[idx];
    });

    return { canvas, labels, values };
}

// CHANGED: Admin/User dashboard charts — bar chart.
function drawBarChart(canvas, config) {
    const ready = initChartCanvas(canvas);
    if (!ready) return;
    const labels = (config.labels || []).map((l) => String(l));
    const values = (config.values || []).map((v) => Number(v) || 0);
    if (labels.length === 0) {
        drawEmptyChart(canvas, config.emptyMessage || 'No data available yet.');
        return;
    }

    const { ctx, w, h } = ready;
    const niceMax = computeNiceMax(Math.max.apply(null, values));
    const { padL, padR, padT, plotW, plotH } = drawChartAxes(ready, niceMax, config.xLabel, config.yLabel);
    const n = labels.length;
    const slot = plotW / n;
    const barWidth = Math.max(Math.min(slot * 0.6, 46), 8);
    const baselineY = padT + plotH;

    ctx.fillStyle = CHART_COLORS.primary;
    values.forEach((v, i) => {
        const barH = (v / niceMax) * plotH;
        const x = padL + slot * i + (slot - barWidth) / 2;
        ctx.fillRect(x, baselineY - barH, barWidth, barH);
    });

    const labelStep = n > 12 ? Math.ceil(n / 12) : 1;
    ctx.fillStyle = CHART_COLORS.muted;
    ctx.font = '10px -apple-system, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    labels.forEach((label, i) => {
        if (i % labelStep !== 0 && i !== n - 1) return;
        ctx.fillText(label, padL + slot * i + slot / 2, padT + plotH + 8);
    });

    if (n <= 12) {
        ctx.fillStyle = CHART_COLORS.text;
        ctx.font = '10px -apple-system, "Segoe UI", Roboto, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        values.forEach((v, i) => {
            const barH = (v / niceMax) * plotH;
            ctx.fillText(String(Math.round(v)), padL + slot * i + slot / 2, baselineY - barH - 4);
        });
    }

    attachChartTooltip(canvas, (e) => {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        if (x < padL - 6 || x > padL + plotW + 6 || y < padT - 6 || y > padT + plotH + 6) return null;
        const idx = Math.max(0, Math.min(n - 1, Math.floor((x - padL) / slot)));
        return labels[idx] + ': ' + values[idx];
    });

    return { canvas, labels, values };
}

// CHANGED: Admin/User dashboard charts — group records by local calendar day.
function buildDateCountSeries(records, field) {
    const counts = {};
    (records || []).forEach((record) => {
        if (!record || !record[field]) return;
        const d = new Date(record[field]);
        if (isNaN(d.getTime())) return;
        const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
        counts[key] = (counts[key] || 0) + 1;
    });
    const labels = Object.keys(counts).sort();
    return { labels: labels, values: labels.map((k) => counts[k]) };
}