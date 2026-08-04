export async function realaiChat(opts) {
    const { baseUrl = "http://localhost:8000", model = "local", messages } = opts;
    const res = await fetch(`${baseUrl}/v1/chat/completions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, messages })
    });
    if (!res.ok)
        throw new Error(`RealAI error: ${res.status}`);
    const data = await res.json();
    return data.choices[0].message.content;
}
