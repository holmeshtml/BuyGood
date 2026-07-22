const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API error");
  }

  return res.json();
}

export interface Product {
  product_id: string;
  name: string;
  category: string;
  stock_quantity: number;
}

export interface Customer {
  customer_id: string;
  full_name: string;
  email: string;
  phone: string;
  address: string;
}

export interface Order {
  order_id: string;
  customer_id: string;
  status: string;
  order_total: number;
  currency: string;
  placed_at: string;
}

export interface SearchResult {
  query: string;
  generated_sql: string;
  results: Record<string, unknown>[];
  count: number;
  is_fallback: boolean;
  error?: string;
}
