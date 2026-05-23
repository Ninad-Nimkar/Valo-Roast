// Global variable to store the loading interval
let loadingInterval = null;

async function roastPlayer() {
    const username = document.getElementById("username").value;
    const tag = document.getElementById("tag").value;
    const resultBox = document.getElementById("result");
    const resultContent = resultBox.querySelector(".result-content");

    if (!username || !tag) {
        resultBox.classList.remove("hidden");
        resultContent.innerText = "ACCESS DENIED: Enter Valid Credentials (Username & Tag).";
        return;
    }

    // Show loading state
    resultBox.classList.remove("hidden");
    loadingAnimation(resultContent);

    try {
        const response = await fetch("/player", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, tag })
        });

        const data = await parseResponse(response);

        // Clear loading animation
        clearLoadingAnimation();

        if (!response.ok || data.error) {
            const message = data.error || data.detail || `Request failed with status ${response.status}`;
            resultContent.innerText = "SYSTEM ERROR: " + message;
            return;
        }

        if (!data.roast) {
            resultContent.innerText = "SYSTEM ERROR: Roast generator returned an empty response.";
            return;
        }

        typeWriter(data.roast, resultContent);

    } catch (error) {
        clearLoadingAnimation();
        resultContent.innerText = "CRITICAL FAILURE: Connection Lost.";
        console.error(error);
    }
}

async function parseResponse(response) {
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        return response.json();
    }

    const text = await response.text();
    return {
        error: text || `Request failed with status ${response.status}`
    };
}

// Typewriter Effect
function typeWriter(text, element, speed = 20) {
    element.innerText = "";
    let i = 0;

    function typing() {
        if (i < text.length) {
            element.innerText += text.charAt(i);
            i++;
            setTimeout(typing, speed);
        }
    }

    typing();
}

 // Loading Animation
function loadingAnimation(element) {
    // Clear any existing interval first
    clearLoadingAnimation();

    let dots = 0;
    element.innerText = "ANALYZING MATCH HISTORY";

    loadingInterval = setInterval(() => {
        dots = (dots + 1) % 4;
        element.innerText = "ANALYZING MATCH HISTORY" + ".".repeat(dots);
    }, 400);
}

// Clear Loading Animation 
function clearLoadingAnimation() {
    if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
    }
}
