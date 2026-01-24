/**
 * Tactical Lane Alignment - positions lanes directly using pixel coordinates
 */
(() => {
    function alignTacticalLanes() {
        const container = document.querySelector('.tactical__chain');
        if (!container) return;

        const svg = container.querySelector('.tactical__lanes');
        if (!svg) return;

        const dots = container.querySelectorAll('.tactical__node-dot');
        if (dots.length < 3) return;

        const containerRect = container.getBoundingClientRect();
        
        // Get dot centers in pixels relative to container
        const dotX = Array.from(dots).map(dot => {
            const r = dot.getBoundingClientRect();
            return (r.left + r.width / 2) - containerRect.left;
        });

        // Make SVG span full container, use pixel viewBox
        const w = containerRect.width;
        svg.setAttribute('viewBox', `0 0 ${w} 20`);
        svg.style.left = '0';
        svg.style.right = '0';
        svg.style.width = '100%';

        // Set lane endpoints directly to dot pixel positions
        const lanes = [
            ['.tactical__lane-bg--left', '.tactical__lane--flow-left', dotX[0], dotX[1]],
            ['.tactical__lane-bg--right', '.tactical__lane--flow-right', dotX[1], dotX[2]]
        ];

        lanes.forEach(([bgSel, flowSel, x1, x2]) => {
            const bg = svg.querySelector(bgSel);
            const flow = svg.querySelector(flowSel);
            if (bg) { bg.setAttribute('x1', x1); bg.setAttribute('x2', x2); }
            if (flow) { flow.setAttribute('x1', x1); flow.setAttribute('x2', x2); }
        });

        // Position convoys
        svg.querySelectorAll('.tactical__convoy').forEach(convoy => {
            const lane = convoy.dataset.lane;
            const progress = parseFloat(convoy.dataset.progress) || 0;
            const [start, end] = lane === 'spaceport-mid' ? [dotX[0], dotX[1]] : [dotX[1], dotX[2]];
            const cx = start + (end - start) * progress / 100;
            convoy.setAttribute('transform', `translate(${cx}, 10)`);
        });
    }

    function schedule() {
        requestAnimationFrame(() => requestAnimationFrame(alignTacticalLanes));
    }

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(alignTacticalLanes, 50);
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', schedule);
    } else {
        schedule();
    }

    document.body.addEventListener('htmx:afterSwap', schedule);
    document.body.addEventListener('htmx:afterSettle', schedule);
    
    window.alignTacticalLanes = alignTacticalLanes;
})();
