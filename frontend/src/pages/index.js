import { useState, useRef, useEffect, useCallback } from "react";
import { sendChat, parseExpenseImage, confirmBooking } from "../lib/api";
import {
  Plane, Hotel, Receipt, AlertTriangle, MessageSquare,
  Send, Upload, Loader2, ChevronRight, CheckCircle,
  XCircle, AlertCircle, Building2, MapPin, Check, Ticket,
  Trash2, RefreshCw, TrendingUp, ShieldCheck, ShieldX,
  Calendar, Clock, Luggage, Hash, ArrowRight, Ban
} from "lucide-react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SUGGESTIONS = [
  "Book me a flight from Bengaluru to Delhi next Monday",
  "Can I book business class for a 3-hour flight?",
  "My IndiGo flight 6E-204 is delayed by 2 hours",
  "Log expense: Ola cab ₹680 from airport today",
];

const INTENT_CONFIG = {
  booking:    { icon: Plane,         color: "blue",   label: "Flight & Hotel Search" },
  expense:    { icon: Receipt,       color: "green",  label: "Expense Logged" },
  policy:     { icon: Building2,     color: "purple", label: "Policy Check" },
  disruption: { icon: AlertTriangle, color: "amber",  label: "Disruption Alert" },
  confirmed:  { icon: Ticket,        color: "green",  label: "Booking Confirmed" },
  general:    { icon: MessageSquare, color: "gray",   label: "DIYA" },
};

const COLORS = {
  blue: "#2563EB", green: "#16A34A", purple: "#7C3AED",
  amber: "#D97706", gray: "#64748B"
};

const CAT_COLORS = {
  meals:         { bg: "#FEF3C7", text: "#92400E" },
  transport:     { bg: "#DBEAFE", text: "#1E40AF" },
  accommodation: { bg: "#F3E8FF", text: "#6B21A8" },
  other:         { bg: "#F1F5F9", text: "#475569" },
};

const AIRLINE_COLORS = {
  "IndiGo":    { bg: "#EFF6FF", text: "#1D4ED8", dot: "#2563EB" },
  "Air India": { bg: "#FEF2F2", text: "#991B1B", dot: "#DC2626" },
  "Vistara":   { bg: "#F5F3FF", text: "#5B21B6", dot: "#7C3AED" },
  "SpiceJet":  { bg: "#FFF7ED", text: "#9A3412", dot: "#EA580C" },
};

export default function Home() {
  const [messages, setMessages] = useState([
    {
      role: "assistant", intent: "general",
      data: { message: "Hi! I'm DIYA, your Yatra AI travel assistant 👋\n\nI can help you book flights & hotels, log expenses, check travel policy, and handle disruptions.\n\nWhat do you need today?" },
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("chat");
  const [expenses, setExpenses] = useState([]);
  const [trips, setTrips] = useState([]);
  const [expensesLoading, setExpensesLoading] = useState(false);
  const [tripsLoading, setTripsLoading] = useState(false);
  const bottomRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const fetchExpenses = useCallback(async () => {
    setExpensesLoading(true);
    try { const r = await fetch(`${BASE}/api/expense/log`); setExpenses(await r.json()); } catch {}
    setExpensesLoading(false);
  }, []);

  const fetchTrips = useCallback(async () => {
    setTripsLoading(true);
    try { const r = await fetch(`${BASE}/api/booking/confirmed`); setTrips(await r.json()); } catch {}
    setTripsLoading(false);
  }, []);

  useEffect(() => { if (activeTab === "expenses") fetchExpenses(); }, [activeTab, fetchExpenses]);
  useEffect(() => { if (activeTab === "trips") fetchTrips(); }, [activeTab, fetchTrips]);

  async function deleteExpense(id) {
    await fetch(`${BASE}/api/expense/log/${id}`, { method: "DELETE" });
    setExpenses(prev => prev.filter(e => e.id !== id));
  }

  async function cancelTrip(id) {
    await fetch(`${BASE}/api/booking/confirmed/${id}`, { method: "DELETE" });
    setTrips(prev => prev.filter(t => t.booking_id !== id));
  }

  const history = messages
    .filter(m => m.role === "user" || m.role === "assistant")
    .map(m => ({ role: m.role, content: m.role === "user" ? m.content : m.data?.message || "" }));

  async function handleSend(text) {
    const msg = text || input;
    if (!msg.trim()) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const res = await sendChat(msg, history);
      setMessages(prev => [...prev, { role: "assistant", intent: res.intent, data: res.data }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", intent: "general", data: { message: "Sorry, couldn't connect to the server." } }]);
    }
    setLoading(false);
  }

  async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setMessages(prev => [...prev, { role: "user", content: `📎 Uploaded receipt: ${file.name}` }]);
    setLoading(true);
    try {
      const result = await parseExpenseImage(file);
      setMessages(prev => [...prev, { role: "assistant", intent: "expense", data: { ...result, message: `Receipt processed! Found ₹${result.total_amount} at ${result.merchant}.` } }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", intent: "general", data: { message: "Could not process the receipt image." } }]);
    }
    setLoading(false);
    e.target.value = "";
  }

  async function handleConfirmBooking(flight) {
    setMessages(prev => [...prev, { role: "user", content: `Confirm booking: ${flight.airline} ${flight.flight_no} at ₹${flight.price.toLocaleString("en-IN")}` }]);
    setLoading(true);
    try {
      const result = await confirmBooking(flight);
      setMessages(prev => [...prev, { role: "assistant", intent: "confirmed", data: { ...result, message: `Your flight is booked! 🎉 Booking ID: ${result.booking_id}` } }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", intent: "general", data: { message: "Booking failed. Please try again." } }]);
    }
    setLoading(false);
  }

  const totalReimbursable = expenses.filter(e => e.reimbursable).reduce((s, e) => s + (e.total_amount || 0), 0);
  const totalNonReimbursable = expenses.filter(e => !e.reimbursable).reduce((s, e) => s + (e.total_amount || 0), 0);
  const totalAll = expenses.reduce((s, e) => s + (e.total_amount || 0), 0);
  const totalSpentOnTrips = trips.reduce((s, t) => s + (t.price || 0), 0);

  const TABS = [
    { id: "chat",     icon: MessageSquare, label: "DIYA Chat",     live: true,  badge: null },
    { id: "expenses", icon: Receipt,       label: "My Expenses",   live: true,  badge: expenses.length || null },
    { id: "trips",    icon: Plane,         label: "My Trips",      live: true,  badge: trips.length || null },
    { id: "policy",   icon: Building2,     label: "Travel Policy", live: false, badge: null },
  ];

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'Inter','Segoe UI',sans-serif", background: "#F8F7F4", color: "#1A1A1A" }}>

      {/* Sidebar */}
      <aside style={{ width: 240, background: "#0F172A", display: "flex", flexDirection: "column", padding: "1.5rem 1rem" }}>
        <div style={{ marginBottom: "2rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "#2563EB", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Plane size={18} color="#fff" />
            </div>
            <span style={{ fontWeight: 700, fontSize: 18, color: "#fff", letterSpacing: "-0.02em" }}>Yatra</span>
          </div>
          <span style={{ fontSize: 11, color: "#64748B", letterSpacing: "0.06em", textTransform: "uppercase", marginLeft: 42 }}>AI Travel Assistant</span>
        </div>

        {TABS.map(({ id, icon: Icon, label, live, badge }) => (
          <button key={id} onClick={() => live && setActiveTab(id)}
            style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 12px", borderRadius: 8, border: "none", cursor: live ? "pointer" : "not-allowed", width: "100%", marginBottom: 4, fontSize: 14, fontWeight: activeTab === id ? 600 : 400, background: activeTab === id ? "#1E293B" : "transparent", color: activeTab === id ? "#fff" : "#94A3B8", opacity: live ? 1 : 0.4 }}>
            <Icon size={16} />
            {label}
            {!live && <span style={{ marginLeft: "auto", fontSize: 10, background: "#1E293B", color: "#475569", padding: "2px 6px", borderRadius: 4 }}>Soon</span>}
            {live && badge > 0 && <span style={{ marginLeft: "auto", fontSize: 10, background: "#2563EB", color: "#fff", padding: "2px 7px", borderRadius: 10, fontWeight: 700 }}>{badge}</span>}
          </button>
        ))}

        <div style={{ marginTop: "auto", borderTop: "1px solid #1E293B", paddingTop: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#1E293B", border: "1px solid #334155", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Building2 size={15} color="#64748B" />
            </div>
            <div>
              <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: "#94A3B8" }}>Product Manager</p>
              <p style={{ margin: 0, fontSize: 11, color: "#475569" }}>Yatra Corporate Travel</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <header style={{ padding: "1rem 1.5rem", borderBottom: "1px solid #E2E8F0", background: "#fff", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em" }}>
              {activeTab === "chat" ? "DIYA — Travel Assistant" : activeTab === "expenses" ? "My Expenses" : activeTab === "trips" ? "My Trips" : "Travel Policy"}
            </h1>
            <p style={{ margin: 0, fontSize: 13, color: "#64748B" }}>
              {activeTab === "chat" ? "Powered by multi-agent AI · Yatra POC" : activeTab === "expenses" ? "Session expense log · auto-captured by RECAP" : activeTab === "trips" ? "Confirmed bookings this session · powered by DIYA" : ""}
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {(activeTab === "expenses" || activeTab === "trips") && (
              <button onClick={activeTab === "expenses" ? fetchExpenses : fetchTrips}
                style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid #E2E8F0", background: "#fff", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#64748B" }}>
                <RefreshCw size={13} /> Refresh
              </button>
            )}
            <span style={{ background: "#DCFCE7", color: "#15803D", fontSize: 12, fontWeight: 600, padding: "4px 10px", borderRadius: 20 }}>● Live</span>
          </div>
        </header>

        {activeTab === "chat" && (
          <>
            <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem", display: "flex", flexDirection: "column", gap: 16 }}>
              {messages.map((msg, i) => <MessageBubble key={i} msg={msg} onConfirmBooking={handleConfirmBooking} />)}
              {loading && (
                <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <AgentAvatar intent="general" />
                  <div style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: "0 16px 16px 16px", padding: "12px 16px", display: "flex", alignItems: "center", gap: 8 }}>
                    <Loader2 size={16} style={{ animation: "spin 1s linear infinite", color: "#2563EB" }} />
                    <span style={{ fontSize: 14, color: "#64748B" }}>DIYA is thinking…</span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
            {messages.length <= 2 && (
              <div style={{ padding: "0 1.5rem 1rem", display: "flex", gap: 8, flexWrap: "wrap" }}>
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} onClick={() => handleSend(s)}
                    style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 20, padding: "6px 14px", fontSize: 13, color: "#334155", cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                    <ChevronRight size={13} color="#2563EB" />{s}
                  </button>
                ))}
              </div>
            )}
            <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid #E2E8F0", background: "#fff", display: "flex", gap: 10 }}>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleFileUpload} />
              <button onClick={() => fileRef.current?.click()}
                style={{ padding: "10px 14px", borderRadius: 10, border: "1px solid #E2E8F0", background: "#F8F7F4", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#64748B" }}>
                <Upload size={16} /> Receipt
              </button>
              <input value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Ask about flights, hotels, expenses, or travel policy…"
                style={{ flex: 1, padding: "10px 16px", borderRadius: 10, border: "1px solid #E2E8F0", fontSize: 14, outline: "none", background: "#F8F7F4" }} />
              <button onClick={() => handleSend()} disabled={!input.trim() || loading}
                style={{ padding: "10px 16px", borderRadius: 10, border: "none", background: "#2563EB", cursor: input.trim() ? "pointer" : "not-allowed", opacity: input.trim() ? 1 : 0.5, display: "flex", alignItems: "center", gap: 6, color: "#fff", fontSize: 14, fontWeight: 600 }}>
                <Send size={16} /> Send
              </button>
            </div>
          </>
        )}

        {activeTab === "expenses" && (
          <ExpensesTab expenses={expenses} loading={expensesLoading} onDelete={deleteExpense} onRefresh={fetchExpenses}
            totalAll={totalAll} totalReimbursable={totalReimbursable} totalNonReimbursable={totalNonReimbursable}
            onSwitchToChat={() => setActiveTab("chat")} />
        )}

        {activeTab === "trips" && (
          <TripsTab trips={trips} loading={tripsLoading} onCancel={cancelTrip} onRefresh={fetchTrips}
            totalSpent={totalSpentOnTrips} onSwitchToChat={() => setActiveTab("chat")} />
        )}
      </main>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function TripsTab({ trips, loading, onCancel, onRefresh, totalSpent, onSwitchToChat }) {
  if (loading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 12 }}>
        <Loader2 size={24} style={{ animation: "spin 1s linear infinite", color: "#2563EB" }} />
        <span style={{ fontSize: 14, color: "#64748B" }}>Loading trips…</span>
      </div>
    );
  }

  if (trips.length === 0) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16, padding: "2rem" }}>
        <div style={{ width: 56, height: 56, borderRadius: 16, background: "#EFF6FF", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Plane size={26} color="#2563EB" />
        </div>
        <div style={{ textAlign: "center" }}>
          <p style={{ margin: "0 0 6px", fontSize: 16, fontWeight: 600, color: "#1A1A1A" }}>No trips booked yet</p>
          <p style={{ margin: 0, fontSize: 14, color: "#64748B" }}>Search for flights and confirm a booking via DIYA</p>
        </div>
        <button onClick={onSwitchToChat}
          style={{ padding: "10px 20px", borderRadius: 10, border: "none", background: "#2563EB", color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
          <MessageSquare size={15} /> Book a flight with DIYA
        </button>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>

      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: "1.5rem" }}>
        {[
          { label: "Trips booked", value: trips.length, icon: Plane, color: "#2563EB", bg: "#EFF6FF", isNum: true },
          { label: "Total fare", value: `₹${totalSpent.toLocaleString("en-IN")}`, icon: TrendingUp, color: "#16A34A", bg: "#F0FDF4", isNum: false },
          { label: "All confirmed", value: `${trips.filter(t => t.status === "confirmed").length}/${trips.length}`, icon: CheckCircle, color: "#7C3AED", bg: "#F5F3FF", isNum: false },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12, padding: "1rem 1.25rem", display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Icon size={18} color={color} />
            </div>
            <div>
              <p style={{ margin: 0, fontSize: 11, color: "#64748B" }}>{label}</p>
              <p style={{ margin: 0, fontSize: 20, fontWeight: 700, color }}>{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Trip cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {trips.map((trip, i) => {
          const airline = trip.airline || "IndiGo";
          const style = AIRLINE_COLORS[airline] || AIRLINE_COLORS["IndiGo"];
          return (
            <div key={trip.booking_id} style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 14, overflow: "hidden" }}>

              {/* Top strip */}
              <div style={{ padding: "12px 16px", borderBottom: "1px solid #F1F5F9", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, background: style.bg, color: style.text, padding: "3px 10px", borderRadius: 20 }}>
                    {airline}
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A" }}>{trip.flight_no}</span>
                  <span style={{ fontSize: 11, background: "#DCFCE7", color: "#15803D", padding: "2px 8px", borderRadius: 10, fontWeight: 600 }}>● Confirmed</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: "#2563EB" }}>₹{trip.price?.toLocaleString("en-IN")}</span>
                  <button onClick={() => onCancel(trip.booking_id)}
                    style={{ padding: "5px 10px", borderRadius: 7, border: "1px solid #FEE2E2", background: "#FEF2F2", cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#DC2626", fontWeight: 500 }}>
                    <Ban size={12} /> Cancel
                  </button>
                </div>
              </div>

              {/* Flight route */}
              <div style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: 0 }}>
                <div style={{ textAlign: "center", minWidth: 80 }}>
                  <p style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#1A1A1A", letterSpacing: "-0.02em" }}>{trip.departure}</p>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#64748B" }}>{trip.origin}</p>
                </div>

                <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "0 16px" }}>
                  <p style={{ margin: "0 0 4px", fontSize: 11, color: "#94A3B8" }}>{trip.duration}</p>
                  <div style={{ width: "100%", display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: style.dot, flexShrink: 0 }} />
                    <div style={{ flex: 1, height: 1.5, background: `linear-gradient(to right, ${style.dot}, ${style.dot})`, backgroundSize: "8px 100%", backgroundRepeat: "repeat-x" }} />
                    <Plane size={16} color={style.dot} style={{ flexShrink: 0 }} />
                  </div>
                  <p style={{ margin: "4px 0 0", fontSize: 11, color: "#94A3B8" }}>Non-stop</p>
                </div>

                <div style={{ textAlign: "center", minWidth: 80 }}>
                  <p style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#1A1A1A", letterSpacing: "-0.02em" }}>{trip.arrival}</p>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: "#64748B" }}>{trip.destination}</p>
                </div>
              </div>

              {/* Details row */}
              <div style={{ padding: "10px 20px 14px", borderTop: "1px solid #F1F5F9", display: "flex", gap: 20, flexWrap: "wrap" }}>
                {[
                  { icon: Hash, label: "Booking ID", value: trip.booking_id },
                  { icon: Hash, label: "PNR", value: trip.pnr },
                  { icon: Calendar, label: "Date", value: trip.travel_date },
                  { icon: Clock, label: "Booked", value: trip.booked_at },
                  { icon: Luggage, label: "Baggage", value: trip.baggage },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <Icon size={13} color="#94A3B8" />
                    <span style={{ fontSize: 12, color: "#64748B" }}>{label}: </span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#334155" }}>{value}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: "1rem", display: "flex", justifyContent: "flex-end", gap: 10 }}>
        <button onClick={onRefresh}
          style={{ padding: "10px 16px", borderRadius: 10, border: "1px solid #E2E8F0", background: "#fff", cursor: "pointer", fontSize: 14, color: "#64748B", display: "flex", alignItems: "center", gap: 6 }}>
          <RefreshCw size={14} /> Refresh
        </button>
        <button
          style={{ padding: "10px 20px", borderRadius: 10, border: "none", background: "#2563EB", color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
          <CheckCircle size={15} /> Download itinerary
        </button>
      </div>
    </div>
  );
}

function ExpensesTab({ expenses, loading, onDelete, onRefresh, totalAll, totalReimbursable, totalNonReimbursable, onSwitchToChat }) {
  if (loading) return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 12 }}>
      <Loader2 size={24} style={{ animation: "spin 1s linear infinite", color: "#2563EB" }} />
      <span style={{ fontSize: 14, color: "#64748B" }}>Loading expenses…</span>
    </div>
  );

  if (expenses.length === 0) return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16, padding: "2rem" }}>
      <div style={{ width: 56, height: 56, borderRadius: 16, background: "#F1F5F9", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Receipt size={26} color="#94A3B8" />
      </div>
      <div style={{ textAlign: "center" }}>
        <p style={{ margin: "0 0 6px", fontSize: 16, fontWeight: 600, color: "#1A1A1A" }}>No expenses yet</p>
        <p style={{ margin: 0, fontSize: 14, color: "#64748B" }}>Log expenses via chat or upload a receipt</p>
      </div>
      <button onClick={onSwitchToChat}
        style={{ padding: "10px 20px", borderRadius: 10, border: "none", background: "#2563EB", color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
        <MessageSquare size={15} /> Go to DIYA Chat
      </button>
    </div>
  );

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: "1.5rem" }}>
        {[
          { label: "Total spent", value: `₹${totalAll.toLocaleString("en-IN")}`, icon: TrendingUp, color: "#2563EB", bg: "#EFF6FF" },
          { label: "Reimbursable", value: `₹${totalReimbursable.toLocaleString("en-IN")}`, icon: ShieldCheck, color: "#16A34A", bg: "#F0FDF4" },
          { label: "Not reimbursable", value: `₹${totalNonReimbursable.toLocaleString("en-IN")}`, icon: ShieldX, color: "#DC2626", bg: "#FEF2F2" },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12, padding: "1rem 1.25rem", display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: 10, background: bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <Icon size={18} color={color} />
            </div>
            <div>
              <p style={{ margin: 0, fontSize: 11, color: "#64748B" }}>{label}</p>
              <p style={{ margin: 0, fontSize: 18, fontWeight: 700, color }}>{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12, overflow: "hidden" }}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#1A1A1A" }}>{expenses.length} expense{expenses.length !== 1 ? "s" : ""} this session</span>
          <span style={{ fontSize: 12, color: "#64748B" }}>Captured by RECAP Agent</span>
        </div>
        {expenses.map((exp, i) => {
          const cat = exp.category || "other";
          const catStyle = CAT_COLORS[cat] || CAT_COLORS.other;
          return (
            <div key={exp.id || i} style={{ padding: "14px 16px", borderBottom: i < expenses.length - 1 ? "1px solid #F1F5F9" : "none", display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 38, height: 38, borderRadius: 10, background: catStyle.bg, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Receipt size={16} color={catStyle.text} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "#1A1A1A" }}>{exp.merchant || "Unknown"}</p>
                  <span style={{ fontSize: 11, background: catStyle.bg, color: catStyle.text, padding: "2px 8px", borderRadius: 10, fontWeight: 500 }}>{cat}</span>
                  {exp.source === "image" && <span style={{ fontSize: 10, background: "#F0F9FF", color: "#0369A1", padding: "2px 6px", borderRadius: 6 }}>📷 OCR</span>}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#64748B" }}>
                  <span>{exp.id}</span><span>·</span><span>{exp.date || exp.logged_at}</span>
                  {exp.tax_amount > 0 && <><span>·</span><span>GST ₹{exp.tax_amount}</span></>}
                </div>
              </div>
              <div style={{ textAlign: "right", marginRight: 12 }}>
                <p style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#1A1A1A" }}>₹{(exp.total_amount || 0).toLocaleString("en-IN")}</p>
                {exp.reimbursable
                  ? <div style={{ display: "flex", alignItems: "center", gap: 4, justifyContent: "flex-end" }}><CheckCircle size={11} color="#16A34A" /><span style={{ fontSize: 11, color: "#16A34A", fontWeight: 600 }}>Reimbursable</span></div>
                  : <div style={{ display: "flex", alignItems: "center", gap: 4, justifyContent: "flex-end" }}><XCircle size={11} color="#DC2626" /><span style={{ fontSize: 11, color: "#DC2626", fontWeight: 600 }}>Not reimbursable</span></div>}
              </div>
              <button onClick={() => onDelete(exp.id)}
                style={{ padding: 8, borderRadius: 8, border: "1px solid #FEE2E2", background: "#FEF2F2", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Trash2 size={14} color="#DC2626" />
              </button>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: "1rem", display: "flex", justifyContent: "flex-end", gap: 10 }}>
        <button onClick={onRefresh} style={{ padding: "10px 16px", borderRadius: 10, border: "1px solid #E2E8F0", background: "#fff", cursor: "pointer", fontSize: 14, color: "#64748B", display: "flex", alignItems: "center", gap: 6 }}>
          <RefreshCw size={14} /> Refresh
        </button>
        <button style={{ padding: "10px 20px", borderRadius: 10, border: "none", background: "#16A34A", color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
          <CheckCircle size={15} /> Submit for reimbursement — ₹{totalReimbursable.toLocaleString("en-IN")}
        </button>
      </div>
    </div>
  );
}

function AgentAvatar({ intent }) {
  const config = INTENT_CONFIG[intent] || INTENT_CONFIG.general;
  const Icon = config.icon;
  const color = COLORS[config.color] || COLORS.gray;
  return (
    <div style={{ width: 36, height: 36, borderRadius: 10, background: color + "1A", border: `1px solid ${color}33`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <Icon size={18} color={color} />
    </div>
  );
}

function MessageBubble({ msg, onConfirmBooking }) {
  if (msg.role === "user") return (
    <div style={{ display: "flex", justifyContent: "flex-end" }}>
      <div style={{ maxWidth: "70%", background: "#2563EB", color: "#fff", borderRadius: "16px 0 16px 16px", padding: "12px 16px", fontSize: 14, lineHeight: 1.6 }}>{msg.content}</div>
    </div>
  );

  const config = INTENT_CONFIG[msg.intent] || INTENT_CONFIG.general;
  const color = COLORS[config.color] || COLORS.gray;
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", maxWidth: "88%" }}>
      <AgentAvatar intent={msg.intent} />
      <div style={{ flex: 1 }}>
        <div style={{ marginBottom: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color, textTransform: "uppercase", letterSpacing: "0.06em" }}>{config.label}</span>
        </div>
        <div style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: "0 16px 16px 16px", padding: "14px 16px" }}>
          <p style={{ margin: "0 0 12px", fontSize: 14, lineHeight: 1.7, whiteSpace: "pre-wrap", color: "#1A1A1A" }}>{msg.data?.message}</p>
          {msg.intent === "booking"    && msg.data?.flights?.length > 0    && <FlightCards flights={msg.data.flights} onConfirm={onConfirmBooking} />}
          {msg.intent === "booking"    && msg.data?.hotels?.length > 0     && <HotelCards hotels={msg.data.hotels} />}
          {msg.intent === "expense"    && msg.data?.merchant                && <ExpenseCard data={msg.data} />}
          {msg.intent === "policy"                                           && <PolicyCard data={msg.data} />}
          {msg.intent === "disruption" && msg.data?.alternatives?.length > 0 && <DisruptionCard data={msg.data} onConfirm={onConfirmBooking} />}
          {msg.intent === "confirmed"                                        && <BookingConfirmedCard data={msg.data} />}
        </div>
      </div>
    </div>
  );
}

function FlightCards({ flights, onConfirm }) {
  const [confirming, setConfirming] = useState(null);
  async function handleConfirm(f) { setConfirming(f.flight_no); await onConfirm(f); setConfirming(null); }
  return (
    <div style={{ marginTop: 4 }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Available Flights</p>
      {flights.slice(0, 3).map((f, i) => (
        <div key={i} style={{ border: "1px solid #E2E8F0", borderRadius: 10, padding: "12px 14px", marginBottom: 8, background: "#F8FAFF" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Plane size={15} color="#2563EB" />
              <div>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>{f.airline} · {f.flight_no}</p>
                <p style={{ margin: 0, fontSize: 12, color: "#64748B" }}>{f.departure} → {f.arrival} · {f.duration}</p>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "#2563EB" }}>₹{f.price.toLocaleString("en-IN")}</p>
              <p style={{ margin: 0, fontSize: 11, color: "#64748B" }}>{f.seats_left} seats left</p>
            </div>
          </div>
          <button onClick={() => handleConfirm(f)} disabled={confirming === f.flight_no}
            style={{ width: "100%", padding: "8px", borderRadius: 8, border: "none", background: confirming === f.flight_no ? "#93C5FD" : "#2563EB", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
            {confirming === f.flight_no ? <><Loader2 size={13} style={{ animation: "spin 1s linear infinite" }} /> Confirming…</> : <><Check size={13} /> Confirm this flight</>}
          </button>
        </div>
      ))}
    </div>
  );
}

function BookingConfirmedCard({ data }) {
  return (
    <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 10, padding: "14px 16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <CheckCircle size={18} color="#16A34A" />
        <span style={{ fontSize: 14, fontWeight: 700, color: "#15803D" }}>Booking Confirmed</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px", fontSize: 13 }}>
        {[["Booking ID", data.booking_id, true], ["PNR", data.pnr, true], ["Flight", `${data.airline} · ${data.flight_no}`, false], ["Route", data.route, false], ["Time", `${data.departure} → ${data.arrival}`, false], ["Seat", `${data.seat} · ${data.class}`, false], ["Baggage", data.baggage, false], ["Amount Paid", `₹${data.price?.toLocaleString("en-IN")}`, false]].map(([label, val, big]) => (
          <div key={label}>
            <p style={{ margin: 0, fontSize: 11, color: "#64748B" }}>{label}</p>
            <p style={{ margin: 0, fontWeight: big ? 700 : 600, fontSize: big ? 14 : 13, color: label === "Amount Paid" ? "#16A34A" : "#1A1A1A" }}>{val}</p>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 12, padding: "8px 12px", background: "#DCFCE7", borderRadius: 8, fontSize: 12, color: "#15803D" }}>
        Confirmation sent to your email · Booked on {data.booked_at}
      </div>
    </div>
  );
}

function HotelCards({ hotels }) {
  return (
    <div style={{ marginTop: 12 }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Hotels</p>
      {hotels.filter(h => h.policy_compliant).slice(0, 2).map((h, i) => (
        <div key={i} style={{ border: "1px solid #E2E8F0", borderRadius: 10, padding: "12px 14px", marginBottom: 8, display: "flex", alignItems: "center", justifyContent: "space-between", background: "#F0FDF4" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Hotel size={15} color="#16A34A" />
            <div>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 700 }}>{h.name}</p>
              <p style={{ margin: 0, fontSize: 12, color: "#64748B" }}><MapPin size={10} /> {h.city} · ⭐ {h.rating}</p>
            </div>
          </div>
          <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: "#16A34A" }}>₹{h.price_per_night.toLocaleString("en-IN")}<span style={{ fontSize: 11, fontWeight: 400, color: "#64748B" }}>/night</span></p>
        </div>
      ))}
    </div>
  );
}

function ExpenseCard({ data }) {
  return (
    <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 10, padding: "12px 14px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p style={{ margin: 0, fontSize: 14, fontWeight: 700 }}>{data.merchant}</p>
          <p style={{ margin: 0, fontSize: 12, color: "#64748B" }}>{data.category} · {data.date}</p>
        </div>
        <div style={{ textAlign: "right" }}>
          <p style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#16A34A" }}>₹{data.total_amount}</p>
          {data.reimbursable ? <span style={{ fontSize: 11, color: "#16A34A", fontWeight: 600 }}>✓ Reimbursable</span> : <span style={{ fontSize: 11, color: "#DC2626", fontWeight: 600 }}>✗ Not reimbursable</span>}
        </div>
      </div>
      {data.policy_flags?.length > 0 && (
        <div style={{ marginTop: 8, background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 6, padding: "6px 10px" }}>
          {data.policy_flags.map((f, i) => <p key={i} style={{ margin: 0, fontSize: 12, color: "#DC2626" }}>⚠ {f}</p>)}
        </div>
      )}
    </div>
  );
}

function PolicyCard({ data }) {
  if (!data) return null;
  return (
    <div style={{ background: "#F5F3FF", border: "1px solid #DDD6FE", borderRadius: 10, padding: "12px 14px" }}>
      {data.allowed !== null && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          {data.allowed ? <CheckCircle size={16} color="#16A34A" /> : <XCircle size={16} color="#DC2626" />}
          <span style={{ fontSize: 13, fontWeight: 700, color: data.allowed ? "#16A34A" : "#DC2626" }}>{data.allowed ? "Allowed" : "Not allowed"}</span>
          {data.approval_needed && <span style={{ fontSize: 11, background: "#FEF3C7", color: "#D97706", padding: "2px 8px", borderRadius: 12, fontWeight: 600 }}>Approval required</span>}
        </div>
      )}
      {data.relevant_policy && (
        <div style={{ background: "#EDE9FE", borderLeft: "3px solid #7C3AED", padding: "6px 10px", borderRadius: 4, marginBottom: 8 }}>
          <p style={{ margin: 0, fontSize: 12, color: "#4C1D95", fontStyle: "italic" }}>{data.relevant_policy}</p>
        </div>
      )}
      {data.suggestion && <p style={{ margin: 0, fontSize: 12, color: "#64748B" }}>💡 {data.suggestion}</p>}
    </div>
  );
}

function DisruptionCard({ data, onConfirm }) {
  return (
    <div>
      {data.entitlements?.length > 0 && (
        <div style={{ background: "#FFFBEB", border: "1px solid #FDE68A", borderRadius: 10, padding: "10px 14px", marginBottom: 10 }}>
          <p style={{ margin: "0 0 6px", fontSize: 12, fontWeight: 700, color: "#92400E" }}>Your entitlements</p>
          {data.entitlements.map((e, i) => <p key={i} style={{ margin: 0, fontSize: 12, color: "#92400E" }}>• {e}</p>)}
        </div>
      )}
      {data.alternatives?.length > 0 && <FlightCards flights={data.alternatives} onConfirm={onConfirm} />}
      {data.action_items?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: "#64748B", textTransform: "uppercase", marginBottom: 6 }}>Action items</p>
          {data.action_items.map((a, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
              <AlertCircle size={13} color="#D97706" />
              <span style={{ fontSize: 13, color: "#334155" }}>{a}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}