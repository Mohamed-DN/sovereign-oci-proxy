/**
 * NeroNet - Interactive Mesh Topology Visualizer & Control Simulation (DARKNERO.COM)
 */

document.addEventListener('DOMContentLoaded', () => {
  initMeshCanvas();
  initHUDControls();
  initClipboard();
});

// Canvas Particle Mesh Simulator
function initMeshCanvas() {
  const canvas = document.getElementById('mesh-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let width, height;
  let particles = [];
  let mouse = { x: null, y: null, radius: 150 };

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    createParticles();
  }

  window.addEventListener('resize', resize);

  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  });

  window.addEventListener('mouseout', () => {
    mouse.x = null;
    mouse.y = null;
  });

  class NodeParticle {
    constructor() {
      this.x = Math.random() * width;
      this.y = Math.random() * height;
      this.vx = (Math.random() - 0.5) * 0.8;
      this.vy = (Math.random() - 0.5) * 0.8;
      this.radius = Math.random() * 2 + 2;
      this.isExit = Math.random() > 0.8;
      this.isRelay = !this.isExit && Math.random() > 0.6;
      this.pulse = Math.random() * Math.PI * 2;
    }

    update() {
      this.x += this.vx;
      this.y += this.vy;
      this.pulse += 0.05;

      if (this.x < 0 || this.x > width) this.vx *= -1;
      if (this.y < 0 || this.y > height) this.vy *= -1;

      // Mouse gentle attraction/deflection
      if (mouse.x !== null) {
        let dx = mouse.x - this.x;
        let dy = mouse.y - this.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < mouse.radius) {
          let force = (mouse.radius - dist) / mouse.radius;
          this.x -= (dx / dist) * force * 2;
          this.y -= (dy / dist) * force * 2;
        }
      }
    }

    draw() {
      ctx.beginPath();
      let r = this.radius + Math.sin(this.pulse) * 0.5;
      ctx.arc(this.x, this.y, r, 0, Math.PI * 2);
      
      if (this.isExit) {
        ctx.fillStyle = '#00df72'; // Green for Exit Bridges
        ctx.shadowColor = '#00df72';
      } else if (this.isRelay) {
        ctx.fillStyle = '#00f0ff'; // Cyan for DERP Relays
        ctx.shadowColor = '#00f0ff';
      } else {
        ctx.fillStyle = '#9d4edd'; // Purple for Edge Clients
        ctx.shadowColor = '#9d4edd';
      }
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  function createParticles() {
    particles = [];
    const count = Math.min(Math.floor((width * height) / 16000), 75);
    for (let i = 0; i < count; i++) {
      particles.push(new NodeParticle());
    }
  }

  function drawConnections() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        let dx = particles[i].x - particles[j].x;
        let dy = particles[i].y - particles[j].y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        const maxDist = 140;

        if (dist < maxDist) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          let alpha = (1 - dist / maxDist) * 0.25;
          ctx.strokeStyle = `rgba(0, 240, 255, ${alpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    }
  }

  function animate() {
    ctx.clearRect(0, 0, width, height);
    for (let p of particles) {
      p.update();
      p.draw();
    }
    drawConnections();
    requestAnimationFrame(animate);
  }

  resize();
  animate();
}

// Live Interactive Simulation HUD Data & Controls
function initHUDControls() {
  const modeButtons = document.querySelectorAll('.mode-btn');
  const valPing = document.getElementById('stat-ping');
  const valDownlink = document.getElementById('stat-downlink');
  const valUplink = document.getElementById('stat-uplink');
  const valHops = document.getElementById('stat-hops');
  const valJitter = document.getElementById('stat-jitter');

  const modesData = {
    country: { ping: '18 ms', down: '124.5 Mbps', up: '52.1 Mbps', hops: '1 Hop (Direct)', jitter: '0.8 ms' },
    host: { ping: '9 ms', down: '210.8 Mbps', up: '98.4 Mbps', hops: '0 Hops (Direct P2P)', jitter: '0.3 ms' },
    onion: { ping: '38 ms', down: '68.2 Mbps', up: '28.0 Mbps', hops: '3 Hops (Obfuscated)', jitter: '12.4 ms' }
  };

  modeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      modeButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const mode = btn.getAttribute('data-mode');
      const data = modesData[mode] || modesData.country;

      if (valPing) valPing.textContent = data.ping;
      if (valDownlink) valDownlink.textContent = data.down;
      if (valUplink) valUplink.textContent = data.up;
      if (valHops) valHops.textContent = data.hops;
      if (valJitter) valJitter.textContent = data.jitter;
    });
  });

  // Minor live jitter ticker simulation
  setInterval(() => {
    const activeBtn = document.querySelector('.mode-btn.active');
    const mode = activeBtn ? activeBtn.getAttribute('data-mode') : 'country';
    if (valPing && mode === 'country') {
      const base = 18;
      const jitter = (Math.random() * 3 - 1.5).toFixed(0);
      valPing.textContent = `${base + parseInt(jitter)} ms`;
    }
  }, 3000);
}

// Clipboard Copy Helper
function initClipboard() {
  const copyBtn = document.getElementById('btn-copy-install');
  if (!copyBtn) return;

  copyBtn.addEventListener('click', () => {
    const codeText = document.querySelector('.quickstart-code').textContent.trim();
    navigator.clipboard.writeText(codeText).then(() => {
      copyBtn.textContent = 'Copied!';
      setTimeout(() => {
        copyBtn.textContent = 'Copy';
      }, 2000);
    });
  });
}
