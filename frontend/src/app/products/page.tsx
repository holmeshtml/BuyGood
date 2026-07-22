"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchApi, Product } from "@/lib/api";

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchApi<Product[]>("/products")
      .then(setProducts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col flex-1">
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4 flex items-center gap-4">
        <Link href="/" className="text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100">
          ← Back
        </Link>
        <h1 className="text-xl font-bold">Products</h1>
      </header>

      <main className="flex-1 p-6 max-w-6xl mx-auto w-full">
        {loading && <p className="text-zinc-500">Loading products...</p>}
        {error && <p className="text-red-500">{error}</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {products.map((product) => (
            <div
              key={product.product_id}
              className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-4"
            >
              <h3 className="font-semibold text-lg">{product.name}</h3>
              <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
                {product.category}
              </p>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs font-mono text-zinc-400">
                  {product.product_id}
                </span>
                <span
                  className={`text-sm font-medium ${
                    product.stock_quantity > 10
                      ? "text-green-600"
                      : product.stock_quantity > 0
                      ? "text-yellow-600"
                      : "text-red-600"
                  }`}
                >
                  {product.stock_quantity} in stock
                </span>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
