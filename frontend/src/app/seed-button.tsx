"use client";

import { useState } from "react";
import { fetchApi } from "@/lib/api";

interface SeedResponse {
  status: string;
  days: number;
  counts: {
    customers: number;
    products: number;
    orders: number;
    order_items: number;
    payments: number;
    events: number;
  };
}

export default function SeedButton() {
  const [days, setDays] = useState(7);
  const [seeding, setSeeding] = useState(false);
  const [result, setResult] = useState<SeedResponse | null>(null);
  const [error, setError] = useState("");

  async function handleSeed() {
    setSeeding(true);
    setError("");
    setResult(null);

    try {
      const res = await fetchApi<SeedResponse>(`/seed?days=${days}`, {
        method: "POST",
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      {result && (
        <span className="text-xs text-green-600 font-medium">
          Seeded {result.counts.orders} orders, {result.counts.events} events
        </span>
      )}
      {error && <span className="text-xs text-red-500">{error}</span>}

      <div className="flex items-center gap-2">
        <label className="text-xs text-zinc-500">Days:</label>
        <input
          type="number"
          min={1}
          max={365}
          value={days}
          onChange={(e) => setDays(parseInt(e.target.value) || 7)}
          className="w-16 rounded border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-1 text-sm"
        />
      </div>

      <button
        onClick={handleSeed}
        disabled={seeding}
        className="rounded-lg bg-orange-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50 transition-colors"
      >
        {seeding ? "Seeding..." : "🌱 Seed DB"}
      </button>
    </div>
  );
}
