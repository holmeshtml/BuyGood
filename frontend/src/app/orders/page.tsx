"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchApi, Order, Product, Customer, SearchResult } from "@/lib/api";

interface OrderItem {
  product_id: string;
  quantity: number;
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [searching, setSearching] = useState(false);

  // Create order state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [orderItems, setOrderItems] = useState<OrderItem[]>([{ product_id: "", quantity: 1 }]);
  const [paymentMethod, setPaymentMethod] = useState("credit_card");
  const [creating, setCreating] = useState(false);
  const [createSuccess, setCreateSuccess] = useState("");

  useEffect(() => {
    fetchApi<Order[]>("/orders")
      .then(setOrders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (showCreateForm) {
      Promise.all([
        fetchApi<Customer[]>("/customers"),
        fetchApi<Product[]>("/products"),
      ]).then(([c, p]) => {
        setCustomers(c);
        setProducts(p);
      });
    }
  }, [showCreateForm]);

  function addItem() {
    setOrderItems([...orderItems, { product_id: "", quantity: 1 }]);
  }

  function removeItem(index: number) {
    setOrderItems(orderItems.filter((_, i) => i !== index));
  }

  function updateItem(index: number, field: keyof OrderItem, value: string | number) {
    const updated = [...orderItems];
    updated[index] = { ...updated[index], [field]: value };
    setOrderItems(updated);
  }

  async function handleCreateOrder(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError("");
    setCreateSuccess("");

    try {
      const result = await fetchApi<{ order_id: string; order_total: number }>("/orders", {
        method: "POST",
        body: JSON.stringify({
          customer_id: selectedCustomer,
          items: orderItems.filter((i) => i.product_id),
          payment: { method: paymentMethod },
        }),
      });
      setCreateSuccess(`Order ${result.order_id} created — $${result.order_total.toFixed(2)}`);
      setShowCreateForm(false);
      setOrderItems([{ product_id: "", quantity: 1 }]);
      setSelectedCustomer("");
      // Refresh orders list
      const refreshed = await fetchApi<Order[]>("/orders");
      setOrders(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create order");
    } finally {
      setCreating(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setSearching(true);
    setSearchResult(null);
    try {
      const result = await fetchApi<SearchResult>("/orders/search", {
        method: "POST",
        body: JSON.stringify({ query: searchQuery }),
      });
      setSearchResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="flex flex-col flex-1">
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4 flex items-center gap-4">
        <Link href="/" className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
          ← Back
        </Link>
        <h1 className="text-xl font-bold">Orders</h1>
      </header>

      <main className="flex-1 p-6 max-w-6xl mx-auto w-full space-y-6">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search orders in plain English... e.g. 'orders over $100 this week'"
            className="flex-1 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={searching}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {searching ? "Searching..." : "Search"}
          </button>
        </form>

        {/* Search Results */}
        {searchResult && (
          <div className="rounded-lg border border-blue-200 dark:border-blue-800 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm">
                Search Results ({searchResult.count})
              </h3>
              <button
                onClick={() => setSearchResult(null)}
                className="text-xs text-zinc-500 hover:text-zinc-900"
              >
                Clear
              </button>
            </div>

            {searchResult.error && (
              <p className="text-sm text-yellow-600">{searchResult.error}</p>
            )}

            <details className="text-xs">
              <summary className="cursor-pointer text-zinc-400 hover:text-zinc-600">
                Generated SQL
              </summary>
              <pre className="mt-2 p-2 bg-zinc-100 dark:bg-zinc-800 rounded font-mono overflow-x-auto">
                {searchResult.generated_sql}
              </pre>
            </details>

            {searchResult.results.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-zinc-200 dark:border-zinc-700">
                      {Object.keys(searchResult.results[0]).map((key) => (
                        <th key={key} className="py-2 px-2 text-left font-medium">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {searchResult.results.map((row, i) => (
                      <tr key={i} className="border-b border-zinc-100 dark:border-zinc-800/50">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="py-2 px-2 text-zinc-600 dark:text-zinc-400">
                            {String(val ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Create Order */}
        <div>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors"
          >
            {showCreateForm ? "Cancel" : "+ New Order"}
          </button>

          {createSuccess && (
            <span className="ml-3 text-sm text-green-600 font-medium">{createSuccess}</span>
          )}
        </div>

        {showCreateForm && (
          <form
            onSubmit={handleCreateOrder}
            className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4 space-y-4"
          >
            <h3 className="font-semibold">Create Order</h3>

            {/* Customer select */}
            <div>
              <label className="block text-sm font-medium mb-1">Customer</label>
              <select
                value={selectedCustomer}
                onChange={(e) => setSelectedCustomer(e.target.value)}
                required
                className="w-full rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
              >
                <option value="">Select a customer...</option>
                {customers.map((c) => (
                  <option key={c.customer_id} value={c.customer_id}>
                    {c.full_name} ({c.email})
                  </option>
                ))}
              </select>
            </div>

            {/* Items */}
            <div>
              <label className="block text-sm font-medium mb-1">Items</label>
              {orderItems.map((item, i) => (
                <div key={i} className="flex gap-2 mb-2">
                  <select
                    value={item.product_id}
                    onChange={(e) => updateItem(i, "product_id", e.target.value)}
                    required
                    className="flex-1 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
                  >
                    <option value="">Select product...</option>
                    {products.map((p) => (
                      <option key={p.product_id} value={p.product_id}>
                        {p.name} ({p.stock_quantity} in stock)
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min={1}
                    value={item.quantity}
                    onChange={(e) => updateItem(i, "quantity", parseInt(e.target.value) || 1)}
                    className="w-20 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
                  />
                  {orderItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeItem(i)}
                      className="text-red-500 hover:text-red-700 text-sm px-2"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addItem}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                + Add item
              </button>
            </div>

            {/* Payment */}
            <div>
              <label className="block text-sm font-medium mb-1">Payment Method</label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-full rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-3 py-2 text-sm"
              >
                <option value="credit_card">Credit Card</option>
                <option value="debit_card">Debit Card</option>
                <option value="paypal">PayPal</option>
                <option value="apple_pay">Apple Pay</option>
                <option value="google_pay">Google Pay</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {creating ? "Placing Order..." : "Place Order"}
            </button>
          </form>
        )}

        {/* Orders Table */}
        {loading && <p className="text-zinc-500">Loading orders...</p>}
        {error && !searchResult && <p className="text-red-500">{error}</p>}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-800 text-left">
                <th className="py-3 px-2 font-medium">Order ID</th>
                <th className="py-3 px-2 font-medium">Customer</th>
                <th className="py-3 px-2 font-medium">Status</th>
                <th className="py-3 px-2 font-medium">Total</th>
                <th className="py-3 px-2 font-medium hidden md:table-cell">Date</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr
                  key={order.order_id}
                  className="border-b border-zinc-100 dark:border-zinc-800/50 hover:bg-zinc-50 dark:hover:bg-zinc-900"
                >
                  <td className="py-3 px-2 font-mono text-xs">{order.order_id}</td>
                  <td className="py-3 px-2 font-mono text-xs text-zinc-500">
                    {order.customer_id}
                  </td>
                  <td className="py-3 px-2">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                        order.status === "placed"
                          ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                          : order.status === "shipped"
                          ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                          : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                      }`}
                    >
                      {order.status}
                    </span>
                  </td>
                  <td className="py-3 px-2 font-medium">
                    ${order.order_total.toFixed(2)}
                  </td>
                  <td className="py-3 px-2 text-zinc-500 hidden md:table-cell">
                    {new Date(order.placed_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
