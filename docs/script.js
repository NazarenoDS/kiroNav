document.addEventListener('DOMContentLoaded', () => {

    // ---- CTA Ghost: Eyes follow mouse ----
    const ctaGhostSvg = document.querySelector('.cta-ghost svg');
    const ctaEyes = document.querySelectorAll('.cta-eye');

    if (ctaGhostSvg && ctaEyes.length === 2) {
        document.addEventListener('mousemove', (e) => {
            const rect = ctaGhostSvg.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height * 0.35;

            const dx = (e.clientX - cx) / rect.width;
            const dy = (e.clientY - cy) / rect.height;

            // Clamp movement to a small radius (0.4 SVG units max)
            const maxMove = 0.4;
            const moveX = Math.max(-maxMove, Math.min(maxMove, dx * 1.5));
            const moveY = Math.max(-maxMove, Math.min(maxMove, dy * 1.5));

            ctaEyes.forEach(eye => {
                eye.setAttribute('transform', `translate(${moveX}, ${moveY})`);
            });
        });
    }

    // ---- Hero Ghost: Blink cycle ----
    const heroGhost = document.getElementById('hero-ghost');
    if (heroGhost) {
        const eyeStates = [
            { left: 'M12.722 10.985c-.656 0-.755-.785-.755-1.252 0-.423.074-.756.218-.97a.61.61 0 01.537-.283c.229 0 .428.095.567.289.159.218.243.55.243.964 0 .785-.303 1.252-.805 1.252h-.005z', right: 'M15.425 10.985c-.656 0-.755-.785-.755-1.252 0-.423.074-.756.219-.97a.61.61 0 01.536-.283c.229 0 .428.095.567.289.159.218.243.55.243.964 0 .785-.303 1.252-.805 1.252h-.005z' },
            { left: 'M12.2 10.2 h1.2', right: 'M14.9 10.2 h1.2' },
            { left: 'M12.0 10.0 Q12.8 10.8 13.5 10.0', right: 'M14.7 10.0 Q15.5 10.8 16.2 10.0' },
        ];
        let state = 0;
        function blink() {
            state = (state + 1) % eyeStates.length;
            const s = eyeStates[state];
            const l = heroGhost.querySelector('.eye-left');
            const r = heroGhost.querySelector('.eye-right');
            if (l && r) { l.setAttribute('d', s.left); r.setAttribute('d', s.right); }
            setTimeout(blink, state === 1 ? 200 : 2500 + Math.random() * 2000);
        }
        setTimeout(blink, 3000);
    }

    // ---- Smooth scroll ----
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            e.preventDefault();
            const t = document.querySelector(a.getAttribute('href'));
            if (t) t.scrollIntoView({ behavior: 'smooth' });
        });
    });
});
