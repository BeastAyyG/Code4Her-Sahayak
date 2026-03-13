/**
 * SafetyCall.js — Sahayak Simulated Safety Call Feature
 * 
 * HOW IT WORKS:
 * 1. User taps "📞 Call Dad (Fake)" button in Quick Messages
 * 2. A full-screen phone-call UI slides up (like a real incoming/active call)
 * 3. Web Audio API generates:
 *    - Low-frequency background ambience (street noise)
 *    - A pulsing "caller voice" tone that sounds like speech rhythm
 * 4. Timer counts up, wake lock prevents screen from sleeping
 * 5. MediaSession API shows "Call in Progress" on phone lock screen
 * 6. User taps "End" to dismiss everything cleanly
 */

(function () {
    'use strict';

    // ─────────────────────────────────────────────────────
    // STATE
    // ─────────────────────────────────────────────────────
    let state = 'IDLE'; // IDLE | RINGING | ACTIVE | ENDED
    let audioCtx = null;
    let callerNode = null;
    let noiseNode = null;
    let masterGain = null;
    let wakeLock = null;
    let timerRef = null;
    let secondsElapsed = 0;
    let ringInterval = null;

    // ─────────────────────────────────────────────────────
    // DOM HELPERS — build the call screen on demand
    // ─────────────────────────────────────────────────────
    function getOrCreateCallScreen() {
        let screen = document.getElementById('sc-call-screen');
        if (!screen) {
            screen = document.createElement('div');
            screen.id = 'sc-call-screen';
            screen.innerHTML = `
                <div class="sc-backdrop"></div>
                <div class="sc-panel">
                    <div class="sc-contact-avatar">👦</div>
                    <div class="sc-contact-name">Dad Mobile</div>
                    <div class="sc-call-state" id="sc-call-state">Calling...</div>
                    <div class="sc-timer" id="sc-timer" style="display:none;">00:00</div>

                    <div class="sc-visualizer" id="sc-visualizer">
                        <span></span><span></span><span></span><span></span><span></span>
                    </div>

                    <div class="sc-controls">
                        <button class="sc-ctrl-btn sc-mute-btn" id="sc-mute-btn" title="Mute">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                            <span>Mute</span>
                        </button>

                        <button class="sc-ctrl-btn sc-end-btn-big" id="sc-end-btn-main" title="End Call">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.58 3.38 2 2 0 0 1 3.55 1h3a2 2 0 0 1 2 1.72c.127.96.362 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.73a16 16 0 0 0 5.97 5.97l.1-.11a2 2 0 0 1 2.11-.45c.907.338 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" transform="rotate(135 12 12)"/></svg>
                            <span>End</span>
                        </button>

                        <button class="sc-ctrl-btn sc-speaker-btn" id="sc-speaker-btn" title="Speaker">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
                            <span>Speaker</span>
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(screen);

            // Inject styles
            injectStyles();

            // Wire up buttons
            document.getElementById('sc-end-btn-main').addEventListener('click', endCall);
            document.getElementById('sc-mute-btn').addEventListener('click', toggleMute);
            document.getElementById('sc-speaker-btn').addEventListener('click', () => {
                document.getElementById('sc-speaker-btn').classList.toggle('active');
            });
        }
        return screen;
    }

    function injectStyles() {
        if (document.getElementById('sc-styles')) return;
        const style = document.createElement('style');
        style.id = 'sc-styles';
        style.textContent = `
            #sc-call-screen {
                position: fixed;
                inset: 0;
                z-index: 99999;
                display: flex;
                align-items: flex-end;
                justify-content: center;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.4s ease;
            }
            #sc-call-screen.visible {
                opacity: 1;
                pointer-events: all;
            }
            .sc-backdrop {
                position: absolute;
                inset: 0;
                background: rgba(0, 0, 0, 0.85);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
            }
            .sc-panel {
                position: relative;
                z-index: 1;
                width: 100%;
                max-width: 420px;
                background: linear-gradient(180deg, #1a0a0f 0%, #0d0d0f 100%);
                border-top-left-radius: 32px;
                border-top-right-radius: 32px;
                border-top: 1px solid rgba(225, 29, 72, 0.25);
                padding: 32px 24px 48px;
                text-align: center;
                transform: translateY(100%);
                transition: transform 0.5s cubic-bezier(0.34, 1.2, 0.64, 1);
                box-shadow: 0 -20px 60px rgba(225, 29, 72, 0.15);
            }
            #sc-call-screen.visible .sc-panel {
                transform: translateY(0);
            }
            .sc-contact-avatar {
                font-size: 4rem;
                margin-bottom: 12px;
                filter: drop-shadow(0 0 20px rgba(225, 29, 72, 0.4));
            }
            .sc-contact-name {
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 1.7rem;
                font-weight: 700;
                color: #ffffff;
                letter-spacing: -0.02em;
                margin-bottom: 8px;
            }
            .sc-call-state {
                font-size: 0.9rem;
                color: rgba(255,255,255,0.4);
                margin-bottom: 4px;
            }
            .sc-timer {
                font-size: 1rem;
                font-weight: 600;
                color: #10B981;
                letter-spacing: 0.1em;
                margin-bottom: 4px;
            }
            .sc-visualizer {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 5px;
                height: 40px;
                margin: 20px 0;
            }
            .sc-visualizer span {
                display: inline-block;
                width: 4px;
                border-radius: 4px;
                background: rgba(225, 29, 72, 0.7);
                animation: sc-bar-idle 1.5s ease-in-out infinite;
            }
            .sc-visualizer span:nth-child(1) { height: 8px;  animation-delay: 0.0s; }
            .sc-visualizer span:nth-child(2) { height: 16px; animation-delay: 0.15s; }
            .sc-visualizer span:nth-child(3) { height: 24px; animation-delay: 0.3s; }
            .sc-visualizer span:nth-child(4) { height: 16px; animation-delay: 0.45s; }
            .sc-visualizer span:nth-child(5) { height: 8px;  animation-delay: 0.6s; }
            
            .sc-visualizer.speaking span {
                animation: sc-bar-speak 0.5s ease-in-out infinite alternate;
            }
            .sc-visualizer.speaking span:nth-child(1) { animation-delay: 0.0s; }
            .sc-visualizer.speaking span:nth-child(2) { animation-delay: 0.08s; }
            .sc-visualizer.speaking span:nth-child(3) { animation-delay: 0.16s; }
            .sc-visualizer.speaking span:nth-child(4) { animation-delay: 0.24s; }
            .sc-visualizer.speaking span:nth-child(5) { animation-delay: 0.32s; }

            @keyframes sc-bar-idle {
                0%, 100% { transform: scaleY(1); opacity: 0.4; }
                50% { transform: scaleY(1.5); opacity: 0.7; }
            }
            @keyframes sc-bar-speak {
                from { height: 6px; opacity: 0.6; }
                to { height: 34px; opacity: 1; }
            }

            .sc-controls {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 28px;
                margin-top: 8px;
            }
            .sc-ctrl-btn {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 50%;
                width: 64px;
                height: 64px;
                cursor: pointer;
                color: #fff;
                transition: all 0.2s ease;
                font-family: inherit;
                font-size: 0.65rem;
                padding: 0;
                overflow: visible;
                padding-top: 12px;
            }
            .sc-ctrl-btn svg {
                width: 22px;
                height: 22px;
            }
            .sc-ctrl-btn span {
                font-size: 0.65rem;
                color: rgba(255,255,255,0.5);
                margin-top: 10px;
                white-space: nowrap;
            }
            .sc-ctrl-btn:hover {
                background: rgba(255,255,255,0.12);
            }
            .sc-ctrl-btn.active {
                background: rgba(255,255,255,0.2);
                border-color: rgba(255,255,255,0.3);
            }
            .sc-end-btn-big {
                background: #E11D48 !important;
                border-color: rgba(225, 29, 72, 0.6) !important;
                width: 72px !important;
                height: 72px !important;
                box-shadow: 0 0 30px rgba(225, 29, 72, 0.4);
            }
            .sc-end-btn-big:hover {
                background: #BE123C !important;
                transform: scale(1.05);
            }
            .sc-end-btn-big svg {
                width: 26px;
                height: 26px;
            }

            /* Pill in navbar-area showing call is active */
            #sc-navbar-pill {
                position: fixed;
                top: 14px;
                left: 50%;
                transform: translateX(-50%) translateY(-60px);
                background: #18181A;
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 100px;
                padding: 6px 16px;
                display: flex;
                align-items: center;
                gap: 10px;
                color: #fff;
                font-size: 0.82rem;
                font-weight: 500;
                font-family: 'Plus Jakarta Sans', sans-serif;
                z-index: 99998;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                transition: transform 0.4s cubic-bezier(0.34, 1.2, 0.64, 1);
            }
            #sc-navbar-pill.visible {
                transform: translateX(-50%) translateY(0);
            }
            #sc-navbar-pill:hover {
                border-color: rgba(16, 185, 129, 0.8);
            }
            .sc-pill-dot {
                width: 8px;
                height: 8px;
                background: #10B981;
                border-radius: 50%;
                animation: sc-pill-pulse 1.5s infinite;
                flex-shrink: 0;
            }
            @keyframes sc-pill-pulse {
                0%, 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
                50% { box-shadow: 0 0 0 5px rgba(16,185,129,0); }
            }
        `;
        document.head.appendChild(style);
    }

    function getOrCreatePill() {
        let pill = document.getElementById('sc-navbar-pill');
        if (!pill) {
            pill = document.createElement('div');
            pill.id = 'sc-navbar-pill';
            pill.innerHTML = `<div class="sc-pill-dot"></div> <span id="sc-pill-time">00:00</span> &nbsp; Dad Mobile`;
            pill.setAttribute('title', 'Tap to return to call');
            pill.addEventListener('click', () => {
                getOrCreateCallScreen().classList.add('visible');
            });
            document.body.appendChild(pill);
        }
        return pill;
    }

    // ─────────────────────────────────────────────────────
    // AUDIO ENGINE
    // ─────────────────────────────────────────────────────
    async function startAudio() {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();

        // Master volume
        masterGain = audioCtx.createGain();
        masterGain.gain.value = 0.6;
        masterGain.connect(audioCtx.destination);

        // --- Background ambient noise (street / TV static) ---
        const bufSecs = 3;
        const bufSize = audioCtx.sampleRate * bufSecs;
        const noiseBuf = audioCtx.createBuffer(1, bufSize, audioCtx.sampleRate);
        const data = noiseBuf.getChannelData(0);
        for (let i = 0; i < bufSize; i++) data[i] = (Math.random() * 2 - 1) * 0.3;

        noiseNode = audioCtx.createBufferSource();
        noiseNode.buffer = noiseBuf;
        noiseNode.loop = true;

        const noiseFilter = audioCtx.createBiquadFilter();
        noiseFilter.type = 'bandpass';
        noiseFilter.frequency.value = 300;
        noiseFilter.Q.value = 0.5;

        const noiseGain = audioCtx.createGain();
        noiseGain.gain.value = 0.15;

        noiseNode.connect(noiseFilter);
        noiseFilter.connect(noiseGain);
        noiseGain.connect(masterGain);
        noiseNode.start();

        // --- Caller voice (pulsed tone simulating speech rhythm) ---
        callerNode = audioCtx.createOscillator();
        callerNode.type = 'sawtooth';
        callerNode.frequency.setValueAtTime(200, audioCtx.currentTime);

        // LFO for pitch variation (natural voice pitch movement)
        const lfo = audioCtx.createOscillator();
        lfo.type = 'sine';
        lfo.frequency.value = 3.5;
        const lfoGain = audioCtx.createGain();
        lfoGain.gain.value = 25;
        lfo.connect(lfoGain);
        lfoGain.connect(callerNode.frequency);
        lfo.start();

        // Low-pass to soften the harsh oscillator and make it more voice-like
        const voiceFilter = audioCtx.createBiquadFilter();
        voiceFilter.type = 'lowpass';
        voiceFilter.frequency.value = 1800;

        // Speech rhythm gate: talk 1.8s, pause 1s, repeat
        const speechGain = audioCtx.createGain();
        speechGain.gain.value = 0;

        const vizEl = document.getElementById('sc-visualizer');
        function scheduleSpeech(startAt) {
            if (state !== 'ACTIVE') return;
            const talkDur = 1.4 + Math.random() * 1.2; // 1.4 – 2.6 s
            const pauseDur = 0.6 + Math.random() * 0.8; // 0.6 – 1.4 s

            speechGain.gain.setValueAtTime(0, startAt);
            speechGain.gain.linearRampToValueAtTime(0.7, startAt + 0.08);
            speechGain.gain.setValueAtTime(0.7, startAt + talkDur - 0.08);
            speechGain.gain.linearRampToValueAtTime(0, startAt + talkDur);

            // Update visualizer CSS class in sync
            const msUntilTalk = (startAt - audioCtx.currentTime) * 1000;
            setTimeout(() => {
                if (vizEl) vizEl.classList.add('speaking');
                setTimeout(() => {
                    if (vizEl) vizEl.classList.remove('speaking');
                }, talkDur * 1000);
            }, Math.max(0, msUntilTalk));

            const nextStart = startAt + talkDur + pauseDur;
            const msUntilNext = (nextStart - audioCtx.currentTime) * 1000;
            setTimeout(() => scheduleSpeech(audioCtx.currentTime), Math.max(0, msUntilNext));
        }

        callerNode.connect(voiceFilter);
        voiceFilter.connect(speechGain);
        speechGain.connect(masterGain);
        callerNode.start();

        // Start speaking 1 second after call connects
        scheduleSpeech(audioCtx.currentTime + 1);
    }

    function stopAudio() {
        try {
            if (noiseNode) { noiseNode.stop(); noiseNode.disconnect(); noiseNode = null; }
            if (callerNode) { callerNode.stop(); callerNode.disconnect(); callerNode = null; }
            if (audioCtx) { audioCtx.close(); audioCtx = null; }
        } catch (e) { /* ignore */ }
        masterGain = null;
    }

    // ─────────────────────────────────────────────────────
    // WAKE LOCK
    // ─────────────────────────────────────────────────────
    async function acquireWakeLock() {
        if ('wakeLock' in navigator) {
            try {
                wakeLock = await navigator.wakeLock.request('screen');
            } catch (e) { /* feature not available */ }
        }
    }
    function releaseWakeLock() {
        if (wakeLock) { try { wakeLock.release(); } catch (e) { } wakeLock = null; }
    }

    // ─────────────────────────────────────────────────────
    // MEDIA SESSION (shows on lock screen)
    // ─────────────────────────────────────────────────────
    function setupMediaSession() {
        if (!('mediaSession' in navigator)) return;
        navigator.mediaSession.metadata = new MediaMetadata({
            title: 'Call with Dad Mobile',
            artist: 'Sahayak Safety Call'
        });
        navigator.mediaSession.setActionHandler('pause', endCall);
        navigator.mediaSession.setActionHandler('stop', endCall);
    }
    function clearMediaSession() {
        if (!('mediaSession' in navigator)) return;
        navigator.mediaSession.metadata = null;
        ['pause', 'stop'].forEach(a => {
            try { navigator.mediaSession.setActionHandler(a, null); } catch (e) { }
        });
    }

    // ─────────────────────────────────────────────────────
    // TIMER
    // ─────────────────────────────────────────────────────
    function startTimer() {
        secondsElapsed = 0;
        timerRef = setInterval(() => {
            secondsElapsed++;
            const m = String(Math.floor(secondsElapsed / 60)).padStart(2, '0');
            const s = String(secondsElapsed % 60).padStart(2, '0');
            const timeStr = `${m}:${s}`;
            const timerEl = document.getElementById('sc-timer');
            const pillEl = document.getElementById('sc-pill-time');
            if (timerEl) timerEl.textContent = timeStr;
            if (pillEl) pillEl.textContent = timeStr;
        }, 1000);
    }
    function stopTimer() {
        clearInterval(timerRef);
        timerRef = null;
    }

    // ─────────────────────────────────────────────────────
    // RINGING (before "answer")
    // ─────────────────────────────────────────────────────
    function startRinging() {
        let ringing = true;
        const ringCtx = new (window.AudioContext || window.webkitAudioContext)();

        function playRingTone() {
            if (!ringing) return;
            const osc = ringCtx.createOscillator();
            const g = ringCtx.createGain();
            osc.type = 'sine';
            osc.frequency.value = 440;
            g.gain.setValueAtTime(0.3, ringCtx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.001, ringCtx.currentTime + 0.15);
            osc.connect(g);
            g.connect(ringCtx.destination);
            osc.start();
            osc.stop(ringCtx.currentTime + 0.15);

            setTimeout(() => {
                if (!ringing) return;
                const osc2 = ringCtx.createOscillator();
                const g2 = ringCtx.createGain();
                osc2.type = 'sine';
                osc2.frequency.value = 480;
                g2.gain.setValueAtTime(0.3, ringCtx.currentTime);
                g2.gain.exponentialRampToValueAtTime(0.001, ringCtx.currentTime + 0.15);
                osc2.connect(g2);
                g2.connect(ringCtx.destination);
                osc2.start();
                osc2.stop(ringCtx.currentTime + 0.15);
            }, 200);
        }

        playRingTone();
        ringInterval = setInterval(playRingTone, 2000);

        // Auto-answer after 2.5 seconds (like a real scripted call would)
        setTimeout(() => {
            ringing = false;
            clearInterval(ringInterval);
            try { ringCtx.close(); } catch (e) { }
            answerCall();
        }, 2500);
    }

    // ─────────────────────────────────────────────────────
    // MUTE
    // ─────────────────────────────────────────────────────
    let muted = false;
    function toggleMute() {
        muted = !muted;
        if (masterGain) masterGain.gain.value = muted ? 0 : 0.6;
        const muteBtn = document.getElementById('sc-mute-btn');
        if (muteBtn) muteBtn.classList.toggle('active', muted);
    }

    // ─────────────────────────────────────────────────────
    // CALL LIFECYCLE
    // ─────────────────────────────────────────────────────
    async function startCall() {
        if (state !== 'IDLE') return;
        state = 'RINGING';
        muted = false;

        const screen = getOrCreateCallScreen();
        const callStateEl = document.getElementById('sc-call-state');
        const timerEl = document.getElementById('sc-timer');
        const vizEl = document.getElementById('sc-visualizer');

        if (callStateEl) callStateEl.textContent = 'Calling...';
        if (timerEl) timerEl.style.display = 'none';
        if (vizEl) vizEl.classList.remove('speaking');

        screen.classList.add('visible');

        await acquireWakeLock();
        startRinging();
    }

    async function answerCall() {
        if (state !== 'RINGING') return;
        state = 'ACTIVE';

        const callStateEl = document.getElementById('sc-call-state');
        const timerEl = document.getElementById('sc-timer');

        if (callStateEl) callStateEl.textContent = 'Connected';
        if (timerEl) timerEl.style.display = 'block';

        startTimer();
        setupMediaSession();

        // Show navbar pill (so it's visible when user minimizes screen)
        getOrCreatePill().classList.add('visible');

        try {
            await startAudio();
        } catch (e) {
            console.warn('SafetyCall audio error:', e);
        }
    }

    function endCall() {
        if (state === 'IDLE') return;
        state = 'ENDED';

        stopAudio();
        stopTimer();
        clearInterval(ringInterval);
        clearMediaSession();
        releaseWakeLock();

        const screen = document.getElementById('sc-call-screen');
        const pill = document.getElementById('sc-navbar-pill');

        if (screen) screen.classList.remove('visible');
        if (pill) pill.classList.remove('visible');

        // Allow CSS transition to finish then reset
        setTimeout(() => {
            state = 'IDLE';
            muted = false;
            const vizEl = document.getElementById('sc-visualizer');
            if (vizEl) vizEl.classList.remove('speaking');
        }, 600);
    }

    // ─────────────────────────────────────────────────────
    // EVENT BUS (connects to index.html)
    // ─────────────────────────────────────────────────────
    window.addEventListener('START_SIMULATION', startCall);
    window.addEventListener('STOP_SIMULATION', endCall);
    window.addEventListener('INTERRUPT_SIMULATION', endCall);

    // Expose for manual calls from console/other modules
    window.safetyCall = { start: startCall, end: endCall };

    // SOS button should also end any active call
    const sosBtn = document.getElementById('sosBtn');
    if (sosBtn) {
        sosBtn.addEventListener('click', () => {
            if (state !== 'IDLE') endCall();
        });
    }

    console.log('SafetyCall module loaded. Click "📞 Call Dad (Fake)" to test.');
})();
