import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-col flex-1">
      {/* Header */}
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight">GoodBuy</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Ecommerce Dashboard
        </p>
      </header>

      {/* Main */}
      <main className="flex-1 p-6 max-w-6xl mx-auto w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Link
            href="/products"
            className="group rounded-xl border border-zinc-200 dark:border-zinc-800 p-6 hover:border-zinc-400 dark:hover:border-zinc-600 transition-colors"
          >
            <h2 className="text-xl font-semibold mb-2 group-hover:text-blue-600 transition-colors">
              Products →
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400">
              Browse the product catalog and check stock levels.
            </p>
          </Link>

          <Link
            href="/customers"
            className="group rounded-xl border border-zinc-200 dark:border-zinc-800 p-6 hover:border-zinc-400 dark:hover:border-zinc-600 transition-colors"
          >
            <h2 className="text-xl font-semibold mb-2 group-hover:text-blue-600 transition-colors">
              Customers →
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400">
              View customer profiles and contact info.
            </p>
          </Link>

          <Link
            href="/orders"
            className="group rounded-xl border border-zinc-200 dark:border-zinc-800 p-6 hover:border-zinc-400 dark:hover:border-zinc-600 transition-colors"
          >
            <h2 className="text-xl font-semibold mb-2 group-hover:text-blue-600 transition-colors">
              Orders →
            </h2>
            <p className="text-zinc-500 dark:text-zinc-400">
              Track orders and search with natural language.
            </p>
          </Link>
        </div>
      </main>
    </div>
  );
}
