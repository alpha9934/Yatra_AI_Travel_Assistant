const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function sendChat(message, history = []) {
  const res = await fetch(`${BASE}/api/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error("Chat API error");
  return res.json();
}

export async function parseExpenseText(description) {
  const form = new FormData();
  form.append("description", description);
  const res = await fetch(`${BASE}/api/expense/parse-text`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error("Expense API error");
  return res.json();
}

export async function parseExpenseImage(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/expense/parse-image`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error("Expense image API error");
  return res.json();
}

export async function confirmBooking(flight) {
  const res = await fetch(`${BASE}/api/booking/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(flight),
  });
  if (!res.ok) throw new Error("Booking confirm error");
  return res.json();
}

