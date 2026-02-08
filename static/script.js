async function roastPlayer() {
    const username = document.getElementById("username").value;
    const tag = document.getElementById("tag").value;
    const resultDiv = document.getElementById("result");

    if (!username || !tag) {
        resultDiv.innerText = "Enter username and tag.";
        return;
    }

    resultDiv.innerText = "Cooking your roast... 🔥";

    try {
        const response = await fetch("/player", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, tag })
        });

        const data = await response.json();

        if (data.error) {
            resultDiv.innerText = "Error: " + JSON.stringify(data.error);
            return;
        }

        resultDiv.innerText = data.roast;

    } catch (error) {
        resultDiv.innerText = "Something went wrong.";
        console.error(error);
    }
}
