const API_URL = 'http://127.0.0.1:5000/api';
let charts = {};
let currentUsers = [];
let graphRendered = false;
let swipeDeck = [];
let swipeIndex = 0;
let likedCount = 0;
let selectedCareerOppId = null;

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initDashboard();
    
    // Bind Modals
    document.getElementById('btn-open-pipeline').addEventListener('click', () => {
        document.getElementById('pipeline-modal').classList.remove('hidden');
    });
    document.getElementById('btn-cancel-pipeline').addEventListener('click', () => {
        document.getElementById('pipeline-modal').classList.add('hidden');
    });
    document.getElementById('btn-start-pipeline').addEventListener('click', startPipelineStream);
    document.getElementById('btn-close-sim').addEventListener('click', () => {
        document.getElementById('simulation-overlay').classList.add('hidden');
        initDashboard();
    });
    
    document.getElementById('btn-add-student').addEventListener('click', () => {
        document.getElementById('student-id').value = '';
        document.getElementById('student-name').value = '';
        document.getElementById('student-profile').value = '';
        document.getElementById('student-interests').value = '';
        document.getElementById('student-skills').value = '';
        document.getElementById('student-modal-title').innerText = 'Add Student';
        document.getElementById('student-modal').classList.remove('hidden');
    });
    document.getElementById('btn-close-student').addEventListener('click', () => {
        document.getElementById('student-modal').classList.add('hidden');
    });
    document.getElementById('btn-save-student').addEventListener('click', saveStudent);
    
    // Swipe buttons
    document.getElementById('btn-swipe-left').addEventListener('click', () => swipeAction('rejected'));
    document.getElementById('btn-swipe-right').addEventListener('click', () => swipeAction('liked'));
});

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            
            const targetView = item.getAttribute('data-tab');
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById(`view-${targetView}`).classList.add('active');
            
            document.getElementById('current-page-title').innerText = item.querySelector('span').innerText;
            
            if (targetView === 'recommendations' && document.getElementById('user-select').value) {
                loadRecommendations(document.getElementById('user-select').value);
            }
            if (targetView === 'clusters' && !graphRendered) {
                setTimeout(() => renderClusterGraph(), 100);
            }
            if (targetView === 'discover') {
                const uid = document.getElementById('user-select').value;
                if (uid) loadSwipeDeck(uid);
            }
            if (targetView === 'career') {
                const uid = document.getElementById('user-select').value;
                if (uid) loadLikedOpportunities(uid);
            }
        });
    });
}

async function initDashboard() {
    await fetchStats();
    await fetchClusters();
    await fetchUsers();
}

async function fetchStats() {
    try {
        const res = await fetch(`${API_URL}/stats`);
        const data = await res.json();
        animateValue('metric-opps', 0, data.totalOpportunities, 1000);
        animateValue('metric-users', 0, data.totalUsers, 1000);
        animateValue('metric-clusters', 0, data.totalClusters, 1000);
        renderTypesChart(data.opportunitiesByType);
    } catch (e) { console.error(e); }
}

async function fetchClusters() {
    try {
        const res = await fetch(`${API_URL}/clusters`);
        const data = await res.json();
        renderClustersChart(data);
    } catch (e) { console.error(e); }
}

function renderClusterGraph() {
    fetch(`${API_URL}/clusters/graph`)
        .then(res => res.json())
        .then(graphData => {
            const container = document.getElementById('clusters-graph-container');
            container.innerHTML = '';
            graphRendered = true;

            const canvas = document.createElement('canvas');
            const dpr = window.devicePixelRatio || 1;
            const W = container.clientWidth || 800;
            const H = container.clientHeight || 500;
            canvas.width = W * dpr;
            canvas.height = H * dpr;
            canvas.style.width = W + 'px';
            canvas.style.height = H + 'px';
            canvas.style.cursor = 'grab';
            container.appendChild(canvas);
            const ctx = canvas.getContext('2d');
            ctx.scale(dpr, dpr);

            // --- build simulation nodes ---
            const nodes = graphData.nodes.map(n => ({
                ...n,
                x: W / 2 + (Math.random() - 0.5) * W * 0.6,
                y: H / 2 + (Math.random() - 0.5) * H * 0.6,
                vx: 0, vy: 0,
                radius: n.type === 'cluster' ? 28 : 9,
            }));
            const nodeMap = {};
            nodes.forEach(n => nodeMap[n.id] = n);

            const links = graphData.links.map(l => ({
                source: nodeMap[l.source],
                target: nodeMap[l.target],
            })).filter(l => l.source && l.target);

            // cluster color palette
            const clusterColors = [
                '#00f3ff', '#b026ff', '#ff2a85', '#00b8ff',
                '#7000ff', '#22d3ee', '#e879f9', '#facc15',
                '#34d399', '#fb923c', '#f472b6', '#a78bfa'
            ];
            function colorForGroup(g) { return clusterColors[g % clusterColors.length]; }

            // --- interaction state ---
            let dragNode = null;
            let hoverNode = null;
            let offsetX = 0, offsetY = 0;

            function getNodeAt(mx, my) {
                for (let i = nodes.length - 1; i >= 0; i--) {
                    const n = nodes[i];
                    const dx = mx - n.x, dy = my - n.y;
                    const hitR = n.radius + 4;
                    if (dx * dx + dy * dy < hitR * hitR) return n;
                }
                return null;
            }

            canvas.addEventListener('mousedown', e => {
                const rect = canvas.getBoundingClientRect();
                const mx = e.clientX - rect.left, my = e.clientY - rect.top;
                dragNode = getNodeAt(mx, my);
                if (dragNode) {
                    offsetX = mx - dragNode.x;
                    offsetY = my - dragNode.y;
                    canvas.style.cursor = 'grabbing';
                }
            });
            canvas.addEventListener('mousemove', e => {
                const rect = canvas.getBoundingClientRect();
                const mx = e.clientX - rect.left, my = e.clientY - rect.top;
                if (dragNode) {
                    dragNode.x = mx - offsetX;
                    dragNode.y = my - offsetY;
                    dragNode.vx = 0;
                    dragNode.vy = 0;
                } else {
                    const h = getNodeAt(mx, my);
                    hoverNode = h;
                    canvas.style.cursor = h ? 'pointer' : 'grab';
                }
            });
            canvas.addEventListener('mouseup', () => { dragNode = null; canvas.style.cursor = 'grab'; });
            canvas.addEventListener('mouseleave', () => { dragNode = null; hoverNode = null; });

            canvas.addEventListener('click', e => {
                const rect = canvas.getBoundingClientRect();
                const mx = e.clientX - rect.left, my = e.clientY - rect.top;
                const n = getNodeAt(mx, my);
                if (n && n.type === 'opportunity' && n.url) {
                    window.open(n.url, '_blank');
                }
            });

            // --- physics ---
            const REPULSION = 800;
            const SPRING_K = 0.005;
            const SPRING_LEN = 120;
            const DAMPING = 0.85;
            const CENTER_PULL = 0.0003;

            function simulate() {
                // repulsion between all nodes
                for (let i = 0; i < nodes.length; i++) {
                    for (let j = i + 1; j < nodes.length; j++) {
                        const a = nodes[i], b = nodes[j];
                        let dx = a.x - b.x, dy = a.y - b.y;
                        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                        let force = REPULSION / (dist * dist);
                        let fx = dx / dist * force, fy = dy / dist * force;
                        a.vx += fx; a.vy += fy;
                        b.vx -= fx; b.vy -= fy;
                    }
                }
                // spring attraction along edges
                for (const l of links) {
                    let dx = l.target.x - l.source.x;
                    let dy = l.target.y - l.source.y;
                    let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    let force = (dist - SPRING_LEN) * SPRING_K;
                    let fx = dx / dist * force, fy = dy / dist * force;
                    l.source.vx += fx; l.source.vy += fy;
                    l.target.vx -= fx; l.target.vy -= fy;
                }
                // gentle center pull
                for (const n of nodes) {
                    n.vx += (W / 2 - n.x) * CENTER_PULL;
                    n.vy += (H / 2 - n.y) * CENTER_PULL;
                }
                // integrate
                for (const n of nodes) {
                    if (n === dragNode) continue;
                    n.vx *= DAMPING; n.vy *= DAMPING;
                    n.x += n.vx; n.y += n.vy;
                    // keep in bounds
                    n.x = Math.max(n.radius, Math.min(W - n.radius, n.x));
                    n.y = Math.max(n.radius, Math.min(H - n.radius, n.y));
                }
            }

            // --- drawing ---
            function draw() {
                ctx.clearRect(0, 0, W, H);

                // edges with arrows
                for (const l of links) {
                    const sx = l.source.x, sy = l.source.y;
                    const tx = l.target.x, ty = l.target.y;
                    const col = colorForGroup(l.target.group);

                    // line
                    ctx.beginPath();
                    ctx.moveTo(sx, sy);
                    ctx.lineTo(tx, ty);
                    ctx.strokeStyle = col.replace(')', ',0.15)').replace('rgb', 'rgba').replace('#', '');
                    // simpler: just use rgba
                    ctx.globalAlpha = 0.18;
                    ctx.strokeStyle = col;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                    ctx.globalAlpha = 1;

                    // arrow head
                    const angle = Math.atan2(ty - sy, tx - sx);
                    const arrowDist = l.target.radius + 6;
                    const ax = tx - Math.cos(angle) * arrowDist;
                    const ay = ty - Math.sin(angle) * arrowDist;
                    const arrowSize = 5;
                    ctx.beginPath();
                    ctx.moveTo(ax, ay);
                    ctx.lineTo(ax - arrowSize * Math.cos(angle - 0.4), ay - arrowSize * Math.sin(angle - 0.4));
                    ctx.lineTo(ax - arrowSize * Math.cos(angle + 0.4), ay - arrowSize * Math.sin(angle + 0.4));
                    ctx.closePath();
                    ctx.globalAlpha = 0.35;
                    ctx.fillStyle = col;
                    ctx.fill();
                    ctx.globalAlpha = 1;
                }

                // nodes
                for (const n of nodes) {
                    const col = colorForGroup(n.group);
                    const isCluster = n.type === 'cluster';
                    const isHover = n === hoverNode;
                    const r = n.radius;

                    // outer glow
                    const glowR = isCluster ? 50 : 22;
                    const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glowR);
                    grad.addColorStop(0, col);
                    grad.addColorStop(1, 'transparent');
                    ctx.globalAlpha = isHover ? 0.35 : 0.12;
                    ctx.beginPath();
                    ctx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
                    ctx.fillStyle = grad;
                    ctx.fill();
                    ctx.globalAlpha = 1;

                    // outer ring
                    ctx.beginPath();
                    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
                    ctx.fillStyle = isCluster ? col : 'rgba(0,0,0,0.5)';
                    ctx.fill();
                    ctx.lineWidth = isHover ? 2.5 : 1.5;
                    ctx.strokeStyle = col;
                    ctx.stroke();

                    if (!isCluster) {
                        // inner dot (magenta center)
                        ctx.beginPath();
                        ctx.arc(n.x, n.y, 3.5, 0, Math.PI * 2);
                        ctx.fillStyle = '#b026ff';
                        ctx.fill();
                    }

                    // label
                    if (isCluster || isHover) {
                        const label = n.name.length > 28 ? n.name.substring(0, 26) + '…' : n.name;
                        ctx.font = isCluster ? '600 12px Outfit' : '500 11px Outfit';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'top';

                        // background pill
                        const tw = ctx.measureText(label).width + 12;
                        const th = 18;
                        const tx = n.x - tw / 2;
                        const ty = n.y + r + 6;
                        ctx.fillStyle = 'rgba(7,9,19,0.85)';
                        ctx.beginPath();
                        ctx.roundRect(tx, ty, tw, th, 6);
                        ctx.fill();
                        ctx.strokeStyle = 'rgba(255,255,255,0.15)';
                        ctx.lineWidth = 0.5;
                        ctx.stroke();

                        ctx.fillStyle = isCluster ? col : '#e2e8f0';
                        ctx.fillText(label, n.x, ty + 3);
                    }
                }

                // tooltip for hovered node
                if (hoverNode && hoverNode.type === 'opportunity') {
                    const n = hoverNode;
                    const label = n.name;
                    ctx.font = '500 13px Outfit';
                    const tw = ctx.measureText(label).width + 20;
                    const th = 32;
                    const tx = Math.min(n.x + 15, W - tw - 10);
                    const ty = Math.max(n.y - 40, 10);

                    ctx.fillStyle = 'rgba(18,22,38,0.95)';
                    ctx.beginPath();
                    ctx.roundRect(tx, ty, tw, th, 8);
                    ctx.fill();
                    ctx.strokeStyle = colorForGroup(n.group);
                    ctx.lineWidth = 1;
                    ctx.stroke();

                    ctx.fillStyle = '#fff';
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(label, tx + 10, ty + th / 2);
                }
            }

            function loop() {
                simulate();
                draw();
                requestAnimationFrame(loop);
            }
            loop();
        });
}

async function fetchUsers() {
    try {
        const res = await fetch(`${API_URL}/users`);
        currentUsers = await res.json();
        
        // Update Dropdown
        const select = document.getElementById('user-select');
        select.innerHTML = '<option value="">-- Select a User --</option>';
        currentUsers.forEach(u => {
            const opt = document.createElement('option');
            opt.value = u.id;
            opt.textContent = u.name;
            opt.dataset.skills = u.skills;
            select.appendChild(opt);
        });
        select.onchange = (e) => {
            if (e.target.value) {
                const selectedOpt = e.target.options[e.target.selectedIndex];
                document.getElementById('user-skills-badge').innerText = `Skills: ${selectedOpt.dataset.skills}`;
                loadRecommendations(e.target.value);
            } else {
                document.getElementById('recs-list-container').innerHTML = '<p class="text-muted">Select a user to view recommendations.</p>';
                document.getElementById('notifs-list-container').innerHTML = '';
            }
        };
        
        // Update Table
        renderStudentsTable();
    } catch (e) { console.error(e); }
}

// --- Student Management ---

function renderStudentsTable() {
    const tbody = document.getElementById('students-tbody');
    tbody.innerHTML = '';
    currentUsers.forEach(u => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${u.name}</td>
            <td>${u.profile}</td>
            <td>${u.skills.substring(0, 30)}${u.skills.length > 30 ? '...' : ''}</td>
            <td>
                <button class="btn-edit" onclick="editStudent(${u.id})"><i class="fa-solid fa-pen-to-square"></i></button>
                <button class="btn-danger" onclick="deleteStudent(${u.id})"><i class="fa-solid fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function editStudent(id) {
    const u = currentUsers.find(x => x.id === id);
    if(!u) return;
    document.getElementById('student-id').value = u.id;
    document.getElementById('student-name').value = u.name;
    document.getElementById('student-profile').value = u.profile;
    document.getElementById('student-interests').value = u.interests;
    document.getElementById('student-skills').value = u.skills;
    document.getElementById('student-modal-title').innerText = 'Edit Student';
    document.getElementById('student-modal').classList.remove('hidden');
}

async function saveStudent() {
    const id = document.getElementById('student-id').value;
    const data = {
        name: document.getElementById('student-name').value,
        profile: document.getElementById('student-profile').value,
        interests: document.getElementById('student-interests').value,
        skills: document.getElementById('student-skills').value
    };
    
    try {
        if(id) {
            await fetch(`${API_URL}/users/${id}`, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        } else {
            await fetch(`${API_URL}/users`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
        }
        document.getElementById('student-modal').classList.add('hidden');
        fetchUsers();
    } catch(e) { console.error(e); }
}

async function deleteStudent(id) {
    if(confirm("Are you sure you want to delete this student and their recommendations?")) {
        try {
            await fetch(`${API_URL}/users/${id}`, { method: 'DELETE' });
            fetchUsers();
        } catch(e) { console.error(e); }
    }
}

// --- Recs ---

async function loadRecommendations(userId) {
    try {
        const resRecs = await fetch(`${API_URL}/users/${userId}/recommendations`);
        const recs = await resRecs.json();
        const recsContainer = document.getElementById('recs-list-container');
        recsContainer.innerHTML = '';
        if (recs.length === 0) recsContainer.innerHTML = '<p class="text-muted">No recommendations found. Run the pipeline.</p>';
        else {
            recs.forEach(rec => {
                const tagsHtml = rec.tags ? rec.tags.split(',').map(t => `<span class="tag">${t.trim()}</span>`).join('') : '';
                recsContainer.insertAdjacentHTML('beforeend', `
                    <div class="opp-card">
                        <div class="opp-header">
                            <div class="opp-title">${rec.title}</div>
                            <div class="opp-score">${(rec.score * 100).toFixed(1)}%</div>
                        </div>
                        <div class="opp-meta">
                            <span><i class="fa-solid fa-layer-group"></i> ${rec.type.replace('_', ' ')}</span>
                            <span><i class="fa-solid fa-globe"></i> ${rec.source}</span>
                        </div>
                        <div class="opp-tags">${tagsHtml}</div>
                    </div>
                `);
            });
        }
        
        const resNotifs = await fetch(`${API_URL}/users/${userId}/notifications`);
        const notifs = await resNotifs.json();
        const notifsContainer = document.getElementById('notifs-list-container');
        notifsContainer.innerHTML = '';
        if (notifs.length === 0) notifsContainer.innerHTML = '<p class="text-muted">No new alerts.</p>';
        else {
            notifs.forEach(n => {
                const d = n.timestamp ? new Date(n.timestamp).toLocaleDateString() : 'Just now';
                notifsContainer.insertAdjacentHTML('beforeend', `
                    <div class="notif-card">
                        <div class="notif-title">${n.title}</div>
                        <div class="notif-time"><i class="fa-regular fa-clock"></i> ${d}</div>
                    </div>
                `);
            });
        }
    } catch (e) { console.error(e); }
}

// --- SSE Pipeline Simulation ---

function startPipelineStream() {
    // Get targets
    const cbs = document.querySelectorAll('.target-cb:checked');
    const targets = Array.from(cbs).map(cb => cb.value).join(',');
    
    // Hide modal, show overlay
    document.getElementById('pipeline-modal').classList.add('hidden');
    document.getElementById('simulation-overlay').classList.remove('hidden');
    
    const logsBox = document.getElementById('sim-logs');
    logsBox.innerHTML = '';
    document.getElementById('btn-close-sim').classList.add('hidden');
    
    // Start SSE
    const source = new EventSource(`${API_URL}/stream-pipeline?targets=${targets}`);
    
    source.onmessage = function(event) {
        const data = JSON.parse(event.data);
        const div = document.createElement('div');
        div.className = 'log-line';
        
        if(data.status === 'info') {
            div.classList.add('log-info');
            div.innerText = `> ${data.message}`;
        } else if(data.status === 'success') {
            div.classList.add('log-info');
            div.innerText = `[SUCCESS] ${data.message}`;
            source.close();
            document.getElementById('btn-close-sim').classList.remove('hidden');
        } else {
            div.innerText = data.message;
        }
        
        logsBox.appendChild(div);
        logsBox.scrollTop = logsBox.scrollHeight;
    };
    
    source.onerror = function() {
        console.error("SSE Error");
        source.close();
        document.getElementById('btn-close-sim').classList.remove('hidden');
    };
}

// --- Utilities ---

function animateValue(id, start, end, duration) {
    if (start === end) return;
    let obj = document.getElementById(id);
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
}

Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Outfit', sans-serif";

function renderTypesChart(typesData) {
    const ctx = document.getElementById('chart-types');
    if (charts.types) charts.types.destroy();
    const labels = Object.keys(typesData).map(t => t.replace('_', ' ').toUpperCase());
    const data = Object.values(typesData);
    charts.types = new Chart(ctx, {
        type: 'doughnut',
        data: { labels: labels, datasets: [{ data: data, backgroundColor: ['#00f3ff', '#b026ff', '#ff2a85', '#00b8ff', '#7000ff'], borderWidth: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 12, usePointStyle: true } } } }
    });
}

function renderClustersChart(clusters) {
    const ctx = document.getElementById('chart-clusters');
    if (charts.clusters) charts.clusters.destroy();
    const topClusters = clusters.slice(0, 5);
    charts.clusters = new Chart(ctx, {
        type: 'bar',
        data: { labels: topClusters.map(c => c.name), datasets: [{ data: topClusters.map(c => c.size), backgroundColor: 'rgba(176, 38, 255, 0.6)', borderRadius: 4 }] },
        options: { responsive: true, maintainAspectRatio: false, scales: { x: { ticks: { display: false } } }, plugins: { legend: { display: false } } }
    });
}

function renderClustersList(clusters) {
    const container = document.getElementById('clusters-list-container');
    if (!container) return;
    container.innerHTML = '';
    if (clusters.length === 0) { container.innerHTML = '<p class="text-muted p-4">No clusters found.</p>'; return; }
    clusters.forEach(c => {
        container.insertAdjacentHTML('beforeend', `<div class="cluster-item"><div class="cluster-name"><i class="fa-solid fa-circle-nodes" style="color:var(--accent-cyan); margin-right: 10px;"></i> ${c.name}</div><div class="cluster-size">${c.size} items</div></div>`);
    });
}

// ===== SWIPE DECK =====

async function loadSwipeDeck(userId) {
    try {
        const res = await fetch(`${API_URL}/users/${userId}/swipe-deck`);
        swipeDeck = await res.json();
        swipeIndex = 0;
        likedCount = 0;
        document.getElementById('swipe-counter').innerText = `${likedCount} liked`;
        if (swipeDeck.length > 0) {
            document.getElementById('swipe-actions').style.display = 'flex';
            renderSwipeCard();
        } else {
            document.getElementById('swipe-deck').innerHTML = '<div class="swipe-placeholder glass-panel"><i class="fa-solid fa-check-circle"></i><p>No more opportunities to swipe!</p></div>';
            document.getElementById('swipe-actions').style.display = 'none';
        }
    } catch(e) { console.error(e); }
}

function renderSwipeCard() {
    if (swipeIndex >= swipeDeck.length) {
        document.getElementById('swipe-deck').innerHTML = '<div class="swipe-placeholder glass-panel"><i class="fa-solid fa-check-circle"></i><p>You\'ve seen all opportunities!</p></div>';
        document.getElementById('swipe-actions').style.display = 'none';
        return;
    }
    const opp = swipeDeck[swipeIndex];
    const tagsHtml = opp.tags ? opp.tags.split(',').slice(0, 4).map(t => `<span class="tag">${t.trim()}</span>`).join('') : '';
    const deck = document.getElementById('swipe-deck');
    deck.innerHTML = `
        <div class="swipe-card" id="current-card">
            <div class="swipe-overlay like" id="overlay-like">LIKE</div>
            <div class="swipe-overlay nope" id="overlay-nope">NOPE</div>
            <div>
                <div class="card-type"><i class="fa-solid fa-layer-group"></i> ${opp.type.replace('_', ' ')}</div>
                <div class="card-title">${opp.title}</div>
                <div class="card-desc">${opp.description || 'No description available.'}</div>
                <div class="card-tags">${tagsHtml}</div>
            </div>
            <div class="card-footer">
                <div class="card-source"><i class="fa-solid fa-globe"></i> ${opp.source || 'Unknown'}</div>
                <div class="card-match">${(opp.score * 100).toFixed(0)}% match</div>
            </div>
        </div>
    `;
    initSwipeDrag(document.getElementById('current-card'));
}

function initSwipeDrag(card) {
    let startX = 0, currentX = 0, isDragging = false;
    
    card.addEventListener('mousedown', e => {
        isDragging = true;
        startX = e.clientX;
        card.style.transition = 'none';
    });
    
    document.addEventListener('mousemove', e => {
        if (!isDragging) return;
        currentX = e.clientX - startX;
        const rotate = currentX * 0.05;
        card.style.transform = `translateX(${currentX}px) rotate(${rotate}deg)`;
        
        const likeOverlay = document.getElementById('overlay-like');
        const nopeOverlay = document.getElementById('overlay-nope');
        if (currentX > 50) {
            likeOverlay.style.opacity = Math.min((currentX - 50) / 100, 1);
            nopeOverlay.style.opacity = 0;
        } else if (currentX < -50) {
            nopeOverlay.style.opacity = Math.min((-currentX - 50) / 100, 1);
            likeOverlay.style.opacity = 0;
        } else {
            likeOverlay.style.opacity = 0;
            nopeOverlay.style.opacity = 0;
        }
    });
    
    document.addEventListener('mouseup', () => {
        if (!isDragging) return;
        isDragging = false;
        
        if (currentX > 120) {
            swipeAction('liked');
        } else if (currentX < -120) {
            swipeAction('rejected');
        } else {
            card.style.transition = 'transform 0.3s ease';
            card.style.transform = 'translateX(0) rotate(0)';
            document.getElementById('overlay-like').style.opacity = 0;
            document.getElementById('overlay-nope').style.opacity = 0;
        }
        currentX = 0;
    });
}

async function swipeAction(action) {
    const opp = swipeDeck[swipeIndex];
    if (!opp) return;
    
    const userId = document.getElementById('user-select').value;
    if (!userId) return;
    
    const card = document.getElementById('current-card');
    if (card) {
        card.style.transition = 'all 0.4s ease';
        if (action === 'liked') {
            card.style.animation = 'swipeRight 0.4s forwards';
            likedCount++;
            document.getElementById('swipe-counter').innerText = `${likedCount} liked`;
        } else {
            card.style.animation = 'swipeLeft 0.4s forwards';
        }
    }
    
    try {
        await fetch(`${API_URL}/users/${userId}/swipe`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ opportunity_id: opp.id, action: action })
        });
    } catch(e) { console.error(e); }
    
    setTimeout(() => {
        swipeIndex++;
        renderSwipeCard();
    }, 400);
}

// ===== CAREER TOOLS =====

async function loadLikedOpportunities(userId) {
    try {
        const res = await fetch(`${API_URL}/users/${userId}/liked`);
        const liked = await res.json();
        const container = document.getElementById('liked-list');
        container.innerHTML = '';
        if (liked.length === 0) {
            container.innerHTML = '<p class="text-muted">No liked opportunities yet. Swipe right on some in the Discover tab!</p>';
            return;
        }
        liked.forEach(opp => {
            const div = document.createElement('div');
            div.className = 'liked-item';
            div.innerHTML = `<div class="li-title">${opp.title}</div><div class="li-type">${opp.type.replace('_', ' ')}</div>`;
            div.addEventListener('click', () => selectCareerOpp(opp, div));
            container.appendChild(div);
        });
    } catch(e) { console.error(e); }
}

function selectCareerOpp(opp, el) {
    document.querySelectorAll('.liked-item').forEach(i => i.classList.remove('active'));
    el.classList.add('active');
    selectedCareerOppId = opp.id;
    document.getElementById('career-opp-title').innerText = opp.title;
    document.getElementById('career-actions').style.display = 'flex';
    document.getElementById('career-output').innerHTML = '<p class="text-muted">Click a button above to generate a document with Gemini AI.</p>';
    document.getElementById('career-download').classList.add('hidden');
}

async function generateDoc(type) {
    const userId = document.getElementById('user-select').value;
    if (!userId || !selectedCareerOppId) return;
    
    const output = document.getElementById('career-output');
    output.innerHTML = '<div class="career-loading"><i class="fa-solid fa-circle-notch fa-spin"></i> Gemini AI is generating...</div>';
    document.getElementById('career-download').classList.add('hidden');
    
    try {
        const res = await fetch(`${API_URL}/generate/${type}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_id: parseInt(userId), opportunity_id: selectedCareerOppId })
        });
        const data = await res.json();
        if (data.error) {
            output.innerHTML = `<p style="color:var(--accent-pink)">Error: ${data.error}</p>`;
            return;
        }
        // Render in iframe for isolation and printing
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        iframe.style.background = 'white';
        output.innerHTML = '';
        output.appendChild(iframe);
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write(data.html);
        doc.close();
        // Make editable
        doc.designMode = 'on';
        document.getElementById('career-download').classList.remove('hidden');
    } catch(e) {
        output.innerHTML = `<p style="color:var(--accent-pink)">Failed to generate. Is your GEMINI_API_KEY set in .env?</p>`;
        console.error(e);
    }
}

function printDoc() {
    const iframe = document.querySelector('#career-output iframe');
    if (iframe) {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
    }
}
