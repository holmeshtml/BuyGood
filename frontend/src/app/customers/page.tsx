"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchApi, Customer } from "@/lib/api";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchApi<Customer[]>("/customers")
      .then(setCustomers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col flex-1">
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4 flex items-center gap-4">
        <Link href="/" className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
          ← Back
        </Link>
        <h1 className="text-xl font-bold">Customers</h1>
      </header>

      <main className="flex-1 p-6 max-w-6xl mx-auto w-full">
        {loading && <p className="text-zinc-500">Loading customers...</p>}
        {error && <p className="text-red-500">{error}</p>}

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-800 text-left">
                <th className="py-3 px-2 font-medium">Name</th>
                <th className="py-3 px-2 font-medium">Email</th>
                <th className="py-3 px-2 font-medium hidden md:table-cell">Phone</th>
                <th className="py-3 px-2 font-medium hidden lg:table-cell">Address</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr
                  key={c.customer_id}
                  className="border-b border-zinc-100 dark:border-zinc-800/50 hover:bg-zinc-50 dark:hover:bg-zinc-900"
                >
                  <td className="py-3 px-2 font-medium">{c.full_name}</td>
                  <td className="py-3 px-2 text-zinc-500">{c.email}</td>
                  <td className="py-3 px-2 text-zinc-500 hidden md:table-cell">{c.phone}</td>
                  <td className="py-3 px-2 text-zinc-500 hidden lg:table-cell">{c.address}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
