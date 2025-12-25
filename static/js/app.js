/**
 * NVR System - Frontend Application
 * Pure Django MVT Version (No APIs)
 */

class NVRApp {
    constructor() {
        this.cameras = window.INITIAL_CAMERAS || [];
        this.timelineData = window.TIMELINE_DATA || null;
        this.selectedCamera = window.SELECTED_CAMERA_ID || null;
        this.selectedDate = window.SELECTED_DATE || null;
        this.currentSegmentIndex = -1;
        this.isAutoPlayEnabled = true;
        this.playbackState = 'stopped';

        this.init();
    }

    init() {
        console.log("🚀 Initializing NVR App (MVT Mode)...");

        // Initialize UI components
        this.initTimePickerUI();
        this.initEventListeners();

        // Page-specific initializations
        // 1. Live View
        if (document.getElementById('camera-grid')) {
            this.initLiveView();
        }

        // 2. Playback Timeline
        console.log('Checking timeline rendering...');
        console.log('timelineData:', this.timelineData);
        console.log('timeline element:', document.getElementById('timeline'));
        if (this.timelineData && document.getElementById('timeline')) {
            console.log('✅ Calling renderTimeline()...');
            this.renderTimeline();
        } else {
            console.log('❌ Timeline not rendered. timelineData:', !!this.timelineData, 'timeline element:', !!document.getElementById('timeline'));
        }

        // 3. Highlight active configuration in sidebar/nav if needed
        const currentPath = window.location.pathname;
        document.querySelectorAll('.nav-item').forEach(item => {
            if (item.getAttribute('href') === currentPath) {
                item.classList.add('active');
            }
        });
    }

    initEventListeners() {
        console.log("Initializing event listeners...");
        // Modal toggles (Pure UI) -- assumes buttons exist
        const addCameraBtn = document.getElementById('add-camera-btn');
        if (addCameraBtn) {
            addCameraBtn.addEventListener('click', () => {
                const modal = document.getElementById('add-camera-modal');
                if (modal) modal.classList.add('active');
            });
        }

        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                if (!this.selectedCamera) {
                    alert("Please select a camera first.");
                    return;
                }
                const modal = document.getElementById('export-modal');
                if (modal) {
                    modal.classList.add('active');
                    // Set hidden input
                    const hiddenId = document.getElementById('export-camera-id');
                    if (hiddenId) hiddenId.value = this.selectedCamera;
                }
            });
        }

        // Close Modals
        document.querySelectorAll('.modal-close, .btn-secondary, .close-modal').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // If it's a specific close button or cancel
                if (btn.id === 'cancel-add' || btn.classList.contains('modal-close')) {
                    const modal = btn.closest('.modal');
                    if (modal) modal.classList.remove('active');
                }
            });
        });

        // Playback: Auto-advance
        const videoPlayer = document.getElementById('playback-video');
        if (videoPlayer) {
            videoPlayer.addEventListener('ended', () => {
                this.playbackState = 'stopped';
                if (this.isAutoPlayEnabled) {
                    this.playNextSegment();
                }
            });

            videoPlayer.addEventListener('error', (e) => {
                console.warn("Video playback error, attempting next segment...", e);
                if (this.isAutoPlayEnabled) {
                    setTimeout(() => this.playNextSegment(), 1000);
                }
            });
        }

        // Layout controls
        document.querySelectorAll('.layout-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setGridLayout(btn.dataset.layout);
            });
        });
    }

    initTimePickerUI() {
        const dateInput = document.getElementById('playback-date');
        // If element doesn't exist (e.g. not on Playback page), just return
        if (!dateInput) return;

        // Basic limits
        const today = new Date().toISOString().split('T')[0];
        dateInput.max = today;
    }

    // ==========================================
    // LIVE VIEW LOGIC
    // ==========================================
    initLiveView() {
        // MVT Pattern: Attach listeners to server-rendered elements
        document.querySelectorAll('.camera-video').forEach(vid => {
            vid.addEventListener('click', () => {
                const card = vid.closest('.camera-card');
                if (card) {
                    card.classList.toggle('maximized');
                    document.body.classList.toggle('maximized-view');
                }
            });
        });

        // Initialize Recording Progress
        this.initRecordingAnimation();
    }

    initRecordingAnimation() {
        document.querySelectorAll('.recording-overlay').forEach(overlay => {
            const duration = parseInt(overlay.dataset.segmentDuration) || 300; // seconds
            const fill = overlay.querySelector('.rec-progress-fill');
            if (fill) {
                // Determine a pseudo-start time based on current time to sync roughly
                // Start of current segment derived from wall clock
                // e.g. if time is 12:00:15 and duration is 60s, we are at 15s.
                // This ensures all cameras sync up.

                const update = () => {
                    const now = Math.floor(Date.now() / 1000);
                    const elapsed = now % duration; // Modulo gives seconds into current window
                    const pct = (elapsed / duration) * 100;
                    fill.style.width = `${pct}%`;

                    // Update timer text inside details
                    const timer = overlay.querySelector('.timer-val');
                    if (timer) {
                        timer.textContent = `${elapsed}s / ${duration}s`;
                    }
                };

                update(); // Initial
                setInterval(update, 1000); // Loop
            }
        });
    }

    setGridLayout(layout) {
        const grid = document.getElementById('camera-grid');
        if (grid) grid.dataset.layout = layout;
    }

    // ==========================================
    // TIMELINE LOGIC (DVR Style)
    // ==========================================
    renderTimeline() {
        console.log('🎬 renderTimeline() called!');
        const container = document.getElementById('timeline');
        console.log('Timeline container:', container);
        if (!container) {
            console.error('❌ Timeline container not found!');
            return;
        }
        container.innerHTML = '';

        const segments = this.timelineData.segments;
        console.log('Segments to render:', segments ? segments.length : 0);
        if (!segments || segments.length === 0) {
            container.innerHTML = '<div class="no-recordings">No recordings found for this date.</div>';
            return;
        }

        // --- Controls ---
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'timeline-playback-controls';

        const autoPlayLabel = document.createElement('label');
        autoPlayLabel.style.cssText = 'display: flex; align-items: center; gap: 6px; cursor: pointer;';
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = this.isAutoPlayEnabled;
        cb.onchange = (e) => this.isAutoPlayEnabled = e.target.checked;
        autoPlayLabel.appendChild(cb);
        autoPlayLabel.appendChild(document.createTextNode('Auto-play'));
        controlsDiv.appendChild(autoPlayLabel);

        const playAllBtn = document.createElement('button');
        playAllBtn.textContent = '▶ Play All';
        playAllBtn.className = 'btn btn-primary btn-sm';
        playAllBtn.onclick = () => { this.isAutoPlayEnabled = true; this.playRecording(0); };
        controlsDiv.appendChild(playAllBtn);
        container.appendChild(controlsDiv);

        // --- Timeline Calculation ---
        const firstSegStart = new Date(segments[0].start_time);
        const lastSegStart = new Date(segments[segments.length - 1].start_time);
        const fullEndTime = new Date(lastSegStart.getTime() + segments[segments.length - 1].duration * 1000);

        const timelineStart = new Date(firstSegStart);
        timelineStart.setMinutes(0, 0, 0);
        const timelineEnd = new Date(fullEndTime);
        if (timelineEnd.getMinutes() > 0) {
            timelineEnd.setHours(timelineEnd.getHours() + 1);
            timelineEnd.setMinutes(0, 0, 0);
        }
        const totalDurationMs = timelineEnd - timelineStart;

        // --- Timline Wrapper ---
        const wrapper = document.createElement('div');
        wrapper.className = 'dvr-timeline-wrapper';
        wrapper.style.cssText = 'position: relative; margin-top: 10px; user-select: none;';

        // Headers (Hours)
        const header = document.createElement('div');
        header.className = 'dvr-timeline-header';
        header.style.cssText = 'position: relative; height: 20px; border-bottom: 1px solid #444; margin-bottom: 5px;';

        const startHour = timelineStart.getHours();
        const endHour = timelineEnd.getHours() + (timelineEnd.getDate() > timelineStart.getDate() ? 24 : 0);

        for (let h = startHour; h <= endHour; h++) {
            const dateAtHour = new Date(timelineStart);
            dateAtHour.setHours(h, 0, 0, 0);

            const offsetMs = dateAtHour - timelineStart;
            const pct = (offsetMs / totalDurationMs) * 100;

            if (pct > 100) continue;

            const label = document.createElement('div');
            label.textContent = `${h % 24}:00`;
            label.style.cssText = `position: absolute; left: ${pct}%; transform: translateX(-50%); font-size: 10px; color: #888;`;

            const tick = document.createElement('div');
            tick.style.cssText = `position: absolute; left: ${pct}%; bottom: 0; width: 1px; height: 5px; background: #666;`;

            header.appendChild(label);
            header.appendChild(tick);
        }
        wrapper.appendChild(header);

        // Track
        const track = document.createElement('div');
        track.className = 'dvr-timeline-track';
        track.style.cssText = 'position: relative; width: 100%; height: 40px; background: #1a1a2e; border: 1px solid #333; cursor: pointer; overflow: hidden; border-radius: 4px;';

        // Segments
        segments.forEach((seg, idx) => {
            const start = new Date(seg.start_time);
            const offset = start - timelineStart;
            const durationMs = seg.duration * 1000;

            const left = (offset / totalDurationMs) * 100;
            // Ensure minimum width of 0.2% so small segments are visible
            const rawWidth = (durationMs / totalDurationMs) * 100;
            const width = Math.max(rawWidth, 0.2);

            const block = document.createElement('div');
            block.id = `segment-block-${idx}`;
            block.style.cssText = `position: absolute; left: ${left}%; width: ${width}%; height: 100%; background: #6366f1; opacity: 0.8; pointer-events: none;`;
            track.appendChild(block);
        });

        // Playhead
        const playhead = document.createElement('div');
        playhead.id = 'dvr-playhead-line';
        playhead.style.cssText = 'position: absolute; top:0; left:0; width: 2px; height: 100%; background: cyan; display: none; pointer-events: none; z-index: 10; box-shadow: 0 0 5px cyan;';
        track.appendChild(playhead);

        // Hover Time
        const hoverTime = document.createElement('div');
        hoverTime.style.cssText = 'position: absolute; top: -25px; background: black; color: white; padding: 2px 4px; font-size: 10px; border-radius: 3px; display: none; pointer-events: none; white-space: nowrap; z-index: 20;';
        track.appendChild(hoverTime);

        // Events
        track.addEventListener('mousemove', (e) => {
            const rect = track.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const pct = Math.max(0, Math.min(1, x / rect.width));

            const timeMs = timelineStart.getTime() + (pct * totalDurationMs);
            hoverTime.textContent = new Date(timeMs).toLocaleTimeString();
            hoverTime.style.left = `${x}px`;
            hoverTime.style.transform = 'translateX(-50%)';
            hoverTime.style.display = 'block';
        });

        track.addEventListener('mouseleave', () => { hoverTime.style.display = 'none'; });

        track.addEventListener('click', (e) => {
            const rect = track.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const pct = Math.max(0, Math.min(1, x / rect.width));
            const clickMs = timelineStart.getTime() + (pct * totalDurationMs);

            // Find segment
            const idx = segments.findIndex(s => {
                const sStart = new Date(s.start_time).getTime();
                const sEnd = sStart + (s.duration * 1000);
                return clickMs >= sStart && clickMs <= sEnd;
            });

            if (idx !== -1) {
                this.playRecording(idx);
                playhead.style.left = `${pct * 100}%`;
                playhead.style.display = 'block';
            } else {
                console.log("No recording at this time");
            }
        });

        wrapper.appendChild(track);
        container.appendChild(wrapper);
    }

    playRecording(index) {
        if (!this.timelineData || !this.timelineData.segments[index]) return;

        this.currentSegmentIndex = index;
        const segment = this.timelineData.segments[index];
        const videoPlayer = document.getElementById('playback-video');
        if (!videoPlayer) return;

        // Use Media URL not API
        // Filename often includes .mp4, backend filter expects startswith. 
        // Let's pass the filename (cleaned of directory if any)
        const filename = segment.filename.split('/').pop();

        videoPlayer.src = `/media/recordings/${this.selectedCamera}/${filename}`;

        // Add overlay info
        const overlay = document.getElementById('video-overlay');
        if (overlay) {
            overlay.classList.add('hidden'); // Hide "Select camera" overlay
        }

        videoPlayer.play().catch(e => console.error("Auto-play blocked", e));

        // Highlight in timeline (visual)
        document.querySelectorAll('.dvr-segment-block').forEach(el => el.style.background = '#6366f1'); // reset
        const activeBlock = document.getElementById(`segment-block-${index}`);
        if (activeBlock) activeBlock.style.background = '#00f2fe'; // highlight
    }

    playNextSegment() {
        if (this.currentSegmentIndex + 1 < this.timelineData.segments.length) {
            this.playRecording(this.currentSegmentIndex + 1);
        }
    }
}

// Instantiate on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new NVRApp();
});
