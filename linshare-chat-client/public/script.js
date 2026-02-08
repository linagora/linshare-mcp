// public/script.js

function fillChatInput(text) {
    const input = document.getElementById('chat-input');
    if (!input) {
        console.warn("⚠️ #chat-input not found yet, retrying...");
        return false;
    }

    console.log(`🎤 Transcription received: "${text}". Filling input field...`);

    try {
        // For React to track the change correctly, we often need to use the native setter
        // This bypasses React's internal state management and then we trigger the 'input' event to notify it.
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
        nativeInputValueSetter.call(input, text);

        // Trigger 'input' event so React updates its state
        input.dispatchEvent(new Event('input', { bubbles: true }));

        // Focus and move cursor to end
        input.focus();
        input.setSelectionRange(text.length, text.length);

        return true;
    } catch (e) {
        console.error("❌ Failed to set input value:", e);
        // Fallback to basic method
        input.value = text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
    }
}

function initTranscriptionBridge() {
    console.log("🚀 Transcription bridge starting...");

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === 1) { // Element
                    // Check if the node itself is the signal or has signals inside
                    const signalNodes = node.classList && node.classList.contains('transcription-signal')
                        ? [node]
                        : node.querySelectorAll('.transcription-signal');

                    signalNodes.forEach(signal => {
                        const text = signal.innerText.trim();
                        if (!text) return;

                        console.log("✨ Signal detected in DOM!");

                        // Try to fill it immediately
                        fillChatInput(text);

                        // Safety retries for race conditions or React re-renders
                        setTimeout(() => fillChatInput(text), 50);
                        setTimeout(() => fillChatInput(text), 250);
                        setTimeout(() => fillChatInput(text), 1000);

                        // Remove or hide the signal message to keep it clean
                        const messageElement = signal.closest('.step') || signal.closest('.cl-message');
                        if (messageElement) {
                            messageElement.style.display = 'none';
                        }
                    });
                }
            }
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    console.log("🚀 Transcription bridge initialized (Robust Mode). Watching for .transcription-signal...");
}

// Start watching
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTranscriptionBridge);
} else {
    initTranscriptionBridge();
}
