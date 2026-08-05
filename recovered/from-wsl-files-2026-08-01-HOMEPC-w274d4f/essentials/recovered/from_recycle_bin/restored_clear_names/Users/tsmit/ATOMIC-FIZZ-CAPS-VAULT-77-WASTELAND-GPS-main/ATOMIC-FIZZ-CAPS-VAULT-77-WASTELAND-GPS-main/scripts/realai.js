import fetch from "node-fetch";

export async function askRealAI(prompt) {
  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "realai-1.0",
      messages: [{ role: "user", content: prompt }]
    })
  });

  const data = await res.json();
  console.log(data.output);
}
